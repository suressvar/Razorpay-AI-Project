"""Repository for customer issue CRUD operations."""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.domain.issue_models import (
    ActionStatus,
    CommunicationStatus,
    ConfidenceLevel,
    CustomerIssue,
    EnvironmentMode,
    IssueAction,
    IssueCategory,
    IssueCause,
    IssueCommunication,
    IssueEvidence,
    IssueSeverity,
    IssueStatus,
    IssueTimelineEntry,
    utc_now,
)
from recovery_autopilot.persistence.issue_models import CustomerIssueRecord, EmailDraftRecord

logger = logging.getLogger("recovery_autopilot.persistence.issue_repository")


class IssueRepository:
    """Repository for customer issue tracking persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _issue_to_record(self, issue: CustomerIssue) -> CustomerIssueRecord:
        return CustomerIssueRecord(
            issue_id=issue.issue_id,
            title=issue.title,
            category=issue.category.value,
            severity=issue.severity.value,
            status=issue.status.value,
            environment=issue.environment.value,
            merchant_id=issue.merchant_id,
            customer_id=issue.customer_id,
            customer_name=issue.customer_name,
            customer_email=issue.customer_email,
            payment_id=issue.payment_id,
            order_id=issue.order_id,
            refund_id=issue.refund_id,
            payment_link_id=issue.payment_link_id,
            case_id=issue.case_id,
            owner=issue.owner,
            sla_deadline=issue.sla_deadline,
            next_action=issue.next_action,
            reported_symptoms=issue.reported_symptoms,
            expected_behavior=issue.expected_behavior,
            actual_behavior=issue.actual_behavior,
            evidence_json=json.dumps([e.model_dump(mode="json") for e in issue.evidence], default=str),
            causes_json=json.dumps([c.model_dump(mode="json") for c in issue.possible_causes], default=str),
            actions_json=json.dumps([a.model_dump(mode="json") for a in issue.actions], default=str),
            communications_json=json.dumps([c.model_dump(mode="json") for c in issue.communications], default=str),
            timeline_json=json.dumps([t.model_dump(mode="json") for t in issue.timeline], default=str),
            resolution_summary=issue.resolution_summary,
            resolution_verified=issue.resolution_verified,
            resolution_evidence=issue.resolution_evidence,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )

    def _record_to_issue(self, rec: CustomerIssueRecord) -> CustomerIssue:
        evidence = [IssueEvidence.model_validate(e) for e in json.loads(rec.evidence_json or "[]")]
        causes = [IssueCause.model_validate(c) for c in json.loads(rec.causes_json or "[]")]
        actions = [IssueAction.model_validate(a) for a in json.loads(rec.actions_json or "[]")]
        comms = [IssueCommunication.model_validate(c) for c in json.loads(rec.communications_json or "[]")]
        timeline = [IssueTimelineEntry.model_validate(t) for t in json.loads(rec.timeline_json or "[]")]

        return CustomerIssue(
            issue_id=rec.issue_id,
            title=rec.title,
            category=IssueCategory(rec.category),
            severity=IssueSeverity(rec.severity),
            status=IssueStatus(rec.status),
            environment=EnvironmentMode(rec.environment) if rec.environment else EnvironmentMode.TEST,
            merchant_id=rec.merchant_id,
            customer_id=rec.customer_id,
            customer_name=rec.customer_name,
            customer_email=rec.customer_email,
            payment_id=rec.payment_id,
            order_id=rec.order_id,
            refund_id=rec.refund_id,
            payment_link_id=rec.payment_link_id,
            case_id=rec.case_id,
            owner=rec.owner,
            sla_deadline=rec.sla_deadline,
            next_action=rec.next_action,
            reported_symptoms=rec.reported_symptoms,
            expected_behavior=rec.expected_behavior,
            actual_behavior=rec.actual_behavior,
            evidence=evidence,
            possible_causes=causes,
            actions=actions,
            communications=comms,
            timeline=timeline,
            resolution_summary=rec.resolution_summary,
            resolution_verified=rec.resolution_verified,
            resolution_evidence=rec.resolution_evidence,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )

    async def save_issue(self, issue: CustomerIssue) -> None:
        """Upsert a customer issue."""
        stmt = select(CustomerIssueRecord).where(CustomerIssueRecord.issue_id == issue.issue_id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            record = self._issue_to_record(issue)
            self.session.add(record)
        else:
            existing.title = issue.title
            existing.category = issue.category.value
            existing.severity = issue.severity.value
            existing.status = issue.status.value
            existing.environment = issue.environment.value
            existing.merchant_id = issue.merchant_id
            existing.customer_id = issue.customer_id
            existing.customer_name = issue.customer_name
            existing.customer_email = issue.customer_email
            existing.payment_id = issue.payment_id
            existing.order_id = issue.order_id
            existing.refund_id = issue.refund_id
            existing.payment_link_id = issue.payment_link_id
            existing.case_id = issue.case_id
            existing.owner = issue.owner
            existing.sla_deadline = issue.sla_deadline
            existing.next_action = issue.next_action
            existing.reported_symptoms = issue.reported_symptoms
            existing.expected_behavior = issue.expected_behavior
            existing.actual_behavior = issue.actual_behavior
            existing.evidence_json = json.dumps([e.model_dump(mode="json") for e in issue.evidence], default=str)
            existing.causes_json = json.dumps([c.model_dump(mode="json") for c in issue.possible_causes], default=str)
            existing.actions_json = json.dumps([a.model_dump(mode="json") for a in issue.actions], default=str)
            existing.communications_json = json.dumps([c.model_dump(mode="json") for c in issue.communications], default=str)
            existing.timeline_json = json.dumps([t.model_dump(mode="json") for t in issue.timeline], default=str)
            existing.resolution_summary = issue.resolution_summary
            existing.resolution_verified = issue.resolution_verified
            existing.resolution_evidence = issue.resolution_evidence
            existing.updated_at = issue.updated_at

        await self.session.flush()

    async def get_issue(self, issue_id: str) -> Optional[CustomerIssue]:
        """Fetch a single issue by ID."""
        stmt = select(CustomerIssueRecord).where(CustomerIssueRecord.issue_id == issue_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        return self._record_to_issue(record)

    async def find_related_issues(
        self,
        payment_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        case_id: Optional[str] = None,
        exclude_closed: bool = True,
    ) -> List[CustomerIssue]:
        """Find existing issues related to the same payment/customer to prevent duplicates."""
        conditions = []
        if payment_id:
            conditions.append(CustomerIssueRecord.payment_id == payment_id)
        if customer_email:
            conditions.append(func.lower(CustomerIssueRecord.customer_email) == customer_email.lower())
        if case_id:
            conditions.append(CustomerIssueRecord.case_id == case_id)

        if not conditions:
            return []

        from sqlalchemy import or_
        stmt = select(CustomerIssueRecord).where(or_(*conditions))
        if exclude_closed:
            stmt = stmt.where(CustomerIssueRecord.status != IssueStatus.CLOSED.value)
        stmt = stmt.order_by(desc(CustomerIssueRecord.created_at))

        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [self._record_to_issue(r) for r in records]

    async def list_issues(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        customer_email: Optional[str] = None,
        merchant_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CustomerIssue]:
        """List issues with optional filters."""
        stmt = select(CustomerIssueRecord)
        if status:
            stmt = stmt.where(CustomerIssueRecord.status == status)
        if category:
            stmt = stmt.where(CustomerIssueRecord.category == category)
        if severity:
            stmt = stmt.where(CustomerIssueRecord.severity == severity)
        if customer_email:
            stmt = stmt.where(func.lower(CustomerIssueRecord.customer_email) == customer_email.lower())
        if merchant_id:
            stmt = stmt.where(CustomerIssueRecord.merchant_id == merchant_id)
        stmt = stmt.order_by(desc(CustomerIssueRecord.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [self._record_to_issue(r) for r in records]

    async def count_issues(self, status: Optional[str] = None) -> int:
        """Count issues optionally filtered by status."""
        stmt = select(func.count(CustomerIssueRecord.issue_id))
        if status:
            stmt = stmt.where(CustomerIssueRecord.status == status)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # --- Email Draft Operations ---

    async def save_email_draft(self, draft: Dict[str, Any]) -> None:
        """Save or update an email draft."""
        stmt = select(EmailDraftRecord).where(EmailDraftRecord.draft_id == draft["draft_id"])
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            record = EmailDraftRecord(**draft)
            self.session.add(record)
        else:
            for key, value in draft.items():
                if key != "draft_id" and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = utc_now()

        await self.session.flush()

    async def get_email_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Fetch an email draft by ID."""
        stmt = select(EmailDraftRecord).where(EmailDraftRecord.draft_id == draft_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        return {
            "draft_id": record.draft_id,
            "issue_id": record.issue_id,
            "case_id": record.case_id,
            "template_id": record.template_id,
            "recipient_email": record.recipient_email,
            "recipient_name": record.recipient_name,
            "subject": record.subject,
            "body_html": record.body_html,
            "body_text": record.body_text,
            "status": record.status,
            "provider_message_id": record.provider_message_id,
            "idempotency_key": record.idempotency_key,
            "sent_at": record.sent_at.isoformat() if record.sent_at else None,
            "error_message": record.error_message,
            "created_by": record.created_by,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

    async def update_draft_status(self, draft_id: str, status: str, provider_message_id: Optional[str] = None, error_message: Optional[str] = None) -> bool:
        """Update email draft send status."""
        stmt = select(EmailDraftRecord).where(EmailDraftRecord.draft_id == draft_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return False
        record.status = status
        if provider_message_id:
            record.provider_message_id = provider_message_id
        if error_message:
            record.error_message = error_message
        if status in ("ACCEPTED", "DELIVERED"):
            record.sent_at = utc_now()
        record.updated_at = utc_now()
        await self.session.flush()
        return True

    async def find_draft_by_idempotency_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Check for existing draft by idempotency key to prevent duplicates."""
        stmt = select(EmailDraftRecord).where(EmailDraftRecord.idempotency_key == key)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        return await self.get_email_draft(record.draft_id)
