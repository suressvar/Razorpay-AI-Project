"""Recovery lifecycle workflow orchestrating diagnosis, safety policy, and execution."""

import logging
from typing import Optional

from recovery_autopilot.domain.enums import ActorType, CaseStatus, RecoveryAction
from recovery_autopilot.domain.models import (
    AuditEvent,
    ExecutionResult,
    PaymentCase,
    PaymentContext,
    PaymentOutcome,
    utc_now,
)
from recovery_autopilot.model_providers.base import ModelProvider
from recovery_autopilot.policies.guardrails import SafetyPolicyEngine
from recovery_autopilot.workflows.protocols import ActionExecutorProtocol, CaseRepositoryProtocol
from recovery_autopilot.workflows.state_machine import CaseStateMachine

logger = logging.getLogger("recovery_autopilot.workflows.recovery_workflow")


class RecoveryWorkflow:
    """Orchestrates end-to-end recovery lifecycle while maintaining safety invariants."""

    def __init__(
        self,
        provider: ModelProvider,
        policy_engine: SafetyPolicyEngine,
        executor: ActionExecutorProtocol,
        repository: Optional[CaseRepositoryProtocol] = None,
    ):
        self.provider = provider
        self.policy_engine = policy_engine
        self.executor = executor
        self.repository = repository

    async def _record_audit(self, event: AuditEvent) -> None:
        if self.repository:
            await self.repository.record_audit(event)

    async def _save_case(self, case: PaymentCase) -> None:
        if self.repository:
            await self.repository.save_case(case)

    async def process_failed_payment(self, context: PaymentContext) -> PaymentCase:
        """Entry point for new payment failure: diagnose -> policy -> schedule/act."""
        case = PaymentCase(context=context, status=CaseStatus.NEW)
        await self._save_case(case)

        audit_new = AuditEvent(
            case_id=case.case_id,
            actor=ActorType.WEBHOOK,
            event_type="PAYMENT_FAILURE_INGESTED",
            details={
                "payment_id": context.payment_id,
                "amount_inr": context.amount_inr,
                "category": context.failure_category.value,
            },
        )
        await self._record_audit(audit_new)

        # Immediate stop if opted out
        if context.opted_out:
            audit_opt = CaseStateMachine.transition(
                case, CaseStatus.OPTED_OUT, actor=ActorType.POLICY, reason="Customer opted out"
            )
            await self._record_audit(audit_opt)
            await self._save_case(case)
            return case

        # Transition to DIAGNOSING
        audit_diag = CaseStateMachine.transition(case, CaseStatus.DIAGNOSING, actor=ActorType.AI)
        await self._record_audit(audit_diag)

        # AI Proposal Generation
        try:
            proposal = await self.provider.propose_recovery(case)
            case.current_proposal = proposal
            audit_prop = AuditEvent(
                case_id=case.case_id,
                actor=ActorType.AI,
                event_type="PROPOSAL_GENERATED",
                details=proposal.model_dump(),
            )
            await self._record_audit(audit_prop)
        except Exception as e:
            logger.error("AI proposal failed: %s; transitioning to ERROR", str(e))
            CaseStateMachine.transition(case, CaseStatus.ERROR, actor=ActorType.AI, reason=str(e))
            await self._save_case(case)
            return case

        # Transition to AWAITING_POLICY
        audit_pol = CaseStateMachine.transition(case, CaseStatus.AWAITING_POLICY, actor=ActorType.POLICY)
        await self._record_audit(audit_pol)

        # Deterministic Policy Evaluation
        decision = self.policy_engine.evaluate(case, proposal)
        case.latest_decision = decision
        audit_dec = AuditEvent(
            case_id=case.case_id,
            actor=ActorType.POLICY,
            event_type="POLICY_DECIDED",
            details=decision.model_dump(),
        )
        await self._record_audit(audit_dec)

        # Route based on policy decision
        if decision.approved_action == RecoveryAction.STOP:
            audit_stop = CaseStateMachine.transition(
                case, CaseStatus.STOPPED, actor=ActorType.POLICY, reason="Policy mandated STOP"
            )
            await self._record_audit(audit_stop)

        elif decision.requires_human_review:
            # Case is held for human approval
            audit_hold = CaseStateMachine.transition(
                case, CaseStatus.AWAITING_APPROVAL, actor=ActorType.POLICY, reason=decision.block_reason or "Human review mandated"
            )
            await self._record_audit(audit_hold)

        elif decision.modified_delay_minutes and decision.modified_delay_minutes > 0:
            # Action is scheduled with delay
            audit_sched = CaseStateMachine.transition(
                case, CaseStatus.SCHEDULED, actor=ActorType.POLICY, reason=f"Delayed execution by {decision.modified_delay_minutes}m"
            )
            await self._record_audit(audit_sched)

        else:
            # Execute action immediately
            await self.execute_approved_action(case)

        await self._save_case(case)
        return case

    async def execute_approved_action(self, case: PaymentCase) -> ExecutionResult:
        """Execute the policy-approved recovery action via executor."""
        action = case.latest_decision.approved_action if case.latest_decision else RecoveryAction.WAIT_FOR_RETRY
        msg = case.current_proposal.customer_message if case.current_proposal else None

        audit_in_prog = CaseStateMachine.transition(case, CaseStatus.ACTION_IN_PROGRESS, actor=ActorType.EXECUTOR)
        await self._record_audit(audit_in_prog)

        result = await self.executor.execute_action(case, action, customer_message=msg)
        case.latest_action_result = result

        if action in [RecoveryAction.SEND_PAYMENT_LINK, RecoveryAction.REQUEST_METHOD_UPDATE, RecoveryAction.SEND_REMINDER]:
            case.record_contact()

        audit_exec = AuditEvent(
            case_id=case.case_id,
            actor=ActorType.EXECUTOR,
            event_type="ACTION_EXECUTED",
            details=result.model_dump(),
        )
        await self._record_audit(audit_exec)

        # Transition to MONITORING
        audit_mon = CaseStateMachine.transition(case, CaseStatus.MONITORING, actor=ActorType.EXECUTOR)
        await self._record_audit(audit_mon)
        await self._save_case(case)

        return result

    async def handle_human_approval(self, case: PaymentCase, operator_id: str) -> None:
        """Human operator signs off on a pending high-value or low-confidence proposal."""
        if case.status != CaseStatus.AWAITING_APPROVAL:
            raise ValueError(f"Case {case.case_id} is in status {case.status.value}, not AWAITING_APPROVAL")

        audit_apprv = AuditEvent(
            case_id=case.case_id,
            actor=ActorType.HUMAN,
            event_type="HUMAN_APPROVAL_GRANTED",
            details={"operator_id": operator_id},
        )
        await self._record_audit(audit_apprv)

        await self.execute_approved_action(case)

    async def handle_human_rejection(self, case: PaymentCase, operator_id: str, reason: str) -> None:
        """Human operator rejects proposed recovery action."""
        if case.status != CaseStatus.AWAITING_APPROVAL:
            raise ValueError(f"Case {case.case_id} is in status {case.status.value}, not AWAITING_APPROVAL")

        audit_rej = AuditEvent(
            case_id=case.case_id,
            actor=ActorType.HUMAN,
            event_type="HUMAN_APPROVAL_REJECTED",
            details={"operator_id": operator_id, "reason": reason},
        )
        await self._record_audit(audit_rej)

        audit_stop = CaseStateMachine.transition(case, CaseStatus.STOPPED, actor=ActorType.HUMAN, reason=f"Rejected: {reason}")
        await self._record_audit(audit_stop)
        await self._save_case(case)

    async def handle_payment_success(self, case: PaymentCase, payment_id: str, amount_inr: float) -> PaymentOutcome:
        """Handle incoming payment.captured or order.paid: immediate stop condition."""
        outcome = PaymentOutcome(
            case_id=case.case_id,
            recovered=True,
            recovered_amount=amount_inr,
            recovered_at=utc_now(),
            contact_count=case.contact_count,
        )
        case.outcome = outcome

        audit_succ = AuditEvent(
            case_id=case.case_id,
            actor=ActorType.WEBHOOK,
            event_type="PAYMENT_CAPTURED_SUCCESS",
            details={"payment_id": payment_id, "amount_inr": amount_inr},
        )
        await self._record_audit(audit_succ)

        audit_trans = CaseStateMachine.transition(
            case, CaseStatus.RECOVERED, actor=ActorType.POLICY, reason="Payment successfully captured"
        )
        await self._record_audit(audit_trans)
        await self._save_case(case)

        return outcome
