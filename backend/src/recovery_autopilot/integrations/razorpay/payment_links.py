"""Razorpay Test Mode Payment Link adapter with immutable amount enforcement."""

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
    1. Synthetic mode (zero network, local simulation)
    2. Genuine Razorpay Test Mode (authentic test API calls using rzp_test_ keys)
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
        elif self.mode == "razorpay_test" and key_id and key_secret and key_id.startswith("rzp_test_"):
            self.client = GenuineRazorpayTestClient(key_id=key_id, key_secret=key_secret)
        else:
            self.client = SyntheticRazorpayClient()

    async def create_payment_link(
        self,
        case: PaymentCase,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> ExecutionResult:
        """Create a payment link with immutable amount and exact correlation notes."""
        ctx = case.context
        amount_paise = int(round(ctx.amount_inr * 100))
        idemp = idempotency_key or f"plink_{case.case_id}_{case.contact_count + 1}_{uuid.uuid4().hex[:6]}"

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
            return ExecutionResult(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                status="FAILED",
                executed_at=utc_now(),
                error=str(exc),
            )
        except Exception as exc:
            logger.error("Unexpected error creating payment link: %s", str(exc))
            return ExecutionResult(
                action=RecoveryAction.SEND_PAYMENT_LINK,
                status="FAILED",
                executed_at=utc_now(),
                error=str(exc),
            )

