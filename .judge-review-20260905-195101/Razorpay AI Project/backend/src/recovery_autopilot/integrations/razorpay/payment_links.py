"""Razorpay Test Mode Payment Link adapter with immutable amount enforcement."""

import json
import logging
import uuid
from typing import Any, Dict, Optional

from recovery_autopilot.domain.enums import RecoveryAction
from recovery_autopilot.domain.models import ExecutionResult, PaymentCase, utc_now
from recovery_autopilot.integrations.razorpay.client import (
    GenuineRazorpayTestClient,
    RazorpayGatewayClient,
    RazorpayGatewayError,
    SyntheticRazorpayClient,
)
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.persistence.database import async_session_factory
from recovery_autopilot.persistence.models import OperationKeyRecord


logger = logging.getLogger("recovery_autopilot.integrations.razorpay.payment_links")


def redact_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive card and personal identifiers from audit and logs."""
    redacted = dict(data)
    if "email" in redacted and isinstance(redacted["email"], str):
        parts = redacted["email"].split("@")
        redacted["email"] = f"{parts[0][:3]}***@{parts[1]}" if len(parts) == 2 else "***"
    if "phone" in redacted and isinstance(redacted["phone"], str):
        redacted["phone"] = f"{redacted['phone'][:3]}****{redacted['phone'][-3:]}"
    return redacted


class PaymentLinkAdapter:
    """Creates Razorpay Payment Links for approved recovery cases with immutable amount enforcement.

    Supports:
    1. Synthetic mode (zero network, local deterministic simulation).
    2. Genuine Razorpay Test Mode (authentic test API calls using rzp_test_ keys).
    Strictly prohibits live production execution and never silently falls back to synthetic client.
    """

    def __init__(
        self,
        key_id: str = "",
        key_secret: str = "",
        mode: str = "synthetic",
        test_mode: Optional[bool] = None,
        gateway_client: Optional[RazorpayGatewayClient] = None,
    ):
        self.key_id = key_id
        self.key_secret = key_secret
        if test_mode is not None:
            self.mode = "synthetic" if test_mode else mode
        else:
            self.mode = mode

        if gateway_client is not None:
            self.client = gateway_client
        elif self.mode == "razorpay_test":
            if not key_id or not key_secret:
                raise ValueError(
                    "Missing Razorpay test credentials. In razorpay_test mode, RAZORPAY_KEY_ID "
                    "and RAZORPAY_KEY_SECRET must be configured. Never silently substituting synthetic client."
                )
            if not key_id.startswith("rzp_test_"):
                raise ValueError(
                    f"Invalid key_id '{key_id[:8]}...': In razorpay_test mode, keys must strictly start with 'rzp_test_'. "
                    "Live credentials (rzp_live_...) are strictly prohibited."
                )
            self.client = GenuineRazorpayTestClient(key_id=key_id, key_secret=key_secret)
        elif self.mode == "synthetic":
            self.client = SyntheticRazorpayClient()
        else:
            raise ValueError(f"Unsupported execution mode '{self.mode}'. Allowed modes: ['synthetic', 'razorpay_test'].")

    async def create_payment_link(
        self,
        case: PaymentCase,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> ExecutionResult:
        """Create a payment link with persisted operation key, immutable amount, and exact correlation notes."""
        from recovery_autopilot.config import settings
        if settings.KILL_SWITCH_ACTIVE:
            logger.warning("Emergency Kill Switch is ACTIVE. Halting payment link creation for case %s.", case.case_id)
            return ExecutionResult(
                action=case.latest_decision.approved_action if case.latest_decision else RecoveryAction.SEND_PAYMENT_LINK,
                status="BLOCKED_BY_KILL_SWITCH",
                error="Emergency Kill Switch is active. Payment link creation halted.",
            )

        ctx = case.context
        amount_paise = int(round(ctx.amount_inr * 100))
        idemp = idempotency_key or f"plink_{case.case_id}_{case.contact_count + 1}_{uuid.uuid4().hex[:6]}"

        # 1. Check Persisted Operation Key (Prevents blind retries & reconciles timeouts)
        try:
            op_rec = None
            if session is not None:
                op_rec = await session.get(OperationKeyRecord, idemp)
            else:
                async with async_session_factory() as s:
                    op_rec = await s.get(OperationKeyRecord, idemp)

            if op_rec and op_rec.status == "completed" and op_rec.result_json:
                cached_res = json.loads(op_rec.result_json)
                logger.info("Reconciled existing payment link from operation key %s: %s", idemp, cached_res.get("id"))
                plink_id = cached_res.get("id")
                short_url = cached_res.get("short_url")

                if plink_id:
                    case.context = case.context.model_copy(update={"payment_link_id": plink_id})

                meta = redact_metadata({
                    "idempotency_key": idemp,
                    "amount_inr": ctx.amount_inr,
                    "short_url": short_url,
                    "payment_link_id": plink_id,
                    "email": ctx.customer_email,
                    "phone": ctx.customer_phone,
                    "execution_mode": self.mode,
                    "reconciled_from_operation_key": True,
                })
                return ExecutionResult(
                    action=RecoveryAction.SEND_PAYMENT_LINK,
                    external_id=plink_id,
                    status="SUCCESS",
                    executed_at=op_rec.created_at,
                    metadata=meta,
                )
        except Exception as e:
            logger.warning("Operation key lookup check warning: %s", e)

        notes = {
            "case_id": case.case_id,
            "subscription_id": ctx.subscription_id,
            "invoice_id": ctx.invoice_id or "",
            "order_id": ctx.order_id or "",
            "idempotency_key": idemp,
            "source": "recovery_autopilot",
        }

        desc = description or f"Subscription Recovery for {ctx.subscription_id}"

        try:
            res = await self.client.create_payment_link(
                amount_paise=amount_paise,
                currency=ctx.currency,
                description=desc,
                customer_name=ctx.customer_name,
                customer_email=ctx.customer_email,
                customer_phone=ctx.customer_phone,
                notes=notes,
                idempotency_key=idemp,
            )

            plink_id = res.get("id")
            short_url = res.get("short_url")

            # Update context with generated payment_link_id for exact webhook matching
            if plink_id:
                case.context = case.context.model_copy(update={"payment_link_id": plink_id})

            # Record completed operation key
            try:
                op = OperationKeyRecord(
                    operation_key=idemp,
                    case_id=case.case_id,
                    action_type="create_payment_link",
                    status="completed",
                    external_id=plink_id,
                    result_json=json.dumps(res),
                )
                if session is not None:
                    session.add(op)
                    await session.flush()
                else:
                    async with async_session_factory() as s:
                        s.add(op)
                        await s.commit()
            except Exception as e:
                logger.warning("Failed saving operation key record: %s", e)


            meta = redact_metadata({
                "idempotency_key": idemp,
                "amount_inr": ctx.amount_inr,
                "short_url": short_url,
                "payment_link_id": plink_id,
                "email": ctx.customer_email,
                "phone": ctx.customer_phone,
                "execution_mode": self.mode,
            })

            return ExecutionResult(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                external_id=plink_id,
                status="SUCCESS",
                executed_at=utc_now(),
                metadata=meta,
            )

        except RazorpayGatewayError as exc:
            logger.error("Razorpay Gateway payment link error: %s", str(exc))
            # Record failed operation key
            try:
                async with async_session_factory() as s:
                    op = OperationKeyRecord(
                        operation_key=idemp,
                        case_id=case.case_id,
                        action_type="create_payment_link",
                        status="failed",
                        error_message=str(exc),
                    )
                    s.add(op)
                    await s.commit()
            except Exception:
                pass

            return ExecutionResult(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                status="FAILED",
                error=f"Gateway Error: {exc.message}",
                executed_at=utc_now(),
                metadata={"idempotency_key": idemp, "error_details": exc.details},
            )
        except Exception as exc:
            logger.error("Unexpected error creating payment link: %s", str(exc), exc_info=True)
            return ExecutionResult(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                status="FAILED",
                error=f"Internal Error: {str(exc)}",
                executed_at=utc_now(),
                metadata={"idempotency_key": idemp},
            )
