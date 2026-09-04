"""Domain contract validation tests."""

import pytest
from pydantic import ValidationError

from recovery_autopilot.domain.enums import (
    ActorType,
    CaseStatus,
    CustomerSegment,
    FailureCategory,
    PaymentMethod,
    RecoveryAction,
)
from recovery_autopilot.domain.models import (
    AuditEvent,
    PaymentCase,
    PaymentContext,
    PolicyDecision,
    RecoveryProposal,
)


def sample_context() -> PaymentContext:
    """Helper to construct a valid PaymentContext."""
    return PaymentContext(
        payment_id="pay_test_001",
        subscription_id="sub_test_001",
        invoice_id="inv_test_001",
        customer_id="cust_syn_001",
        customer_name="Aarav Sharma",
        customer_email="aarav@synthetic-test.example.com",
        customer_phone="+919800000001",
        amount_inr=4999.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST_PAYMENT_FAILED",
        failure_reason="Customer bank reported insufficient funds",
        payment_method=PaymentMethod.CARD,
        customer_segment=CustomerSegment.SMB,
        previous_failures=1,
        previous_contacts=0,
        bank_name="HDFC",
        bank_degraded=False,
        opted_out=False,
    )


def test_payment_context_immutability():
    """PaymentContext should be frozen/immutable to prevent amount or customer tampering."""
    ctx = sample_context()
    with pytest.raises(ValidationError):
        ctx.amount_inr = 9999.0  # type: ignore


def test_recovery_proposal_valid():
    """Valid proposal with allowed actions should pass validation."""
    proposal = RecoveryProposal(
        action=RecoveryAction.SEND_PAYMENT_LINK,
        confidence=0.88,
        delay_minutes=60,
        reason_codes=["INSUFFICIENT_FUNDS_SALARY_CYCLE"],
        explanation="Customer typically settles within 24 hours when given a direct payment link.",
        requires_human_approval=False,
    )
    assert proposal.action == RecoveryAction.SEND_PAYMENT_LINK
    assert proposal.confidence == 0.88
    assert proposal.delay_minutes == 60


def test_recovery_proposal_rejects_arbitrary_fields():
    """AI proposal must reject unexpected fields (e.g. attempting to inject amount or raw shell tools)."""
    with pytest.raises(ValidationError):
        RecoveryProposal(
            action=RecoveryAction.SEND_PAYMENT_LINK,
            confidence=0.9,
            delay_minutes=0,
            explanation="Test proposal",
            injected_amount=100.0,  # Prohibited
        )


def test_recovery_proposal_bounds():
    """Confidence and delay must adhere to domain bounds."""
    with pytest.raises(ValidationError):
        RecoveryProposal(
            action=RecoveryAction.WAIT_FOR_RETRY,
            confidence=1.5,  # Invalid: > 1.0
            delay_minutes=10,
            explanation="Out of bounds confidence",
        )

    with pytest.raises(ValidationError):
        RecoveryProposal(
            action=RecoveryAction.WAIT_FOR_RETRY,
            confidence=-0.1,  # Invalid: < 0.0
            delay_minutes=10,
            explanation="Out of bounds confidence",
        )

    with pytest.raises(ValidationError):
        RecoveryProposal(
            action=RecoveryAction.WAIT_FOR_RETRY,
            confidence=0.5,
            delay_minutes=20000,  # Invalid: > 10080
            explanation="Excessive delay",
        )


def test_policy_decision_creation():
    """Policy decision correctly captures approval and reason codes."""
    decision = PolicyDecision(
        case_id="case_001",
        allowed=True,
        approved_action=RecoveryAction.SEND_PAYMENT_LINK,
        modified_delay_minutes=120,
        reason_codes=["APPROVED_WITHIN_LIMITS"],
        requires_human_review=False,
    )
    assert decision.allowed is True
    assert decision.approved_action == RecoveryAction.SEND_PAYMENT_LINK
    assert decision.modified_delay_minutes == 120


def test_payment_case_contact_tracking():
    """PaymentCase tracks lifecycle status and contact attempts."""
    ctx = sample_context()
    case = PaymentCase(context=ctx, status=CaseStatus.NEW)
    assert case.contact_count == 0
    assert case.status == CaseStatus.NEW

    case.record_contact()
    assert case.contact_count == 1


def test_audit_event_structure():
    """AuditEvent records actor and detailed payload."""
    event = AuditEvent(
        case_id="case_001",
        actor=ActorType.AI,
        event_type="PROPOSAL_GENERATED",
        details={"model": "gemini-3.7-flash", "confidence": 0.85},
    )
    assert event.actor == ActorType.AI
    assert event.details["confidence"] == 0.85
