"""Domain models for Copilot customer issue tracking and investigation."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums ---

class IssueStatus(str, Enum):
    """Issue lifecycle states."""
    NEW = "NEW"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_INFO = "AWAITING_INFO"
    ACTION_IN_PROGRESS = "ACTION_IN_PROGRESS"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueCategory(str, Enum):
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    DEBIT_WITHOUT_CONFIRMATION = "DEBIT_WITHOUT_CONFIRMATION"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    ORDER_PAYMENT_MISMATCH = "ORDER_PAYMENT_MISMATCH"
    AUTH_CAPTURE_DISCREPANCY = "AUTH_CAPTURE_DISCREPANCY"
    INCORRECT_AMOUNT = "INCORRECT_AMOUNT"
    EXPIRED_PAYMENT_LINK = "EXPIRED_PAYMENT_LINK"
    WEBHOOK_ISSUE = "WEBHOOK_ISSUE"
    INTEGRATION_ERROR = "INTEGRATION_ERROR"
    CONFIG_MISMATCH = "CONFIG_MISMATCH"
    REFUND_DELAY = "REFUND_DELAY"
    REFUND_FAILURE = "REFUND_FAILURE"
    SETTLEMENT_DISCREPANCY = "SETTLEMENT_DISCREPANCY"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class CommunicationStatus(str, Enum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    ACCEPTED = "ACCEPTED"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class CommunicationChannel(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class EnvironmentMode(str, Enum):
    TEST = "TEST"
    LIVE = "LIVE"


# --- Domain Models ---

class IssueEvidence(BaseModel):
    """A single piece of evidence collected during investigation."""
    evidence_id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:10]}")
    source: str = Field(..., description="Where this evidence came from: payment_record, webhook, api_response, user_report, log")
    description: str = Field(..., description="Plain-language summary of what was found")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Structured data backing this evidence")
    timestamp: datetime = Field(default_factory=utc_now)
    confidence: ConfidenceLevel = Field(ConfidenceLevel.MEDIUM)


class IssueCause(BaseModel):
    """A possible cause identified during investigation."""
    cause_id: str = Field(default_factory=lambda: f"cause_{uuid.uuid4().hex[:8]}")
    description: str = Field(..., description="Plain-language description of the suspected cause")
    confidence: ConfidenceLevel = Field(...)
    supporting_evidence: List[str] = Field(default_factory=list, description="Evidence IDs that support this cause")
    contradicting_evidence: List[str] = Field(default_factory=list, description="Evidence IDs contradicting this cause")
    missing_evidence: List[str] = Field(default_factory=list, description="What additional data would confirm/deny this")
    recommended_action: Optional[str] = Field(None, description="Recommended diagnostic check or fix")
    is_confirmed: bool = Field(False, description="Whether this cause has been confirmed vs hypothesis")


class IssueAction(BaseModel):
    """An action attempted as part of issue resolution."""
    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:10]}")
    action_type: str = Field(..., description="Type: investigate_payment, create_payment_link, prepare_refund, send_email, escalate, etc.")
    description: str = Field(..., description="What this action does")
    status: ActionStatus = Field(ActionStatus.PENDING)
    result: Optional[Dict[str, Any]] = Field(None, description="Structured result of the action")
    error_message: Optional[str] = Field(None)
    requires_approval: bool = Field(False)
    executed_by: str = Field("copilot", description="Who triggered this: copilot, operator, system")
    executed_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=utc_now)


class IssueCommunication(BaseModel):
    """A customer communication associated with the issue."""
    communication_id: str = Field(default_factory=lambda: f"comm_{uuid.uuid4().hex[:10]}")
    channel: CommunicationChannel = Field(CommunicationChannel.EMAIL)
    direction: str = Field("outbound", description="inbound or outbound")
    recipient: str = Field(..., description="Email address or phone number")
    subject: Optional[str] = Field(None)
    body: str = Field(..., description="Message content")
    template_used: Optional[str] = Field(None, description="Template ID if generated from template")
    provider_message_id: Optional[str] = Field(None, description="External message ID from email/SMS provider")
    status: CommunicationStatus = Field(CommunicationStatus.DRAFT)
    idempotency_key: Optional[str] = Field(None, description="Prevents duplicate sends on retry")
    sent_at: Optional[datetime] = Field(None)
    created_at: datetime = Field(default_factory=utc_now)


class IssueTimelineEntry(BaseModel):
    """A single event in the issue timeline."""
    entry_id: str = Field(default_factory=lambda: f"tle_{uuid.uuid4().hex[:10]}")
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: str = Field(..., description="status_change, evidence_added, action_taken, communication_sent, note_added")
    actor: str = Field(..., description="copilot, operator:{id}, system, webhook")
    summary: str = Field(..., description="Short description of what happened")
    details: Optional[Dict[str, Any]] = Field(None)


class CustomerIssue(BaseModel):
    """Aggregate root: a customer issue being tracked and investigated by the Copilot."""

    issue_id: str = Field(default_factory=lambda: f"iss_{uuid.uuid4().hex[:12]}")
    title: str = Field(..., description="Brief issue title")
    category: IssueCategory = Field(IssueCategory.GENERAL_INQUIRY)
    severity: IssueSeverity = Field(IssueSeverity.MEDIUM)
    status: IssueStatus = Field(IssueStatus.NEW)
    environment: EnvironmentMode = Field(EnvironmentMode.TEST)

    # Customer context
    merchant_id: Optional[str] = Field(None)
    customer_id: Optional[str] = Field(None)
    customer_name: Optional[str] = Field(None)
    customer_email: Optional[str] = Field(None)

    # Related entity IDs
    payment_id: Optional[str] = Field(None)
    order_id: Optional[str] = Field(None)
    refund_id: Optional[str] = Field(None)
    payment_link_id: Optional[str] = Field(None)
    case_id: Optional[str] = Field(None, description="Link to existing PaymentCase if applicable")

    # Ownership and SLA
    owner: Optional[str] = Field(None, description="Operator or copilot session owning this issue")
    sla_deadline: Optional[datetime] = Field(None)
    next_action: Optional[str] = Field(None, description="What should happen next")

    # Reported problem
    reported_symptoms: Optional[str] = Field(None, description="What the customer reported")
    expected_behavior: Optional[str] = Field(None, description="What should have happened")
    actual_behavior: Optional[str] = Field(None, description="What actually happened")

    # Investigation data
    evidence: List[IssueEvidence] = Field(default_factory=list)
    possible_causes: List[IssueCause] = Field(default_factory=list)
    actions: List[IssueAction] = Field(default_factory=list)
    communications: List[IssueCommunication] = Field(default_factory=list)
    timeline: List[IssueTimelineEntry] = Field(default_factory=list)

    # Resolution
    resolution_summary: Optional[str] = Field(None)
    resolution_verified: bool = Field(False)
    resolution_evidence: Optional[str] = Field(None, description="Evidence that the resolution worked")

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def add_evidence(self, evidence: IssueEvidence) -> None:
        self.evidence.append(evidence)
        self.timeline.append(IssueTimelineEntry(
            event_type="evidence_added",
            actor="copilot",
            summary=f"Evidence collected: {evidence.description[:80]}",
            details={"evidence_id": evidence.evidence_id, "source": evidence.source},
        ))
        self.updated_at = utc_now()

    def add_cause(self, cause: IssueCause) -> None:
        self.possible_causes.append(cause)
        self.timeline.append(IssueTimelineEntry(
            event_type="cause_identified",
            actor="copilot",
            summary=f"Possible cause ({cause.confidence.value}): {cause.description[:80]}",
            details={"cause_id": cause.cause_id, "confidence": cause.confidence.value},
        ))
        self.updated_at = utc_now()

    def add_action(self, action: IssueAction) -> None:
        self.actions.append(action)
        self.timeline.append(IssueTimelineEntry(
            event_type="action_taken",
            actor=action.executed_by,
            summary=f"Action: {action.description[:80]} [{action.status.value}]",
            details={"action_id": action.action_id, "action_type": action.action_type, "status": action.status.value},
        ))
        self.updated_at = utc_now()

    def add_communication(self, comm: IssueCommunication) -> None:
        self.communications.append(comm)
        self.timeline.append(IssueTimelineEntry(
            event_type="communication_sent",
            actor="copilot",
            summary=f"{comm.channel.value} to {comm.recipient}: {comm.subject or comm.body[:50]}",
            details={"communication_id": comm.communication_id, "status": comm.status.value},
        ))
        self.updated_at = utc_now()

    def transition_status(self, new_status: IssueStatus, actor: str = "copilot", reason: str = "") -> None:
        old_status = self.status
        self.status = new_status
        self.timeline.append(IssueTimelineEntry(
            event_type="status_change",
            actor=actor,
            summary=f"Status: {old_status.value} → {new_status.value}" + (f" ({reason})" if reason else ""),
            details={"from": old_status.value, "to": new_status.value, "reason": reason},
        ))
        self.updated_at = utc_now()
