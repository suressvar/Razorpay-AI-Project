"""Unit tests for the recovery case lifecycle state machine."""

import pytest

from recovery_autopilot.domain.enums import ActorType, CaseStatus
from recovery_autopilot.domain.models import PaymentCase, PaymentContext
from recovery_autopilot.workflows.state_machine import CaseStateMachine, IllegalStateTransitionError


def make_case(status: CaseStatus = CaseStatus.NEW) -> PaymentCase:
    ctx = PaymentContext(
        payment_id="pay_sm_001",
        subscription_id="sub_sm_001",
        customer_id="cust_sm_001",
        customer_name="Test Customer",
        customer_email="sm@synthetic-test.example.com",
        customer_phone="+919800099999",
        amount_inr=1999.0,
        failure_category="BANK_TIMEOUT",  # type: ignore
        failure_code="TIMEOUT",
        failure_reason="Bank timeout",
        payment_method="UPI",  # type: ignore
    )
    return PaymentCase(context=ctx, status=status)


def test_legal_lifecycle_transitions():
    """Verify standard sequence: NEW -> DIAGNOSING -> AWAITING_POLICY -> ACTION_IN_PROGRESS -> MONITORING -> RECOVERED."""
    case = make_case(CaseStatus.NEW)

    ev1 = CaseStateMachine.transition(case, CaseStatus.DIAGNOSING, actor=ActorType.AI)
    assert case.status == CaseStatus.DIAGNOSING
    assert ev1.event_type == "STATUS_CHANGED"

    CaseStateMachine.transition(case, CaseStatus.AWAITING_POLICY, actor=ActorType.POLICY)
    assert case.status == CaseStatus.AWAITING_POLICY

    CaseStateMachine.transition(case, CaseStatus.ACTION_IN_PROGRESS, actor=ActorType.EXECUTOR)
    assert case.status == CaseStatus.ACTION_IN_PROGRESS

    CaseStateMachine.transition(case, CaseStatus.MONITORING, actor=ActorType.EXECUTOR)
    assert case.status == CaseStatus.MONITORING

    CaseStateMachine.transition(case, CaseStatus.RECOVERED, actor=ActorType.POLICY)
    assert case.status == CaseStatus.RECOVERED


def test_illegal_transition_blocked():
    """Jumping from NEW directly to RECOVERED or MONITORING must raise IllegalStateTransitionError."""
    case = make_case(CaseStatus.NEW)

    with pytest.raises(IllegalStateTransitionError) as exc_info:
        CaseStateMachine.transition(case, CaseStatus.RECOVERED, actor=ActorType.AI)

    assert exc_info.value.current_status == CaseStatus.NEW
    assert exc_info.value.target_status == CaseStatus.RECOVERED
    assert case.status == CaseStatus.NEW  # Status remains uncorrupted


def test_terminal_state_immutability():
    """Terminal states (RECOVERED, EXHAUSTED, OPTED_OUT, STOPPED) must not allow further transitions."""
    for terminal in [CaseStatus.RECOVERED, CaseStatus.EXHAUSTED, CaseStatus.OPTED_OUT, CaseStatus.STOPPED]:
        case = make_case(terminal)
        with pytest.raises(IllegalStateTransitionError):
            CaseStateMachine.transition(case, CaseStatus.DIAGNOSING, actor=ActorType.AI)
