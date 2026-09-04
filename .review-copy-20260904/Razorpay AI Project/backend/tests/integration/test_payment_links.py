"""Integration tests for Razorpay test-mode payment link generation and simulated notifications."""

import pytest

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, PaymentContext, PolicyDecision
from recovery_autopilot.integrations.notifications.simulator import UnifiedActionExecutor
from recovery_autopilot.integrations.razorpay.payment_links import PaymentLinkAdapter


def make_test_case(amount_inr: float = 4999.0) -> PaymentCase:
    ctx = PaymentContext(
        payment_id="pay_plink_test_01",
        subscription_id="sub_plink_test_01",
        customer_id="cust_plink_01",
        customer_name="Siddharth Rao",
        customer_email="siddharth@synthetic-test.example.com",
        customer_phone="+919800077777",
        amount_inr=amount_inr,
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="INSUFFICIENT_FUNDS",
        failure_reason="Insufficient balance",
        payment_method="CARD",  # type: ignore
    )
    case = PaymentCase(context=ctx)
    case.latest_decision = PolicyDecision(
        case_id=case.case_id,
        allowed=True,
        approved_action=RecoveryAction.SEND_PAYMENT_LINK,
        modified_delay_minutes=0,
        reason_codes=["APPROVED"],
        requires_human_review=False,
    )
    return case


@pytest.mark.asyncio
async def test_payment_link_adapter_generates_valid_link():
    """PaymentLinkAdapter creates test payment link with immutable amount and masked metadata."""
    adapter = PaymentLinkAdapter(test_mode=True)
    case = make_test_case(amount_inr=4999.0)

    result = await adapter.create_payment_link(case)
    assert result.status == "SUCCESS"
    assert result.action == RecoveryAction.SEND_PAYMENT_LINK
    assert result.external_id is not None
    assert result.external_id.startswith("plink_test_")
    assert result.metadata["amount_inr"] == 4999.0

    # Ensure PII was redacted
    assert "siddharth@synthetic-test.example.com" not in result.metadata["email"]
    assert "***" in result.metadata["email"]


@pytest.mark.asyncio
async def test_unified_executor_stores_notification_preview():
    """UnifiedActionExecutor creates link and stores in-memory notification preview."""
    adapter = PaymentLinkAdapter(test_mode=True)
    executor = UnifiedActionExecutor(payment_link_adapter=adapter)
    case = make_test_case(amount_inr=1999.0)

    result = await executor.execute_action(
        case=case,
        action=RecoveryAction.SEND_PAYMENT_LINK,
        customer_message="Please complete your payment here",
    )
    assert result.status == "SUCCESS"

    notifications = executor.get_notifications_for_case(case.case_id)
    assert len(notifications) == 1
    notif = notifications[0]
    assert notif.channel == "WHATSAPP"
    assert notif.recipient_masked.startswith("+919")
    assert "Please complete your payment here" in notif.content
