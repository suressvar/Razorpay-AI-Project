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
    PromiseToPay,
    RecoveryProposal,
    utc_now,
)
from recovery_autopilot.persistence.models import (
    AuditEventRecord,
    OperationKeyRecord,
    PaymentCaseRecord,
    PromiseToPayRecord,
    RecoveryActionRecord,
    RecoveryLedgerRecord,
    UnmatchedWebhookRecord,
    VoiceSessionRecord,
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
        ptp_json = json.dumps(case.promise_to_pay.model_dump(mode="json")) if case.promise_to_pay else None
        out_json = json.dumps(case.outcome.model_dump(mode="json")) if case.outcome else None

        if not record:
            record = PaymentCaseRecord(
                case_id=case.case_id,
                payment_id=ctx.payment_id,
                subscription_id=ctx.subscription_id,
                invoice_id=ctx.invoice_id,
                order_id=ctx.order_id,
                payment_link_id=ctx.payment_link_id,
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
                promise_to_pay_json=ptp_json,
                outcome_json=out_json,
                created_at=case.created_at,
                updated_at=case.updated_at,
            )
            self.session.add(record)
        else:
            record.status = case.status.value
            record.contact_count = case.contact_count
            if ctx.order_id and not record.order_id:
                record.order_id = ctx.order_id
            if ctx.payment_link_id and not record.payment_link_id:
                record.payment_link_id = ctx.payment_link_id
            record.current_proposal_json = prop_json
            record.latest_decision_json = dec_json
            record.latest_action_json = act_json
            record.promise_to_pay_json = ptp_json
            record.outcome_json = out_json
            record.updated_at = case.updated_at

        await self.session.flush()

    def _record_to_case(self, rec: PaymentCaseRecord) -> PaymentCase:
        """Convert ORM record to domain PaymentCase."""
        ctx = PaymentContext(
            payment_id=rec.payment_id,
            subscription_id=rec.subscription_id,
            invoice_id=rec.invoice_id,
            order_id=rec.order_id,
            payment_link_id=rec.payment_link_id,
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
        ptp = PromiseToPay.model_validate_json(rec.promise_to_pay_json) if getattr(rec, 'promise_to_pay_json', None) else None
        outcome = PaymentOutcome.model_validate_json(rec.outcome_json) if rec.outcome_json else None

        case = PaymentCase(
            case_id=rec.case_id,
            context=ctx,
            status=CaseStatus(rec.status),
            current_proposal=proposal,
            latest_decision=decision,
            latest_action_result=action_res,
            promise_to_pay=ptp,
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

    async def get_case_by_exact_identifier(
        self,
        payment_id: Optional[str] = None,
        payment_link_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        order_id: Optional[str] = None,
        subscription_id: Optional[str] = None,
    ) -> Optional[tuple[PaymentCase, str, str]]:
        """Perform exact indexed lookup across 5 identifiers without guessing.

        Returns tuple (case, matched_field_name, matched_value) or None.
        """
        # 1. Exact Payment ID (highest confidence)
        if payment_id and payment_id not in ("pay_unknown", "pay_captured"):
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.payment_id == payment_id)
            res = (await self.session.execute(stmt)).scalars().first()
            if res:
                return self._record_to_case(res), "payment_id", payment_id

        # 2. Exact Payment Link ID
        if payment_link_id:
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.payment_link_id == payment_link_id)
            res = (await self.session.execute(stmt)).scalars().first()
            if res:
                return self._record_to_case(res), "payment_link_id", payment_link_id

        # 3. Exact Invoice ID
        if invoice_id:
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.invoice_id == invoice_id)
            res = (await self.session.execute(stmt)).scalars().first()
            if res:
                return self._record_to_case(res), "invoice_id", invoice_id

        # 4. Exact Order ID
        if order_id:
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.order_id == order_id)
            res = (await self.session.execute(stmt)).scalars().first()
            if res:
                return self._record_to_case(res), "order_id", order_id

        # 5. Exact Subscription ID (only match active case when it uniquely identifies the correct billing obligation)
        if subscription_id and subscription_id not in ("sub_unknown", ""):
            stmt = (
                select(PaymentCaseRecord)
                .where(PaymentCaseRecord.subscription_id == subscription_id)
                .order_by(desc(PaymentCaseRecord.created_at))
            )
            records = (await self.session.execute(stmt)).scalars().all()
            active_records = [
                r for r in records
                if r.status not in (CaseStatus.RECOVERED.value, CaseStatus.OPTED_OUT.value, CaseStatus.STOPPED.value)
            ]
            if len(active_records) == 1:
                return self._record_to_case(active_records[0]), "subscription_id", subscription_id
            elif len(active_records) > 1:
                # Ambiguous: multiple active billing obligations for this subscription
                return None
            elif len(records) == 1:
                # Exactly one record exists for this subscription
                return self._record_to_case(records[0]), "subscription_id", subscription_id

        return None

    async def get_active_cases_for_subscription(self, subscription_id: str) -> List[PaymentCase]:
        """Fetch all currently active (unsettled) cases for a subscription to evaluate ambiguity."""
        stmt = (
            select(PaymentCaseRecord)
            .where(PaymentCaseRecord.subscription_id == subscription_id)
            .where(
                PaymentCaseRecord.status.notin_([
                    CaseStatus.RECOVERED.value,
                    CaseStatus.OPTED_OUT.value,
                    CaseStatus.STOPPED.value,
                ])
            )
            .order_by(desc(PaymentCaseRecord.created_at))
        )
        records = (await self.session.execute(stmt)).scalars().all()
        return [self._record_to_case(r) for r in records]

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

    async def save_webhook_event(
        self,
        event_id: str,
        event_type: str,
        signature: str,
        payload_json: str,
        status: str = "received",
    ) -> bool:
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
            status=status,
            processed=(status == "completed"),
        )
        self.session.add(record)
        await self.session.flush()
        return True

    async def update_webhook_status(
        self,
        event_id: str,
        status: str,
        error_code: Optional[str] = None,
    ) -> None:
        """Update asynchronous processing status for a webhook event."""
        stmt = select(WebhookEventRecord).where(WebhookEventRecord.event_id == event_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
            record.status = status
            record.attempts += 1
            if error_code:
                record.error_code = error_code
            if status in ("completed", "unmatched", "dead_letter"):
                record.processed = True
                record.processed_at = utc_now()
            await self.session.flush()

    async def save_unmatched_event(
        self,
        event_id: str,
        event_type: str,
        payload_json: str,
        reason: str,
        signature: Optional[str] = None,
    ) -> None:
        """Persist uncorrelatable webhook event for investigation without corrupting cases."""
        stmt = select(UnmatchedWebhookRecord).where(UnmatchedWebhookRecord.event_id == event_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            return  # Already persisted

        record = UnmatchedWebhookRecord(
            event_id=event_id,
            event_type=event_type,
            signature=signature,
            payload_json=payload_json,
            reason=reason,
            received_at=utc_now(),
        )
        self.session.add(record)
        await self.session.flush()

    async def list_unmatched_events(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List uncorrelatable webhook events for the review dashboard."""
        stmt = select(UnmatchedWebhookRecord).order_by(desc(UnmatchedWebhookRecord.received_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [
            {
                "event_id": r.event_id,
                "event_type": r.event_type,
                "signature": r.signature,
                "payload_json": r.payload_json,
                "reason": r.reason,
                "received_at": r.received_at.isoformat() if r.received_at else None,
            }
            for r in records
        ]

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

    async def save_voice_session(self, session_record: VoiceSessionRecord) -> None:
        """Upsert a voice recovery session record."""
        existing = await self.session.get(VoiceSessionRecord, session_record.session_id)
        if not existing:
            self.session.add(session_record)
        else:
            existing.state = session_record.state
            existing.consent_granted = session_record.consent_granted
            existing.consent_timestamp = session_record.consent_timestamp
            existing.language = session_record.language
            existing.turn_count = session_record.turn_count
            existing.detected_intent = session_record.detected_intent
            existing.intent_confidence = session_record.intent_confidence
            existing.proposed_action = session_record.proposed_action
            existing.action_confirmed = session_record.action_confirmed
            existing.escalated_to_human = session_record.escalated_to_human
            existing.redacted_transcript_json = session_record.redacted_transcript_json
            existing.updated_at = session_record.updated_at
        await self.session.flush()

    async def get_voice_session(self, session_id: str) -> Optional[VoiceSessionRecord]:
        """Fetch a voice session by ID."""
        return await self.session.get(VoiceSessionRecord, session_id)

    async def delete_voice_transcript(self, session_id: str) -> bool:
        """Purge transcript data for operator privacy compliance."""
        record = await self.session.get(VoiceSessionRecord, session_id)
        if record:
            record.redacted_transcript_json = "[]"
            record.updated_at = utc_now()
            await self.session.flush()
            return True
        return False

    async def save_promise_to_pay(self, ptp: PromiseToPay) -> None:
        """Save a PromiseToPay commitment."""
        rec = PromiseToPayRecord(
            promise_id=ptp.promise_id,
            case_id=ptp.case_id,
            promised_datetime=ptp.promised_datetime,
            channel=ptp.channel,
            consent_timestamp=ptp.consent_timestamp,
            status=ptp.status,
            reminder_limit=ptp.reminder_limit,
            notes=ptp.notes,
            created_at=utc_now(),
        )
        self.session.add(rec)
        await self.session.flush()

    async def record_recovery_ledger(
        self,
        ledger_id: str,
        case_id: str,
        provider_payment_id: str,
        event_id: str,
        event_type: str,
        amount_inr: float,
        currency: str,
        matched_field: str,
        matched_value: str,
        recovered_at: Optional[Any] = None,
    ) -> tuple[bool, RecoveryLedgerRecord]:
        """Record recovery in the immutable ledger.
        
        Returns (True, record) if newly inserted, or (False, existing_record) if provider_payment_id already exists.
        Guarantees protection against distinct success events double-counting the same payment.
        """
        # 1. Check existing entry by unique provider payment id
        stmt = select(RecoveryLedgerRecord).where(RecoveryLedgerRecord.provider_payment_id == provider_payment_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return False, existing

        # 2. Insert new ledger record
        rec = RecoveryLedgerRecord(
            ledger_id=ledger_id,
            case_id=case_id,
            provider_payment_id=provider_payment_id,
            event_id=event_id,
            event_type=event_type,
            amount_inr=amount_inr,
            currency=currency,
            matched_field=matched_field,
            matched_value=matched_value,
            recovered_at=recovered_at or utc_now(),
        )
        self.session.add(rec)
        try:
            await self.session.flush()
            return True, rec
        except Exception:
            # Handle concurrent race condition on unique index
            await self.session.rollback()
            stmt_retry = select(RecoveryLedgerRecord).where(RecoveryLedgerRecord.provider_payment_id == provider_payment_id)
            existing_retry = (await self.session.execute(stmt_retry)).scalar_one_or_none()
            if existing_retry:
                return False, existing_retry
            raise

    async def get_recovery_by_payment_id(self, provider_payment_id: str) -> Optional[RecoveryLedgerRecord]:
        """Fetch recovery ledger record by unique provider payment ID."""
        stmt = select(RecoveryLedgerRecord).where(RecoveryLedgerRecord.provider_payment_id == provider_payment_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recovery_records(self, case_id: Optional[str] = None, limit: int = 100) -> List[RecoveryLedgerRecord]:
        """List persisted recovery ledger entries."""
        stmt = select(RecoveryLedgerRecord)
        if case_id:
            stmt = stmt.where(RecoveryLedgerRecord.case_id == case_id)
        stmt = stmt.order_by(desc(RecoveryLedgerRecord.recovered_at)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def cancel_pending_recovery_work(self, case_id: str) -> Dict[str, int]:
        """Cancel pending recovery work once payment is confirmed.
        
        Cancels active promises to pay, ongoing voice sessions, and scheduled tasks.
        """
        from sqlalchemy import update
        cancelled_counts = {"promises": 0, "voice_sessions": 0}

        # 1. Cancel active promises to pay
        stmt_ptp = (
            update(PromiseToPayRecord)
            .where(PromiseToPayRecord.case_id == case_id)
            .where(PromiseToPayRecord.status == "ACTIVE")
            .values(status="FULFILLED", notes="Automatically fulfilled upon confirmed payment")
        )
        res_ptp = await self.session.execute(stmt_ptp)
        cancelled_counts["promises"] = res_ptp.rowcount or 0

        # 2. Cancel/complete active voice sessions
        stmt_voice = (
            update(VoiceSessionRecord)
            .where(VoiceSessionRecord.case_id == case_id)
            .where(VoiceSessionRecord.state.notin_(["COMPLETED", "OPTED_OUT", "ESCALATED"]))
            .values(state="COMPLETED", proposed_action="PAYMENT_CONFIRMED_CANCELLED")
        )
        res_voice = await self.session.execute(stmt_voice)
        cancelled_counts["voice_sessions"] = res_voice.rowcount or 0

        await self.session.flush()
        return cancelled_counts

    async def clear_all_data(self) -> Dict[str, int]:
        """Delete all records across all tables for full sandbox/demo reset."""
        from sqlalchemy import delete
        
        from recovery_autopilot.persistence.issue_models import CustomerIssueRecord, EmailDraftRecord
        
        counts = {}
        for model, name in [
            (RecoveryLedgerRecord, "recovery_ledger"),
            (RecoveryActionRecord, "recovery_actions"),
            (AuditEventRecord, "audit_events"),
            (PromiseToPayRecord, "promises_to_pay"),
            (VoiceSessionRecord, "voice_sessions"),
            (UnmatchedWebhookRecord, "unmatched_webhooks"),
            (WebhookEventRecord, "webhook_events"),
            (CustomerIssueRecord, "customer_issues"),
            (EmailDraftRecord, "email_drafts"),
            (PaymentCaseRecord, "payment_cases"),
            (OperationKeyRecord, "operation_keys"),
        ]:
            res = await self.session.execute(delete(model))
            counts[name] = res.rowcount or 0

        await self.session.flush()
        return counts



