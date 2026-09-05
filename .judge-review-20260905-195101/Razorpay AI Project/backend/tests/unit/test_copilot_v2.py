"""Unit tests for Copilot V2 domain models, repository, services, and reasoning engine."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from recovery_autopilot.domain.issue_models import (
    CustomerIssue,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    IssueEvidence,
    IssueCause,
    IssueAction,
    IssueCommunication,
    ConfidenceLevel,
    ActionStatus,
    CommunicationStatus,
    EnvironmentMode,
)
from recovery_autopilot.domain.enums import CaseStatus
from recovery_autopilot.persistence.models import Base, PaymentCaseRecord
from recovery_autopilot.persistence.issue_models import CustomerIssueRecord, EmailDraftRecord
from recovery_autopilot.persistence.issue_repository import IssueRepository
from recovery_autopilot.services.email_service import email_service
from recovery_autopilot.services.refund_service import refund_service
from recovery_autopilot.services.automation_service import automation_service
from recovery_autopilot.services.copilot_reasoning import copilot_reasoning


@pytest_asyncio.fixture
async def async_db_session():
    """In-memory SQLite test database fixture."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_issue_models_creation():
    """Verify issue domain models instantiate and serialize cleanly."""
    issue = CustomerIssue(
        title="Payment Failed for Priya Sharma",
        category=IssueCategory.PAYMENT_FAILURE,
        severity=IssueSeverity.HIGH,
        merchant_id="merch_001",
        customer_email="priya@example.com",
        payment_id="pay_fail_123",
        reported_symptoms="Card declined with error code BAD_REQUEST",
    )
    assert issue.issue_id.startswith("iss_")
    assert issue.status == IssueStatus.NEW
    assert issue.severity == IssueSeverity.HIGH

    # Add evidence and cause
    issue.add_evidence(
        IssueEvidence(
            source="payment_record",
            description="Payment marked as failed in gateway",
            raw_data={"status": "failed", "gateway_error": "INSUFFICIENT_FUNDS"},
            confidence=ConfidenceLevel.HIGH,
        )
    )
    issue.add_cause(
        IssueCause(
            description="Customer Account Insufficient Balance",
            confidence=ConfidenceLevel.HIGH,
            supporting_evidence=[issue.evidence[0].evidence_id],
            recommended_action="Issue smart retry link via WhatsApp.",
        )
    )
    dumped = issue.model_dump()
    assert len(dumped["evidence"]) == 1
    assert len(dumped["possible_causes"]) == 1
    assert len(dumped["timeline"]) == 2


@pytest.mark.asyncio
async def test_issue_repository_crud(async_db_session: AsyncSession):
    """Test repository create, get, update, and search."""
    repo = IssueRepository(async_db_session)

    issue = CustomerIssue(
        title="Subscription Renewal Failure",
        category=IssueCategory.PAYMENT_FAILURE,
        severity=IssueSeverity.MEDIUM,
        merchant_id="merch_test",
        customer_email="rahul@example.com",
        order_id="order_999",
    )

    await repo.save_issue(issue)
    await async_db_session.commit()

    # Retrieve
    retrieved = await repo.get_issue(issue.issue_id)
    assert retrieved is not None
    assert retrieved.customer_email == "rahul@example.com"
    assert retrieved.title == "Subscription Renewal Failure"

    # Update status
    retrieved.transition_status(IssueStatus.RESOLVED, actor="operator_1", reason="Customer paid via retry link")
    retrieved.resolution_summary = "Customer paid successfully"
    retrieved.resolution_verified = True
    await repo.save_issue(retrieved)
    await async_db_session.commit()

    updated = await repo.get_issue(issue.issue_id)
    assert updated.status == IssueStatus.RESOLVED
    assert updated.resolution_verified is True

    # List
    issues = await repo.list_issues(merchant_id="merch_test")
    assert len(issues) == 1
    assert issues[0].issue_id == issue.issue_id


@pytest.mark.asyncio
async def test_email_service_drafting_and_duplicate_prevention(async_db_session: AsyncSession):
    """Test generating email drafts and duplicate prevention."""
    draft = await email_service.generate_draft(
        session=async_db_session,
        template_id="payment_failure",
        recipient_email="test@user.com",
        recipient_name="Aarav",
        template_vars={
            "amount": "2,499.00",
            "failure_reason": "Insufficient balance",
            "resolution_instruction": "Please retry with another card or UPI.",
            "payment_link_section": "Payment link: https://rzp.io/l/test_link_123\n",
            "payment_link_section_html": "<p>Payment link: https://rzp.io/l/test_link_123</p>",
            "business_name": "Test Merchant",
        },
        issue_id="iss_test_01",
    )
    await async_db_session.commit()

    assert draft["draft_id"].startswith("draft_")
    assert "2,499.00" in draft["body_text"]
    assert "https://rzp.io/l/test_link_123" in draft["body_text"]
    assert draft["status"] == "DRAFT"

    # Send email (simulation)
    result = await email_service.send_email(
        session=async_db_session,
        draft_id=draft["draft_id"],
        operator_id="operator_copilot",
    )
    await async_db_session.commit()

    assert result["status"] in ("DELIVERED", "ACCEPTED")
    assert "provider_message_id" in result

    # Prevent duplicate sends
    result_dup = await email_service.send_email(
        session=async_db_session,
        draft_id=draft["draft_id"],
    )
    assert result_dup["is_duplicate"] is True


@pytest.mark.asyncio
async def test_refund_service_eligibility_and_execution(async_db_session: AsyncSession):
    """Test refund investigation and eligibility checks."""
    # Seed a sample payment case
    case_record = PaymentCaseRecord(
        case_id="case_ref_001",
        payment_id="pay_ref_001",
        subscription_id="sub_ref_001",
        customer_id="cust_ref_001",
        customer_name="Vikram Singh",
        customer_email="vikram@example.com",
        customer_phone="+919876543210",
        amount_inr=1500.0,
        currency="INR",
        status=CaseStatus.RECOVERED.value,
        failure_category="UNKNOWN_FAILURE",
        failure_code="NONE",
        failure_reason="",
        payment_method="CARD",
    )
    async_db_session.add(case_record)
    await async_db_session.commit()

    # Investigate refund
    inv = await refund_service.investigate_refund(
        session=async_db_session,
        payment_id="pay_ref_001",
    )
    assert inv["found"] is True
    assert inv["refund_eligible"] is True
    assert inv["original_amount_inr"] == 1500.0

    # Prepare refund
    prep = await refund_service.prepare_refund(
        session=async_db_session,
        case_id="case_ref_001",
        amount_inr=1500.0,
        reason="Customer cancellation",
        operator_id="test_operator",
    )
    await async_db_session.commit()
    assert prep["status"] == "PROCESSING"
    assert "rfnd_" in prep["refund_id"]
    assert prep["amount_inr"] == 1500.0


@pytest.mark.asyncio
async def test_automation_service_checks(async_db_session: AsyncSession):
    """Test operational automation checks and clear configuration disclosure."""
    status = await automation_service.get_automation_status(session=async_db_session)
    assert "scheduling_infrastructure" in status
    assert len(status["available_checks"]) >= 5

    # Run payment mismatch check
    mismatches = await automation_service.check_payment_mismatches(session=async_db_session)
    assert mismatches["check"] == "payment_mismatch"
    assert "alerts" in mismatches

    # Run operational summary
    summary = await automation_service.generate_operational_summary(session=async_db_session)
    assert summary["check"] == "operational_summary"
    assert "cases" in summary
    assert "issues" in summary
