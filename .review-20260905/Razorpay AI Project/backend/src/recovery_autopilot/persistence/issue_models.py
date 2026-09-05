"""SQLAlchemy ORM models for customer issue tracking persistence."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from recovery_autopilot.persistence.models import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CustomerIssueRecord(Base):
    """Customer issue aggregate persistence."""

    __tablename__ = "customer_issues"

    issue_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW", index=True)
    environment: Mapped[str] = mapped_column(String(8), nullable=False, default="TEST")

    # Customer context
    merchant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    # Related entity IDs
    payment_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    refund_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payment_link_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    case_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Ownership
    owner: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Reported problem
    reported_symptoms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_behavior: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_behavior: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Serialized JSON blobs
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    causes_json: Mapped[str] = mapped_column(Text, default="[]")
    actions_json: Mapped[str] = mapped_column(Text, default="[]")
    communications_json: Mapped[str] = mapped_column(Text, default="[]")
    timeline_json: Mapped[str] = mapped_column(Text, default="[]")

    # Resolution
    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EmailDraftRecord(Base):
    """Persisted email drafts for the Copilot email workflow."""

    __tablename__ = "email_drafts"

    draft_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    issue_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    case_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    template_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    recipient_email: Mapped[str] = mapped_column(String(128), nullable=False)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Send tracking
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)  # DRAFT, QUEUED, ACCEPTED, DELIVERED, FAILED
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[str] = mapped_column(String(64), default="copilot")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
