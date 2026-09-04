"""Maps raw Razorpay webhook event payloads into domain entities and failure categories."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from recovery_autopilot.domain.enums import CustomerSegment, FailureCategory, PaymentMethod
from recovery_autopilot.domain.models import PaymentContext

logger = logging.getLogger("recovery_autopilot.integrations.razorpay.event_mapper")

# Mapping of known gateway / bank error codes to domain FailureCategory
ERROR_CODE_CATEGORY_MAP = {
    "BAD_REQUEST_PAYMENT_FAILED": FailureCategory.INSUFFICIENT_FUNDS,
    "GATEWAY_TIMEOUT": FailureCategory.BANK_TIMEOUT,
    "BANK_TECHNICAL_ERROR": FailureCategory.BANK_TIMEOUT,
    "EXPIRED_CARD_INSTRUMENT": FailureCategory.EXPIRED_CARD,
    "CARD_EXPIRED": FailureCategory.EXPIRED_CARD,
    "MANDATE_CANCELLED_BY_USER": FailureCategory.MANDATE_REVOKED,
    "MANDATE_REVOKED": FailureCategory.MANDATE_REVOKED,
    "CARD_VELOCITY_LIMIT_EXCEEDED": FailureCategory.LIMIT_EXCEEDED,
    "AMOUNT_LIMIT_EXCEEDED": FailureCategory.LIMIT_EXCEEDED,
    "NETWORK_COMMUNICATION_ERROR": FailureCategory.NETWORK_FAILURE,
    "GATEWAY_ERROR": FailureCategory.NETWORK_FAILURE,
    "ACTION_REQUIRED_OTP": FailureCategory.CUSTOMER_ACTION_REQUIRED,
    "CUSTOMER_DROPPED": FailureCategory.CUSTOMER_ACTION_REQUIRED,
}


def classify_failure(error_code: str, error_desc: str) -> FailureCategory:
    """Classify failure code and description into controlled FailureCategory."""
    code_upper = error_code.upper()
    if code_upper in ERROR_CODE_CATEGORY_MAP:
        return ERROR_CODE_CATEGORY_MAP[code_upper]

    desc_lower = error_desc.lower()
    if "insufficient" in desc_lower or "balance" in desc_lower:
        return FailureCategory.INSUFFICIENT_FUNDS
    elif "timeout" in desc_lower or "timed out" in desc_lower:
        return FailureCategory.BANK_TIMEOUT
    elif "expired" in desc_lower:
        return FailureCategory.EXPIRED_CARD
    elif "mandate" in desc_lower and ("revoked" in desc_lower or "cancel" in desc_lower):
        return FailureCategory.MANDATE_REVOKED
    elif "limit" in desc_lower or "exceeded" in desc_lower:
        return FailureCategory.LIMIT_EXCEEDED
    elif "network" in desc_lower or "switch" in desc_lower:
        return FailureCategory.NETWORK_FAILURE
    elif "action" in desc_lower or "otp" in desc_lower or "auth" in desc_lower:
        return FailureCategory.CUSTOMER_ACTION_REQUIRED

    return FailureCategory.UNKNOWN_FAILURE


@dataclass
class CapturedPaymentContext:
    """Structured context extracted from payment.captured or order.paid webhooks."""

    payment_id: str
    amount_inr: float
    currency: str = "INR"
    order_id: Optional[str] = None
    subscription_id: Optional[str] = None
    invoice_id: Optional[str] = None
    payment_link_id: Optional[str] = None
    method: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class RazorpayEventMapper:
    """Extracts structured domain context from raw Razorpay webhook payloads."""

    @staticmethod
    def map_payment_failed(payload: Dict[str, Any]) -> PaymentContext:
        """Map payment.failed webhook payload into PaymentContext."""
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        error_code = payment_entity.get("error_code", "UNKNOWN_ERROR")
        error_desc = payment_entity.get("error_description", "Payment failed")
        category = classify_failure(error_code, error_desc)

        # Amounts in Razorpay are in paise (e.g. 50000 = INR 500.00)
        amount_paise = payment_entity.get("amount", 0)
        amount_inr = round(float(amount_paise) / 100.0, 2)
        if amount_inr <= 0:
            amount_inr = 999.0  # Safe positive fallback

        # Determine method
        method_str = payment_entity.get("method", "card").upper()
        method = PaymentMethod.CARD
        if "UPI" in method_str:
            method = PaymentMethod.UPI
        elif "NETBANKING" in method_str:
            method = PaymentMethod.NETBANKING
        elif "NACH" in method_str:
            method = PaymentMethod.NACH

        created_at_ts = payment_entity.get("created_at")
        occurred_at = (
            datetime.fromtimestamp(created_at_ts, tz=timezone.utc)
            if created_at_ts
            else datetime.now(timezone.utc)
        )

        notes = payment_entity.get("notes", {})
        subscription_id = (
            payment_entity.get("subscription_id")
            or payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("id")
            or notes.get("subscription_id")
            or "sub_unknown"
        )
        order_id = payment_entity.get("order_id") or payload.get("payload", {}).get("order", {}).get("entity", {}).get("id") or notes.get("order_id")
        payment_link_id = notes.get("payment_link_id") or payment_entity.get("payment_link_id") or notes.get("plink_id")

        return PaymentContext(
            payment_id=payment_entity.get("id", "pay_unknown"),
            subscription_id=subscription_id,
            invoice_id=payment_entity.get("invoice_id") or notes.get("invoice_id"),
            order_id=order_id,
            payment_link_id=payment_link_id,
            customer_id=payment_entity.get("customer_id") or notes.get("customer_id") or "cust_syn_guest",
            customer_name=notes.get("customer_name") or "Synthetic Customer",
            customer_email=payment_entity.get("email") or notes.get("email") or "customer@synthetic-test.example.com",
            customer_phone=payment_entity.get("contact") or notes.get("phone") or "+919800000000",
            amount_inr=amount_inr,
            currency=payment_entity.get("currency", "INR"),
            failure_category=category,
            failure_code=error_code,
            failure_reason=error_desc,
            payment_method=method,
            customer_segment=CustomerSegment.SMB,
            previous_failures=1,
            previous_contacts=0,
            bank_name=payment_entity.get("bank"),
            bank_degraded=(category in [FailureCategory.BANK_TIMEOUT, FailureCategory.NETWORK_FAILURE]),
            opted_out=False,
            occurred_at=occurred_at,
        )

    @staticmethod
    def map_payment_captured(payload: Dict[str, Any]) -> CapturedPaymentContext:
        """Extract multi-identifier CapturedPaymentContext from payment.captured / order.paid webhook."""
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        sub_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})

        pay_id = payment_entity.get("id") or "pay_captured"
        amount_paise = payment_entity.get("amount") or order_entity.get("amount") or 0
        amount_inr = round(float(amount_paise) / 100.0, 2)
        currency = payment_entity.get("currency") or order_entity.get("currency") or "INR"

        notes = payment_entity.get("notes", {}) or order_entity.get("notes", {})

        sub_id = payment_entity.get("subscription_id") or sub_entity.get("id") or notes.get("subscription_id")
        inv_id = payment_entity.get("invoice_id") or notes.get("invoice_id")
        ord_id = payment_entity.get("order_id") or order_entity.get("id") or notes.get("order_id")
        plink_id = (
            notes.get("payment_link_id")
            or notes.get("plink_id")
            or payment_entity.get("payment_link_id")
            or notes.get("idempotency_key")
        )

        return CapturedPaymentContext(
            payment_id=pay_id,
            amount_inr=amount_inr,
            currency=currency,
            order_id=ord_id,
            subscription_id=sub_id,
            invoice_id=inv_id,
            payment_link_id=plink_id,
            method=payment_entity.get("method"),
            customer_email=payment_entity.get("email") or notes.get("email"),
            customer_phone=payment_entity.get("contact") or notes.get("phone"),
        )

