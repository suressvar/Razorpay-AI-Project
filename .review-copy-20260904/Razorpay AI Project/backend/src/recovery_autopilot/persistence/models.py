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
    """Raw received webhook events for idempotency and replay."""

    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PaymentCaseRecord(Base):
    """Payment recovery cases aggregate persistence."""

    __tablename__ = "payment_cases"

    case_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    payment_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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


class AuditEventRecord(Base):
    """Immutable audit trail for compliance and dashboard timeline."""

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
