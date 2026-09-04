"""Workflow and state machine exports."""

from recovery_autopilot.workflows.protocols import ActionExecutorProtocol, CaseRepositoryProtocol
from recovery_autopilot.workflows.recovery_workflow import RecoveryWorkflow
from recovery_autopilot.workflows.state_machine import (
    LEGAL_TRANSITIONS,
    CaseStateMachine,
    IllegalStateTransitionError,
)

__all__ = [
    "ActionExecutorProtocol",
    "CaseRepositoryProtocol",
    "CaseStateMachine",
    "IllegalStateTransitionError",
    "LEGAL_TRANSITIONS",
    "RecoveryWorkflow",
]
