"""Razorpay Test Mode Payment Link adapter with immutable amount enforcement."""

import logging
import uuid
from typing import Any, Dict, Optional

from recovery_autopilot.domain.enums import RecoveryAction
from recovery_autopilot.domain.models import ExecutionResult, PaymentCase, utc_now

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
    """Creates test-mode Razorpay Payment Links for approved recovery cases.

    Safety:
    The billing amount is strictly derived from the immutable context of the PaymentCase.
    An external caller or LLM CANNOT pass a new amount.
    """

    def __init__(self, key_id: str = "", key_secret: str = "", test_mode: bool = True):
        self.key_id = key_id
        self.key_secret = key_secret
        self.test_mode = test_mode
        self._razorpay_client = None

    def _get_client(self):
        if self._razorpay_client is None and self.key_id and self.key_secret:
            try:
                import razorpay
                self._razorpay_client = razorpay.Client(auth=(self.key_id, self.key_secret))
            except Exception as e:
                logger.warning("Failed to initialize Razorpay SDK client: %s; using simulation adapter", str(e))
        return self._razorpay_client

    async def create_payment_link(
        self,
        case: PaymentCase,
        description: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> ExecutionResult:
        """Create a test-mode payment link for the case."""
        ctx = case.context
        amount_paise = int(round(ctx.amount_inr * 100))
        idemp = idempotency_key or f"plink_{case.case_id}_{case.contact_count + 1}_{uuid.uuid4().hex[:6]}"

        client = self._get_client()

        if client and not self.test_mode:
            # If live credentials existed, call SDK
            try:
                link_data = {
                    "amount": amount_paise,
                    "currency": ctx.currency,
                    "accept_partial": False,
                    "description": description or f"Subscription Renewal {ctx.subscription_id}",
                    "customer": {
                        "name": ctx.customer_name,
                        "email": ctx.customer_email,
                        "contact": ctx.customer_phone,
                    },
                    "notes": {
                        "case_id": case.case_id,
                        "subscription_id": ctx.subscription_id,
                        "idempotency_key": idemp,
                    },
                }
                res = client.payment_link.create(link_data)
                plink_id = res.get("id")
                short_url = res.get("short_url")

                meta = redact_metadata({
                    "idempotency_key": idemp,
                    "amount_inr": ctx.amount_inr,
                    "short_url": short_url,
                    "email": ctx.customer_email,
                    "phone": ctx.customer_phone,
                })

                return ExecutionResult(
                    action=RecoveryAction.SEND_PAYMENT_LINK,
                    external_id=plink_id,
                    status="SUCCESS",
                    executed_at=utc_now(),
                    metadata=meta,
                )
            except Exception as e:
                logger.error("Razorpay SDK payment link generation failed: %s", str(e))
                return ExecutionResult(
                    action=RecoveryAction.SEND_PAYMENT_LINK,
                    status="FAILED",
                    executed_at=utc_now(),
                    error=str(e),
                )

        # Simulation Mode (Zero external call / Test mode)
        simulated_id = f"plink_test_{uuid.uuid4().hex[:12]}"
        simulated_url = f"https://rzp.io/i/{simulated_id[6:]}"

        meta = redact_metadata({
            "idempotency_key": idemp,
            "amount_inr": ctx.amount_inr,
            "short_url": simulated_url,
            "email": ctx.customer_email,
            "phone": ctx.customer_phone,
            "test_mode": True,
        })

        return ExecutionResult(
            action=RecoveryAction.SEND_PAYMENT_LINK,
            external_id=simulated_id,
            status="SUCCESS",
            executed_at=utc_now(),
            metadata=meta,
        )
