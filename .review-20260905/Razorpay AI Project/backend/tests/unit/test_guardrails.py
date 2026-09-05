"""Unit tests for deterministic policy guardrails."""


from recovery_autopilot.config import Settings
from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, PaymentContext, RecoveryProposal
from recovery_autopilot.policies.guardrails import SafetyPolicyEngine


def make_test_case(
    amount: float = 2999.0,
    category: FailureCategory = FailureCategory.BANK_TIMEOUT,
    contacts: int = 0,
    opted_out: bool = False,
) -> PaymentCase:
    ctx = PaymentContext(
        payment_id="pay_guard_001",
        subscription_id="sub_guard_001",
        customer_id="cust_guard_001",
        customer_name="Test User",
        customer_email="user@synthetic-test.example.com",
        customer_phone="+919800012345",
        amount_inr=amount,
        failure_category=category,
        failure_code="ERR_01",
        failure_reason="Failed payment",
        payment_method="CARD",  # type: ignore
        previous_contacts=contacts,
        opted_out=opted_out,
    )
    case = PaymentCase(context=ctx)
    case.contact_count = contacts
    return case


def test_opt_out_overrides_to_stop():
    """An opted out customer proposal must be blocked and forced to STOP."""
    engine = SafetyPolicyEngine()
    case = make_test_case(opted_out=True)
    proposal = RecoveryProposal(
        action=RecoveryAction.SEND_PAYMENT_LINK,
        confidence=0.9,
        delay_minutes=0,
        explanation="Attempting recovery",
    )
    decision = engine.evaluate(case, proposal)
    assert decision.allowed is False
    assert decision.approved_action == RecoveryAction.STOP
    assert "RULE_CUSTOMER_OPTED_OUT" in decision.reason_codes


def test_max_attempts_reached_forces_stop():
    """When contact_count >= max_attempts, further customer contact is blocked and stopped."""
    engine = SafetyPolicyEngine(Settings(MAX_CONTACT_ATTEMPTS=3))
    case = make_test_case(contacts=3)
    proposal = RecoveryProposal(
        action=RecoveryAction.SEND_PAYMENT_LINK,
        confidence=0.85,
        delay_minutes=0,
        explanation="Sending another link",
    )
    decision = engine.evaluate(case, proposal)
    assert decision.allowed is False
    assert decision.approved_action == RecoveryAction.STOP
    assert "RULE_MAX_ATTEMPTS_EXCEEDED" in decision.reason_codes


def test_high_value_mandates_human_review():
    """Amounts >= threshold mandate human review sign-off."""
    engine = SafetyPolicyEngine(Settings(HUMAN_REVIEW_THRESHOLD_INR=15000.0))
    case = make_test_case(amount=25000.0)
    proposal = RecoveryProposal(
        action=RecoveryAction.SEND_PAYMENT_LINK,
        confidence=0.88,
        delay_minutes=0,
        explanation="Payment link for large amount",
    )
    decision = engine.evaluate(case, proposal)
    assert decision.requires_human_review is True
    assert decision.allowed is False  # Held pending human review
    assert "RULE_HIGH_VALUE_THRESHOLD" in decision.reason_codes


def test_unknown_failure_mandates_human_review():
    """Unknown failures require human operator review before taking customer actions."""
    engine = SafetyPolicyEngine()
    case = make_test_case(category=FailureCategory.UNKNOWN_FAILURE)
    proposal = RecoveryProposal(
        action=RecoveryAction.SEND_PAYMENT_LINK,
        confidence=0.8,
        delay_minutes=0,
        explanation="Automated link on unknown error",
    )
    decision = engine.evaluate(case, proposal)
    assert decision.requires_human_review is True
    assert decision.approved_action == RecoveryAction.HUMAN_REVIEW
    assert "RULE_UNKNOWN_FAILURE_CATEGORY" in decision.reason_codes


def test_low_confidence_mandates_human_review():
    """Proposals with confidence < 0.70 mandate human review."""
    engine = SafetyPolicyEngine(Settings(MIN_CONFIDENCE_THRESHOLD=0.70))
    case = make_test_case()
    proposal = RecoveryProposal(
        action=RecoveryAction.WAIT_FOR_RETRY,
        confidence=0.55,
        delay_minutes=60,
        explanation="Uncertain recommendation",
    )
    decision = engine.evaluate(case, proposal)
    assert decision.requires_human_review is True
    assert "RULE_LOW_CONFIDENCE" in decision.reason_codes


def test_expired_card_retry_prohibited():
    """Proposing WAIT_FOR_RETRY on an expired card is overridden to REQUEST_METHOD_UPDATE."""
    engine = SafetyPolicyEngine()
    case = make_test_case(category=FailureCategory.EXPIRED_CARD)
    proposal = RecoveryProposal(
        action=RecoveryAction.WAIT_FOR_RETRY,
        confidence=0.85,
        delay_minutes=120,
        explanation="Retrying card",
    )
    decision = engine.evaluate(case, proposal)
    assert decision.approved_action == RecoveryAction.REQUEST_METHOD_UPDATE
    assert "RULE_EXPIRED_CARD_NO_RETRY" in decision.reason_codes
