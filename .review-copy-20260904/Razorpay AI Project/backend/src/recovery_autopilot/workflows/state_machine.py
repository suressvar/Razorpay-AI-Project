"""Deterministic state machine governing recovery case lifecycle."""

from typing import Dict, Set

from recovery_autopilot.domain.enums import ActorType, CaseStatus
from recovery_autopilot.domain.models import AuditEvent, PaymentCase, utc_now


class IllegalStateTransitionError(ValueError):
    """Raised when an illegal lifecycle state transition is attempted."""

    def __init__(self, current_status: CaseStatus, target_status: CaseStatus, reason: str = ""):
        message = f"Illegal transition from {current_status.value} to {target_status.value}. {reason}".strip()
        super().__init__(message)
        self.current_status = current_status
        self.target_status = target_status


# Legal State Transition Table
LEGAL_TRANSITIONS: Dict[CaseStatus, Set[CaseStatus]] = {
    CaseStatus.NEW: {
        CaseStatus.DIAGNOSING,
        CaseStatus.STOPPED,
        CaseStatus.OPTED_OUT,
        CaseStatus.ERROR,
    },
    CaseStatus.DIAGNOSING: {
        CaseStatus.AWAITING_POLICY,
        CaseStatus.ERROR,
        CaseStatus.STOPPED,
    },
    CaseStatus.AWAITING_POLICY: {
        CaseStatus.SCHEDULED,
        CaseStatus.AWAITING_APPROVAL,
        CaseStatus.ACTION_IN_PROGRESS,
        CaseStatus.OPTED_OUT,
        CaseStatus.STOPPED,
        CaseStatus.ERROR,
    },
    CaseStatus.SCHEDULED: {
        CaseStatus.ACTION_IN_PROGRESS,
        CaseStatus.RECOVERED,
        CaseStatus.OPTED_OUT,
        CaseStatus.STOPPED,
        CaseStatus.ERROR,
    },
    CaseStatus.AWAITING_APPROVAL: {
        CaseStatus.SCHEDULED,
        CaseStatus.ACTION_IN_PROGRESS,
        CaseStatus.STOPPED,
        CaseStatus.RECOVERED,
        CaseStatus.OPTED_OUT,
        CaseStatus.ERROR,
    },
    CaseStatus.ACTION_IN_PROGRESS: {
        CaseStatus.MONITORING,
        CaseStatus.RECOVERED,
        CaseStatus.ERROR,
        CaseStatus.STOPPED,
    },
    CaseStatus.MONITORING: {
        CaseStatus.RECOVERED,
        CaseStatus.EXHAUSTED,
        CaseStatus.PROMISED_TO_PAY,
        CaseStatus.DIAGNOSING,  # Next round of recovery
        CaseStatus.OPTED_OUT,
        CaseStatus.STOPPED,
        CaseStatus.ERROR,
    },
    CaseStatus.PROMISED_TO_PAY: {
        CaseStatus.MONITORING,
        CaseStatus.RECOVERED,
        CaseStatus.EXHAUSTED,
        CaseStatus.OPTED_OUT,
        CaseStatus.STOPPED,
        CaseStatus.ERROR,
    },
    # Terminal States: No departures allowed
    CaseStatus.RECOVERED: set(),
    CaseStatus.EXHAUSTED: set(),
    CaseStatus.OPTED_OUT: set(),
    CaseStatus.STOPPED: set(),
    CaseStatus.ERROR: {CaseStatus.DIAGNOSING},  # Operator can retry errored cases
}


class CaseStateMachine:
    """State machine validator and manager for PaymentCase lifecycle."""

    @staticmethod
    def can_transition(current: CaseStatus, target: CaseStatus) -> bool:
        """Check if transition from current to target status is legal."""
        return target in LEGAL_TRANSITIONS.get(current, set())

    @classmethod
    def transition(
        cls,
        case: PaymentCase,
        target_status: CaseStatus,
        actor: ActorType = ActorType.POLICY,
        reason: str = "",
    ) -> AuditEvent:
        """Transition case to a new status or fail safely with an audit event."""
        current_status = case.status

        if not cls.can_transition(current_status, target_status):
            raise IllegalStateTransitionError(current_status, target_status, reason)

        # Apply transition
        case.status = target_status
        case.updated_at = utc_now()

        # Generate successful transition audit event
        return AuditEvent(
            case_id=case.case_id,
            actor=actor,
            event_type="STATUS_CHANGED",
            details={
                "from_status": current_status.value,
                "to_status": target_status.value,
                "reason": reason,
            },
        )
