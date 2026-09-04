"""SQLAlchemy repository implementing persistence for cases, webhooks, and audit logs."""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.domain.enums import (
    ActorType,
    CaseStatus,
    CustomerSegment,
    FailureCategory,
    PaymentMethod,
)
from recovery_autopilot.domain.models import (
    AuditEvent,
    ExecutionResult,
    PaymentCase,
    PaymentContext,
    PaymentOutcome,
    PolicyDecision,
    RecoveryProposal,
)
from recovery_autopilot.persistence.models import (
    AuditEventRecord,
    PaymentCaseRecord,
    WebhookEventRecord,
)
from recovery_autopilot.workflows.protocols import CaseRepositoryProtocol


class SqlAlchemyRepository(CaseRepositoryProtocol):
    """Repository managing asynchronous database persistence for Recovery Autopilot."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_case(self, case: PaymentCase) -> None:
        """Upsert a PaymentCase aggregate into database."""
        stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.case_id == case.case_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        ctx = case.context
        prop_json = json.dumps(case.current_proposal.model_dump(mode="json")) if case.current_proposal else None
        dec_json = json.dumps(case.latest_decision.model_dump(mode="json")) if case.latest_decision else None
        act_json = json.dumps(case.latest_action_result.model_dump(mode="json")) if case.latest_action_result else None
        out_json = json.dumps(case.outcome.model_dump(mode="json")) if case.outcome else None

        if not record:
            record = PaymentCaseRecord(
                case_id=case.case_id,
                payment_id=ctx.payment_id,
                subscription_id=ctx.subscription_id,
                invoice_id=ctx.invoice_id,
                customer_id=ctx.customer_id,
                customer_name=ctx.customer_name,
                customer_email=ctx.customer_email,
                customer_phone=ctx.customer_phone,
                amount_inr=ctx.amount_inr,
                currency=ctx.currency,
                failure_category=ctx.failure_category.value,
                failure_code=ctx.failure_code,
                failure_reason=ctx.failure_reason,
                payment_method=ctx.payment_method.value,
                customer_segment=ctx.customer_segment.value,
                status=case.status.value,
                contact_count=case.contact_count,
                bank_name=ctx.bank_name,
                bank_degraded=ctx.bank_degraded,
                opted_out=ctx.opted_out,
                current_proposal_json=prop_json,
                latest_decision_json=dec_json,
                latest_action_json=act_json,
                outcome_json=out_json,
                created_at=case.created_at,
                updated_at=case.updated_at,
            )
            self.session.add(record)
        else:
            record.status = case.status.value
            record.contact_count = case.contact_count
            record.current_proposal_json = prop_json
            record.latest_decision_json = dec_json
            record.latest_action_json = act_json
            record.outcome_json = out_json
            record.updated_at = case.updated_at

        await self.session.flush()

    def _record_to_case(self, rec: PaymentCaseRecord) -> PaymentCase:
        """Convert ORM record to domain PaymentCase."""
        ctx = PaymentContext(
            payment_id=rec.payment_id,
            subscription_id=rec.subscription_id,
            invoice_id=rec.invoice_id,
            customer_id=rec.customer_id,
            customer_name=rec.customer_name,
            customer_email=rec.customer_email,
            customer_phone=rec.customer_phone,
            amount_inr=rec.amount_inr,
            currency=rec.currency,
            failure_category=FailureCategory(rec.failure_category),
            failure_code=rec.failure_code,
            failure_reason=rec.failure_reason,
            payment_method=PaymentMethod(rec.payment_method),
            customer_segment=CustomerSegment(rec.customer_segment),
            bank_name=rec.bank_name,
            bank_degraded=rec.bank_degraded,
            opted_out=rec.opted_out,
            occurred_at=rec.created_at,
        )

        proposal = RecoveryProposal.model_validate_json(rec.current_proposal_json) if rec.current_proposal_json else None
        decision = PolicyDecision.model_validate_json(rec.latest_decision_json) if rec.latest_decision_json else None
        action_res = ExecutionResult.model_validate_json(rec.latest_action_json) if rec.latest_action_json else None
        outcome = PaymentOutcome.model_validate_json(rec.outcome_json) if rec.outcome_json else None

        case = PaymentCase(
            case_id=rec.case_id,
            context=ctx,
            status=CaseStatus(rec.status),
            current_proposal=proposal,
            latest_decision=decision,
            latest_action_result=action_res,
            outcome=outcome,
            contact_count=rec.contact_count,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
        return case

    async def get_case(self, case_id: str) -> Optional[PaymentCase]:
        """Fetch a single case by ID."""
        stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.case_id == case_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        return self._record_to_case(record)

    async def list_cases(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PaymentCase]:
        """List cases with optional status and category filters."""
        stmt = select(PaymentCaseRecord)
        if status:
            stmt = stmt.where(PaymentCaseRecord.status == status)
        if category:
            stmt = stmt.where(PaymentCaseRecord.failure_category == category)
        stmt = stmt.order_by(desc(PaymentCaseRecord.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [self._record_to_case(r) for r in records]

    async def record_audit(self, event: AuditEvent) -> None:
        """Record immutable audit log entry."""
        details_str = json.dumps(event.details, default=str)
        actor_str = event.actor.value if hasattr(event.actor, "value") else str(event.actor)

        record = AuditEventRecord(
            event_id=event.event_id,
            case_id=event.case_id,
            actor=actor_str,
            event_type=event.event_type,
            details_json=details_str,
            timestamp=event.timestamp,
        )
        self.session.add(record)
        await self.session.flush()

    async def get_audit_events(self, case_id: str) -> List[AuditEvent]:
        """Fetch all chronological audit events for a case."""
        stmt = select(AuditEventRecord).where(AuditEventRecord.case_id == case_id).order_by(AuditEventRecord.timestamp.asc())
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        events: List[AuditEvent] = []
        for r in records:
            actor = ActorType(r.actor) if r.actor in ActorType.__members__ else ActorType.SYSTEM
            details = json.loads(r.details_json) if r.details_json else {}
            events.append(
                AuditEvent(
                    event_id=r.event_id,
                    case_id=r.case_id,
                    timestamp=r.timestamp,
                    actor=actor,
                    event_type=r.event_type,
                    details=details,
                )
            )
        return events

    async def list_recent_audit_events(self, limit: int = 25) -> List[AuditEvent]:
        """Fetch global recent audit events feed for the dashboard."""
        stmt = select(AuditEventRecord).order_by(desc(AuditEventRecord.timestamp)).limit(limit)
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        events: List[AuditEvent] = []
        for r in records:
            actor = ActorType(r.actor) if r.actor in ActorType.__members__ else ActorType.SYSTEM
            details = json.loads(r.details_json) if r.details_json else {}
            events.append(
                AuditEvent(
                    event_id=r.event_id,
                    case_id=r.case_id,
                    timestamp=r.timestamp,
                    actor=actor,
                    event_type=r.event_type,
                    details=details,
                )
            )
        return events

    async def save_webhook_event(self, event_id: str, event_type: str, signature: str, payload_json: str) -> bool:
        """Store raw webhook idempotently. Returns False if event was already recorded."""
        stmt = select(WebhookEventRecord).where(WebhookEventRecord.event_id == event_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            return False  # Duplicate event

        record = WebhookEventRecord(
            event_id=event_id,
            event_type=event_type,
            signature=signature,
            payload_json=payload_json,
            processed=False,
        )
        self.session.add(record)
        await self.session.flush()
        return True

    async def get_summary_metrics(self) -> Dict[str, Any]:
        """Compute live recovery metrics from database records."""
        total_stmt = select(func.count(PaymentCaseRecord.case_id))
        total_cases = (await self.session.execute(total_stmt)).scalar() or 0

        rec_stmt = select(
            func.count(PaymentCaseRecord.case_id),
            func.sum(PaymentCaseRecord.amount_inr),
        ).where(PaymentCaseRecord.status == CaseStatus.RECOVERED.value)
        rec_res = (await self.session.execute(rec_stmt)).one()
        recovered_cases = rec_res[0] or 0
        total_inr_recovered = rec_res[1] or 0.0

        awaiting_stmt = select(func.count(PaymentCaseRecord.case_id)).where(
            PaymentCaseRecord.status == CaseStatus.AWAITING_APPROVAL.value
        )
        awaiting_cases = (await self.session.execute(awaiting_stmt)).scalar() or 0

        recovery_rate = (recovered_cases / total_cases * 100) if total_cases > 0 else 0.0

        return {
            "total_cases": total_cases,
            "recovered_cases": recovered_cases,
            "total_inr_recovered": round(total_inr_recovered, 2),
            "recovery_rate": round(recovery_rate, 2),
            "awaiting_approval_count": awaiting_cases,
        }
