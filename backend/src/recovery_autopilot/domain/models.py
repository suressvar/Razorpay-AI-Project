"""Domain entity models and Pydantic schemas for Recovery Autopilot."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from recovery_autopilot.domain.enums import (
    ActorType,
    CaseStatus,
    CustomerSegment,
    FailureCategory,
    PaymentMethod,
    RecoveryAction,
)


def utc_now() -> datetime:
    """Return current UTC timestamp with timezone awareness."""
    return datetime.now(timezone.utc)


class PaymentContext(BaseModel):
    """Immutable context surrounding a failed subscription payment."""

    model_config = ConfigDict(frozen=True)

    payment_id: str = Field(..., description="Razorpay payment identifier (synthetic or test mode)")
    subscription_id: str = Field(..., description="Razorpay subscription identifier")
    invoice_id: Optional[str] = Field(None, description="Associated invoice identifier")
    order_id: Optional[str] = Field(None, description="Associated Razorpay order identifier")
    payment_link_id: Optional[str] = Field(None, description="Associated Razorpay payment link identifier")
    customer_id: str = Field(..., description="Synthetic customer identifier")

    customer_name: str = Field(..., description="Synthetic customer full name")
    customer_email: str = Field(..., description="Synthetic customer email address")
    customer_phone: str = Field(..., description="Synthetic customer phone number")
    amount_inr: float = Field(..., gt=0, description="Exact subscription billing amount in INR")
    currency: str = Field("INR", description="Currency ISO code")
    failure_category: FailureCategory = Field(..., description="Classified failure category")
    failure_code: str = Field(..., description="Raw gateway or bank error code")
    failure_reason: str = Field(..., description="Human-readable gateway failure reason")
    payment_method: PaymentMethod = Field(..., description="Payment instrument used")
    customer_segment: CustomerSegment = Field(CustomerSegment.SMB, description="Customer value tier")
    previous_failures: int = Field(0, ge=0, description="Count of past failures on this subscription")
    previous_contacts: int = Field(0, ge=0, description="Count of contact attempts made")
    bank_name: Optional[str] = Field(None, description="Issuing bank name")
    bank_degraded: bool = Field(False, description="Flag indicating known bank network downtime")
    opted_out: bool = Field(False, description="Whether customer opted out of recovery communications")
    occurred_at: datetime = Field(default_factory=utc_now, description="Timestamp of payment failure")


class RecoveryProposal(BaseModel):
    """Proposal produced by an AI model.

    Safety constraint:
    The model cannot change the payment amount, invent custom tools, or bypass policies.
    """

    model_config = ConfigDict(extra="forbid")

    action: RecoveryAction = Field(..., description="Bounded recovery action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score between 0 and 1")
    delay_minutes: int = Field(0, ge=0, le=10080, description="Suggested delay in minutes before executing (max 7 days)")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable justification codes")
    explanation: str = Field(..., min_length=5, description="Concise explanation for the chosen action")
    customer_message: Optional[str] = Field(None, description="Proposed customer message draft (if applicable)")
    requires_human_approval: bool = Field(False, description="Model-signaled request for human review")
    prompt_version: Optional[str] = Field(None, description="Version of the prompt used")
    model_name: Optional[str] = Field(None, description="Identifier of the model that generated proposal")

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, codes: List[str]) -> List[str]:
        if not codes:
            return ["DEFAULT_PROPOSAL"]
        return codes


class PolicyDecision(BaseModel):
    """Deterministic evaluation outcome for an AI RecoveryProposal."""

    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    case_id: str = Field(..., description="Associated case identifier")
    allowed: bool = Field(..., description="Whether the proposed action is permitted to execute")
    approved_action: RecoveryAction = Field(..., description="Final policy-approved action (may be adjusted or overridden)")
    modified_delay_minutes: Optional[int] = Field(None, ge=0, description="Adjusted delay applied by policy")
    reason_codes: List[str] = Field(default_factory=list, description="Policy check result codes")
    requires_human_review: bool = Field(False, description="Whether human confirmation is mandated before execution")
    block_reason: Optional[str] = Field(None, description="Detailed reason if action was blocked or overridden")
    decided_at: datetime = Field(default_factory=utc_now)


class ExecutionResult(BaseModel):
    """Outcome of executing a policy-approved recovery action."""

    model_config = ConfigDict(frozen=True)

    action: RecoveryAction = Field(..., description="Action that was executed")
    external_id: Optional[str] = Field(None, description="Identifier in external system, e.g. plink_xxx")
    status: str = Field(..., description="Execution status: SUCCESS, FAILED, SIMULATED, SKIPPED")
    executed_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Redacted operational details")
    error: Optional[str] = Field(None, description="Execution error message if failed")


class PaymentOutcome(BaseModel):
    """Final business resolution of a recovery case."""

    case_id: str = Field(..., description="Case identifier")
    recovered: bool = Field(False, description="Whether the payment was successfully recovered")
    recovered_amount: float = Field(0.0, ge=0.0, description="Amount recovered in INR")
    recovered_at: Optional[datetime] = Field(None, description="Timestamp of recovery")
    failure_reason: Optional[str] = Field(None, description="Reason if abandoned or exhausted")
    time_to_recovery_hours: Optional[float] = Field(None, ge=0.0, description="Hours elapsed between failure and recovery")
    contact_count: int = Field(0, ge=0, description="Total contacts made to achieve resolution")


class AuditEvent(BaseModel):
    """Immutable audit record for every action and decision in the system."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    case_id: str = Field(..., description="Case identifier")
    timestamp: datetime = Field(default_factory=utc_now)
    actor: ActorType = Field(..., description="Entity that initiated the event")
    event_type: str = Field(..., description="Machine-readable event type identifier")
    details: Dict[str, Any] = Field(default_factory=dict, description="Redacted audit payload details")


