"""Unit tests for immediate stop conditions in the recovery workflow."""

import pytest

from recovery_autopilot.config import Settings
from recovery_autopilot.domain.enums import CaseStatus, FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import ExecutionResult, PaymentCase, PaymentContext
from recovery_autopilot.model_providers.fake import FakeModelProvider
from recovery_autopilot.policies.guardrails import SafetyPolicyEngine
from recovery_autopilot.workflows.recovery_workflow import RecoveryWorkflow


class MockExecutor:
    """Mock action executor returning simulated success."""

    async def execute_action(self, case: PaymentCase, action: RecoveryAction, customer_message=None):
        return ExecutionResult(action=action, status="SUCCESS")


@pytest.fixture
def workflow():
    provider = FakeModelProvider()
    policy = SafetyPolicyEngine(Settings(MAX_CONTACT_ATTEMPTS=3, HUMAN_REVIEW_THRESHOLD_INR=15000.0))
    executor = MockExecutor()
    return RecoveryWorkflow(provider=provider, policy_engine=policy, executor=executor)


@pytest.mark.asyncio
async def test_immediate_stop_on_opt_out(workflow):
    """If customer is opted out, case terminates immediately in OPTED_OUT without diagnosis."""
    ctx = PaymentContext(
        payment_id="pay_opt_001",
        subscription_id="sub_opt_001",
        customer_id="cust_opt_001",
        customer_name="Opted Out User",
        customer_email="opt@synthetic-test.example.com",
        customer_phone="+919800000000",
        amount_inr=999.0,
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="FAILED",
        failure_reason="Failed",
        payment_method="UPI",  # type: ignore
        opted_out=True,
    )
    case = await workflow.process_failed_payment(ctx)
    assert case.status == CaseStatus.OPTED_OUT
    assert case.contact_count == 0


@pytest.mark.asyncio
async def test_immediate_stop_on_payment_captured(workflow):
    """When a payment is captured while monitoring, case transitions immediately to RECOVERED."""
    ctx = PaymentContext(
        payment_id="pay_succ_001",
        subscription_id="sub_succ_001",
        customer_id="cust_succ_001",
        customer_name="Success User",
        customer_email="succ@synthetic-test.example.com",
        customer_phone="+919800000001",
        amount_inr=1999.0,
        failure_category=FailureCategory.BANK_TIMEOUT,
        failure_code="FAILED",
        failure_reason="Timeout",
        payment_method="CARD",  # type: ignore
    )
    case = await workflow.process_failed_payment(ctx)
    assert case.status in [CaseStatus.MONITORING, CaseStatus.SCHEDULED]

    outcome = await workflow.handle_payment_success(case, payment_id="pay_captured_123", amount_inr=1999.0)
    assert outcome.recovered is True
    assert outcome.recovered_amount == 1999.0
    assert case.status == CaseStatus.RECOVERED


@pytest.mark.asyncio
async def test_human_rejection_stops_case(workflow):
    """When a human operator rejects an AWAITING_APPROVAL case, it transitions to STOPPED."""
    ctx = PaymentContext(
        payment_id="pay_high_001",
        subscription_id="sub_high_001",
        customer_id="cust_high_001",
        customer_name="High Value User",
        customer_email="high@synthetic-test.example.com",
        customer_phone="+919800000002",
        amount_inr=25000.0,  # High value triggers AWAITING_APPROVAL
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="FAILED",
        failure_reason="Insufficient funds",
        payment_method="CARD",  # type: ignore
    )
    case = await workflow.process_failed_payment(ctx)
    assert case.status == CaseStatus.AWAITING_APPROVAL

    await workflow.handle_human_rejection(case, operator_id="ops_admin_1", reason="Customer requested subscription cancellation")
    assert case.status == CaseStatus.STOPPED
