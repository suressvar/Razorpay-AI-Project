"""Unified payment event processing service.

Unifies direct webhook ingestion, asynchronous queue worker, demo simulation routes,
and reconciliation paths behind one consistent financial processing pipeline.

Guarantees:
1. Exact obligation matching across payment, payment_link, invoice, order, and unambiguous subscription references.
2. Explicit handling of ambiguous and unmatched events.
3. Strict amount (within 5 paise) and currency validation.
4. Stable event deduplication using provider event ID with SHA-256 fallback.
5. Idempotent recovery ledger with unique provider payment references (prevents double-counting).
6. Authorization events (payment.authorized) are never credited as captured revenue.
7. Out-of-order delivery protection (e.g. capture before failure, failure after capture).
8. Automatic cancellation of pending recovery work (promises to pay, voice sessions) upon confirmed payment.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.domain.enums import ActorType, CaseStatus
from recovery_autopilot.domain.models import AuditEvent, PaymentOutcome, utc_now
from recovery_autopilot.integrations.razorpay.event_mapper import CapturedPaymentContext, RazorpayEventMapper
from recovery_autopilot.persistence.database import async_session_factory
from recovery_autopilot.persistence.models import (
    RecoveryLedgerRecord,
    UnmatchedWebhookRecord,
    WebhookEventRecord,
)
from recovery_autopilot.persistence.repository import SqlAlchemyRepository

logger = logging.getLogger("recovery_autopilot.services.event_processor")


class UnifiedEventProcessor:
    """Singleton service for processing and reconciling all Razorpay lifecycle events."""

    def __init__(self, orchestrator_ref=None):
        self._orchestrator = orchestrator_ref

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            from recovery_autopilot.services.orchestrator import orchestrator
            self._orchestrator = orchestrator
        return self._orchestrator

    @staticmethod
    def compute_payload_hash(payload_str: str) -> str:
        """Compute stable SHA-256 hash of raw or serialized payload for deduplication fallback."""
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    async def process_event(
        self,
        payload: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        signature: Optional[str] = None,
        event_id: Optional[str] = None,
        source: str = "webhook",
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Process any incoming payment lifecycle event with complete accounting guarantees."""
        payload_str = raw_body.decode("utf-8") if raw_body else json.dumps(payload)
        payload_hash = self.compute_payload_hash(payload_str)

        # 1. Resolve Provider Event ID or SHA-256 fallback
        if event_id:
            resolved_event_id = event_id
        elif payload.get("event_id"):
            resolved_event_id = payload.get("event_id")
        elif payload.get("id"):
            resolved_event_id = payload.get("id")
        else:
            resolved_event_id = f"evt_sha256_{payload_hash[:24]}"

        event_name = payload.get("event", "unknown")

        async def _execute(s: AsyncSession) -> Dict[str, Any]:
            repo = SqlAlchemyRepository(s)

            # 2. Stable Event Deduplication Check using resolved_event_id
            existing_event = await s.get(WebhookEventRecord, resolved_event_id)
            if existing_event and existing_event.processed:
                logger.info("Ignoring duplicate event %s (status: %s)", resolved_event_id, existing_event.status)
                return {
                    "status": "duplicate_ignored",
                    "event_id": resolved_event_id,
                    "previous_status": existing_event.status,
                }

            # If not in table, register event record
            if not existing_event:
                await repo.save_webhook_event(
                    event_id=resolved_event_id,
                    event_type=event_name,
                    signature=signature or "sig_internal_or_demo",
                    payload_json=payload_str,
                    status="processing",
                )
                # Update payload_hash on record
                evt_rec = await s.get(WebhookEventRecord, resolved_event_id)
                if evt_rec:
                    evt_rec.payload_hash = payload_hash

            # -------------------------------------------------------------
            # 3. Handle PAYMENT FAILURE Events
            # -------------------------------------------------------------
            if event_name in ("payment.failed", "order.paid.failed", "subscription.charged.failed", "invoice.payment_failed"):
                context = RazorpayEventMapper.map_payment_failed(payload)

                # Check if this payment ID was already recovered in ledger (out-of-order delivery)
                existing_ledger = await repo.get_recovery_by_payment_id(context.payment_id)
                if existing_ledger:
                    logger.warning(
                        "Out-of-order failure arrived for already recovered payment %s. Ignoring failure transition.",
                        context.payment_id,
                    )
                    await repo.update_webhook_status(resolved_event_id, status="completed")
                    return {
                        "status": "out_of_order_failure_ignored",
                        "event_id": resolved_event_id,
                        "payment_id": context.payment_id,
                        "recovered_ledger_id": existing_ledger.ledger_id,
                    }

                # Check if case already exists for this payment_id
                match_res = await repo.get_case_by_exact_identifier(payment_id=context.payment_id)
                if match_res:
                    case, matched_field, matched_val = match_res
                    if case.status == CaseStatus.RECOVERED:
                        logger.info("Case %s is already RECOVERED. Ignoring late failure event.", case.case_id)
                        await repo.update_webhook_status(resolved_event_id, status="completed")
                        return {
                            "status": "out_of_order_failure_ignored",
                            "event_id": resolved_event_id,
                            "case_id": case.case_id,
                        }
                    # Update context / existing case
                    await repo.update_webhook_status(resolved_event_id, status="completed")
                    return {
                        "status": "case_already_active",
                        "event_id": resolved_event_id,
                        "case_id": case.case_id,
                        "case_status": case.status.value,
                    }

                # Check if an unmatched capture arrived previously for this payment or order (out-of-order capture)
                stmt_unmatched = select(UnmatchedWebhookRecord).where(
                    UnmatchedWebhookRecord.payload_json.like(f"%{context.payment_id}%")
                )
                prior_unmatched = (await s.execute(stmt_unmatched)).scalars().first()

                workflow = self.orchestrator.create_workflow(repo)
                case = await workflow.process_failed_payment(context)

                if prior_unmatched:
                    # Immediately reconcile the prior unmatched capture
                    logger.info("Reconciling out-of-order capture %s for newly arrived failure case %s", prior_unmatched.event_id, case.case_id)
                    prior_payload = json.loads(prior_unmatched.payload_json)
                    prior_ctx = RazorpayEventMapper.map_payment_captured(prior_payload)
                    
                    ledger_id = f"led_{uuid.uuid4().hex[:12]}"
                    is_new_ledger, ledger_rec = await repo.record_recovery_ledger(
                        ledger_id=ledger_id,
                        case_id=case.case_id,
                        provider_payment_id=prior_ctx.payment_id,
                        event_id=prior_unmatched.event_id,
                        event_type=prior_unmatched.event_type,
                        amount_inr=prior_ctx.amount_inr,
                        currency=prior_ctx.currency,
                        matched_field="payment_id",
                        matched_value=context.payment_id,
                    )
                    if is_new_ledger:
                        await workflow.handle_payment_success(
                            case=case,
                            payment_id=prior_ctx.payment_id,
                            amount_inr=prior_ctx.amount_inr,
                            currency=prior_ctx.currency,
                            matched_field="payment_id",
                            matched_value=context.payment_id,
                        )
                    await s.delete(prior_unmatched)

                await repo.update_webhook_status(resolved_event_id, status="completed")
                return {
                    "status": "processed",
                    "event_id": resolved_event_id,
                    "case_id": case.case_id,
                    "case_status": case.status.value,
                    "action": case.latest_action_result.action.value if case.latest_action_result else None,
                }

            # -------------------------------------------------------------
            # 4. Handle PAYMENT AUTHORIZED Events (Pre-authorization only)
            # -------------------------------------------------------------
            if event_name == "payment.authorized":
                captured_ctx = RazorpayEventMapper.map_payment_captured(payload)
                match_result = await repo.get_case_by_exact_identifier(
                    payment_id=captured_ctx.payment_id,
                    payment_link_id=captured_ctx.payment_link_id,
                    invoice_id=captured_ctx.invoice_id,
                    order_id=captured_ctx.order_id,
                    subscription_id=captured_ctx.subscription_id,
                )
                if match_result:
                    case, matched_field, matched_value = match_result
                    audit_auth = AuditEvent(
                        case_id=case.case_id,
                        actor=ActorType.WEBHOOK,
                        event_type="PAYMENT_AUTHORIZED_PENDING_CAPTURE",
                        details={
                            "payment_id": captured_ctx.payment_id,
                            "amount_inr": captured_ctx.amount_inr,
                            "currency": captured_ctx.currency,
                            "matched_by": matched_field,
                            "matched_value": matched_value,
                            "note": "Pre-authorization received. Not credited as captured revenue until payment.captured.",
                        },
                    )
                    await repo.record_audit(audit_auth)
                    await repo.update_webhook_status(resolved_event_id, status="completed")
                    return {
                        "status": "authorized_pending_capture",
                        "event_id": resolved_event_id,
                        "case_id": case.case_id,
                        "amount_inr": captured_ctx.amount_inr,
                        "message": "Authorization recorded; pending capture confirmation",
                    }
                else:
                    await repo.update_webhook_status(resolved_event_id, status="completed")
                    return {
                        "status": "authorized_unmatched",
                        "event_id": resolved_event_id,
                        "payment_id": captured_ctx.payment_id,
                    }

            # -------------------------------------------------------------
            # 5. Handle PAYMENT SUCCESS / CAPTURE Events
            # -------------------------------------------------------------
            if event_name in ("payment.captured", "order.paid", "subscription.charged", "payment_link.paid", "invoice.paid"):
                captured_ctx = RazorpayEventMapper.map_payment_captured(payload)
                provider_payment_id = captured_ctx.payment_id

                # Guard: Check if provider_payment_id was already recorded in recovery ledger
                existing_ledger = await repo.get_recovery_by_payment_id(provider_payment_id)
                if existing_ledger:
                    logger.info(
                        "Duplicate payment capture ignored for provider_payment_id %s (already in ledger %s)",
                        provider_payment_id,
                        existing_ledger.ledger_id,
                    )
                    audit_dup_ledger = AuditEvent(
                        case_id=existing_ledger.case_id,
                        actor=ActorType.WEBHOOK,
                        event_type="DUPLICATE_PAYMENT_LEDGER_IGNORED",
                        details={
                            "provider_payment_id": provider_payment_id,
                            "event_id": resolved_event_id,
                            "event_type": event_name,
                            "existing_ledger_id": existing_ledger.ledger_id,
                        },
                    )
                    await repo.record_audit(audit_dup_ledger)
                    await repo.update_webhook_status(resolved_event_id, status="completed")
                    return {
                        "status": "recovered",
                        "duplicate_ignored": True,
                        "event_id": resolved_event_id,
                        "case_id": existing_ledger.case_id,
                        "provider_payment_id": provider_payment_id,
                        "recovered_amount": existing_ledger.amount_inr,
                        "ledger_id": existing_ledger.ledger_id,
                    }

                # Exact Obligation Matching
                # First check for ambiguity on subscription if subscription_id is provided
                if captured_ctx.subscription_id and captured_ctx.subscription_id not in ("sub_unknown", ""):
                    active_sub_cases = await repo.get_active_cases_for_subscription(captured_ctx.subscription_id)
                    if len(active_sub_cases) > 1:
                        # Ambiguous subscription match: multiple active cases
                        candidate_ids = [c.case_id for c in active_sub_cases]
                        logger.warning(
                            "Ambiguous subscription match for %s: %s active cases (%s). Storing as unmatched.",
                            captured_ctx.subscription_id,
                            len(candidate_ids),
                            candidate_ids,
                        )
                        reason_msg = (
                            f"Ambiguous subscription match: multiple active cases ({candidate_ids}) "
                            f"for subscription {captured_ctx.subscription_id}. Human review required."
                        )
                        for c in active_sub_cases:
                            audit_ambig = AuditEvent(
                                case_id=c.case_id,
                                actor=ActorType.POLICY,
                                event_type="AMBIGUOUS_SUBSCRIPTION_MATCH_DETECTED",
                                details={
                                    "subscription_id": captured_ctx.subscription_id,
                                    "event_id": resolved_event_id,
                                    "candidate_cases": candidate_ids,
                                },
                            )
                            await repo.record_audit(audit_ambig)

                        await repo.save_unmatched_event(
                            event_id=resolved_event_id,
                            event_type=event_name,
                            payload_json=payload_str,
                            reason=reason_msg,
                            signature=signature,
                        )
                        await repo.update_webhook_status(resolved_event_id, status="unmatched")
                        return {
                            "status": "ambiguous_subscription_stored",
                            "event_id": resolved_event_id,
                            "subscription_id": captured_ctx.subscription_id,
                            "candidate_cases": candidate_ids,
                            "reason": reason_msg,
                        }

                # Attempt exact identifier match across payment_id, payment_link_id, invoice_id, order_id, subscription_id
                match_result = await repo.get_case_by_exact_identifier(
                    payment_id=captured_ctx.payment_id,
                    payment_link_id=captured_ctx.payment_link_id,
                    invoice_id=captured_ctx.invoice_id,
                    order_id=captured_ctx.order_id,
                    subscription_id=captured_ctx.subscription_id,
                )

                if not match_result:
                    reason_msg = (
                        f"Uncorrelatable success event: payment_id={captured_ctx.payment_id}, "
                        f"order_id={captured_ctx.order_id}, sub_id={captured_ctx.subscription_id}, "
                        f"plink_id={captured_ctx.payment_link_id}, inv_id={captured_ctx.invoice_id}"
                    )
                    logger.info("Unmatched success event stored: %s", reason_msg)
                    await repo.save_unmatched_event(
                        event_id=resolved_event_id,
                        event_type=event_name,
                        payload_json=payload_str,
                        reason=reason_msg,
                        signature=signature,
                    )
                    await repo.update_webhook_status(resolved_event_id, status="unmatched")
                    return {
                        "status": "unmatched_stored",
                        "event_id": resolved_event_id,
                        "reason": reason_msg,
                    }

                case, matched_field, matched_value = match_result
                workflow = self.orchestrator.create_workflow(repo)

                # Validate financial amount & currency
                currency_match = captured_ctx.currency.upper() == case.context.currency.upper()
                amount_diff = abs(captured_ctx.amount_inr - case.context.amount_inr)
                amount_valid = amount_diff <= 0.05

                if not currency_match or not amount_valid:
                    logger.warning(
                        "Financial mismatch for Case %s: expected %s %s, got %s %s. Holding for review.",
                        case.case_id,
                        case.context.currency,
                        case.context.amount_inr,
                        captured_ctx.currency,
                        captured_ctx.amount_inr,
                    )
                    outcome = await workflow.handle_payment_success(
                        case=case,
                        payment_id=captured_ctx.payment_id,
                        amount_inr=captured_ctx.amount_inr,
                        currency=captured_ctx.currency,
                        matched_field=matched_field,
                        matched_value=matched_value,
                    )
                    await repo.update_webhook_status(resolved_event_id, status="completed")
                    return {
                        "status": "held_for_review",
                        "case_id": case.case_id,
                        "event_id": resolved_event_id,
                        "reason": f"Financial mismatch: expected {case.context.currency} {case.context.amount_inr}, received {captured_ctx.currency} {captured_ctx.amount_inr}",
                    }

                # Atomic insertion into recovery ledger
                ledger_id = f"led_{uuid.uuid4().hex[:12]}"
                is_new_ledger, ledger_rec = await repo.record_recovery_ledger(
                    ledger_id=ledger_id,
                    case_id=case.case_id,
                    provider_payment_id=provider_payment_id,
                    event_id=resolved_event_id,
                    event_type=event_name,
                    amount_inr=captured_ctx.amount_inr,
                    currency=captured_ctx.currency,
                    matched_field=matched_field,
                    matched_value=matched_value,
                )

                if not is_new_ledger:
                    logger.info("Payment %s already registered in recovery ledger", provider_payment_id)
                    await repo.update_webhook_status(resolved_event_id, status="completed")
                    return {
                        "status": "recovered",
                        "duplicate_ignored": True,
                        "case_id": case.case_id,
                        "provider_payment_id": provider_payment_id,
                        "recovered_amount": ledger_rec.amount_inr,
                        "ledger_id": ledger_rec.ledger_id,
                    }

                # Process success transition & cancel pending work
                outcome = await workflow.handle_payment_success(
                    case=case,
                    payment_id=captured_ctx.payment_id,
                    amount_inr=captured_ctx.amount_inr,
                    currency=captured_ctx.currency,
                    matched_field=matched_field,
                    matched_value=matched_value,
                )
                await repo.update_webhook_status(resolved_event_id, status="completed")

                return {
                    "status": "recovered",
                    "event_id": resolved_event_id,
                    "case_id": case.case_id,
                    "provider_payment_id": provider_payment_id,
                    "matched_by": matched_field,
                    "matched_value": matched_value,
                    "recovered_amount": outcome.recovered_amount,
                    "ledger_id": ledger_id,
                }

            # Unhandled event types
            await repo.update_webhook_status(resolved_event_id, status="completed")
            return {
                "status": "accepted",
                "event_id": resolved_event_id,
                "event": event_name,
            }

        if session:
            return await _execute(session)
        else:
            async with async_session_factory() as s:
                res = await _execute(s)
                await s.commit()
                return res


# Global singleton instance
event_processor = UnifiedEventProcessor()
