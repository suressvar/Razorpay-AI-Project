"""SQLAlchemy ORM models for PostgreSQL and SQLite persistence."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class WebhookEventRecord(Base):
    """Raw received webhook events for idempotency, retry, and asynchronous queuing."""

    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="received", index=True)  # received, queued, processing, completed, unmatched, failed, dead_letter
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class UnmatchedWebhookRecord(Base):
    """Unmatched webhook events stored for investigation without altering payment cases."""

    __tablename__ = "unmatched_webhooks"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signature: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class PaymentCaseRecord(Base):
    """Payment recovery cases aggregate persistence."""

    __tablename__ = "payment_cases"

    case_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    payment_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    payment_link_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(128), nullable=False)

    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_inr: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    failure_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    failure_code: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_segment: Mapped[str] = mapped_column(String(32), default="SMB")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    bank_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bank_degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)

    # Serialized JSON blobs for proposal, decision, and action
    current_proposal_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latest_decision_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latest_action_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    promise_to_pay_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class RecoveryActionRecord(Base):
    """Execution records for recovery interventions."""

    __tablename__ = "recovery_actions"

    action_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PromiseToPayRecord(Base):
    """Persistent customer commitment to pay at a future scheduled time."""

    __tablename__ = "promises_to_pay"

    promise_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    promised_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="WHATSAPP")
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    reminder_limit: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VoiceSessionRecord(Base):
    """Voice recovery session metadata and redacted transcript record."""

    __tablename__ = "voice_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(64), nullable=False, default="AWAITING_CONSENT")
    consent_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="hinglish")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    detected_intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    intent_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    proposed_action: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_to_human: Mapped[bool] = mapped_column(Boolean, default=False)
    redacted_transcript_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEventRecord(Base):
    """Immutable audit trail for compliance and dashboard timeline."""

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