class PromiseToPay(BaseModel):
    """Customer-committed payment arrangement details."""

    model_config = ConfigDict(frozen=True)

    promise_id: str = Field(default_factory=lambda: f"ptp_{uuid.uuid4().hex[:12]}")
    case_id: str = Field(..., description="Related recovery case ID")
    promised_datetime: datetime = Field(..., description="Customer-committed payment date/time")
    channel: str = Field(default="WHATSAPP", description="Customer-approved follow-up channel")
    consent_timestamp: datetime = Field(default_factory=utc_now, description="When customer gave verbal/text confirmation")
    status: str = Field(default="ACTIVE", description="Status: ACTIVE, FULFILLED, BROKEN, CANCELLED")
    reminder_limit: int = Field(default=1, description="Maximum reminder notifications permitted")
    notes: Optional[str] = Field(None, description="Operator or AI contextual notes")


class PaymentCase(BaseModel):
    """Aggregate root tracking a subscription payment recovery lifecycle."""

    case_id: str = Field(default_factory=lambda: f"case_{uuid.uuid4().hex[:12]}")
    context: PaymentContext = Field(..., description="Immutable context of the failed payment")
    status: CaseStatus = Field(default=CaseStatus.NEW, description="Current lifecycle state")
    current_proposal: Optional[RecoveryProposal] = Field(None, description="Latest AI proposal")
    latest_decision: Optional[PolicyDecision] = Field(None, description="Latest policy decision")
    latest_action_result: Optional[ExecutionResult] = Field(None, description="Latest execution result")
    promise_to_pay: Optional[PromiseToPay] = Field(None, description="Active Promise-to-Pay arrangement if negotiated")
    outcome: Optional[PaymentOutcome] = Field(None, description="Final outcome if completed")
    action_version: int = Field(1, description="Sequential action proposal version for binding human approvals")
    contact_count: int = Field(0, ge=0, description="Number of recovery outreach contacts made")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def record_contact(self) -> None:
        """Increment customer contact counter."""
        self.contact_count += 1
        self.updated_at = utc_now()

