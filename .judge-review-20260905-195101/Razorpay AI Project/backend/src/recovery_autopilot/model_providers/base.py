"""Base protocol and common types for AI model providers."""

from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, RecoveryProposal


class DiagnosisResult(BaseModel):
    """Structured root-cause diagnosis output from an AI model."""

    failure_category: FailureCategory = Field(..., description="Inferred failure category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in diagnosis")
    is_transient: bool = Field(False, description="Whether failure appears to be transient/infrastructure")
    evidence_signals: list[str] = Field(default_factory=list, description="Observed evidence factors")
    reasoning: str = Field(..., description="Concise explanation of diagnosis")
    suggested_action: RecoveryAction = Field(..., description="Preliminary recovery recommendation")


class ProviderError(Exception):
    """Base exception for model provider errors."""

    def __init__(self, message: str, provider_name: str, recoverable: bool = True):
        super().__init__(message)
        self.provider_name = provider_name
        self.recoverable = recoverable


@runtime_checkable
class ModelProvider(Protocol):
    """Asynchronous protocol implemented by all model providers."""

    provider_name: str
    model_identifier: str

    async def diagnose_failure(self, case: PaymentCase) -> DiagnosisResult:
        """Analyze payment context and return structured root-cause diagnosis."""
        ...

    async def propose_recovery(self, case: PaymentCase) -> RecoveryProposal:
        """Formulate a bounded RecoveryProposal strictly adhering to domain schema."""
        ...

    async def draft_customer_message(self, case: PaymentCase, action: RecoveryAction) -> Optional[str]:
        """Draft a polite, compliant, and empathetic customer communication."""
        ...
