"""Abstract interfaces and protocols for execution and persistence."""

from typing import Optional, Protocol, runtime_checkable

from recovery_autopilot.domain.enums import RecoveryAction
from recovery_autopilot.domain.models import AuditEvent, ExecutionResult, PaymentCase


@runtime_checkable
class ActionExecutorProtocol(Protocol):
    """Protocol for executing policy-approved recovery interventions."""

    async def execute_action(
        self,
        case: PaymentCase,
        action: RecoveryAction,
        customer_message: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute recovery action in external system or simulator."""
        ...


@runtime_checkable
class CaseRepositoryProtocol(Protocol):
    """Protocol for persisting case state and audit events."""

    async def get_case(self, case_id: str) -> Optional[PaymentCase]:
        """Fetch case by ID."""
        ...

    async def save_case(self, case: PaymentCase) -> None:
        """Persist updated case state."""
        ...

    async def record_audit(self, event: AuditEvent) -> None:
        """Append immutable audit log entry."""
        ...
