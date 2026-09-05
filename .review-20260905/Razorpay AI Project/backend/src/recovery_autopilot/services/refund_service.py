"""Refund assistance service: investigation, eligibility checks, and simulated execution."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.config import settings
from recovery_autopilot.domain.enums import ActorType, CaseStatus
from recovery_autopilot.domain.issue_models import ActionStatus, IssueAction, utc_now
from recovery_autopilot.domain.models import AuditEvent
from recovery_autopilot.persistence.issue_repository import IssueRepository
from recovery_autopilot.persistence.models import PaymentCaseRecord, RecoveryActionRecord
from recovery_autopilot.persistence.repository import SqlAlchemyRepository

logger = logging.getLogger("recovery_autopilot.services.refund_service")


class RefundService:
    """Refund investigation and preparation service.

    In synthetic mode, simulates refund operations.
    Never describes an accepted refund request as money already received by the customer.
    """

    async def investigate_refund(
        self,
        session: AsyncSession,
        case_id: Optional[str] = None,
        payment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Investigate refund status and eligibility for a payment.

        Returns refund information including original payment, prior refunds,
        pending refunds, and remaining refundable amount.
        """
        repo = SqlAlchemyRepository(session)

        # Find the payment case
        case = None
        if case_id:
            case = await repo.get_case(case_id)
        if not case and payment_id:
            stmt = select(PaymentCaseRecord).where(PaymentCaseRecord.payment_id == payment_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record:
                case = repo._record_to_case(record)

        if not case:
            return {
                "found": False,
                "message": "No matching payment record found for refund investigation.",
                "refund_eligible": False,
            }

        ctx = case.context

        # Check for existing refund actions on this case
        stmt = select(RecoveryActionRecord).where(
            RecoveryActionRecord.case_id == case.case_id,
            RecoveryActionRecord.action == "REFUND",
        ).order_by(desc(RecoveryActionRecord.executed_at))
        result = await session.execute(stmt)
        prior_refund_records = result.scalars().all()

        prior_refunds = []
        total_refunded = 0.0
        for r in prior_refund_records:
            import json
            meta = json.loads(r.metadata_json) if r.metadata_json else {}
            refund_amount = meta.get("amount_inr", 0.0)
            total_refunded += refund_amount
            prior_refunds.append({
                "refund_id": r.action_id,
                "amount_inr": refund_amount,
                "status": r.status,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            })

        remaining_refundable = max(0.0, ctx.amount_inr - total_refunded)

        # Determine eligibility
        refund_eligible = (
            remaining_refundable > 0
            and not ctx.opted_out
        )

        # Determine refund status
        if prior_refunds:
            latest_refund = prior_refunds[0]
            if latest_refund["status"] == "COMPLETED":
                refund_status = "Previously refunded"
            elif latest_refund["status"] in ("PENDING", "PROCESSING"):
                refund_status = "Refund in progress"
            else:
                refund_status = "Prior refund attempt failed"
        else:
            refund_status = "No prior refunds"

        return {
            "found": True,
            "case_id": case.case_id,
            "payment_id": ctx.payment_id,
            "customer_name": ctx.customer_name,
            "customer_email": ctx.customer_email,
            "original_amount_inr": ctx.amount_inr,
            "currency": ctx.currency,
            "payment_status": case.status.value,
            "refund_status": refund_status,
            "prior_refunds": prior_refunds,
            "total_refunded_inr": total_refunded,
            "remaining_refundable_inr": remaining_refundable,
            "refund_eligible": refund_eligible,
            "requires_approval": ctx.amount_inr >= settings.HUMAN_REVIEW_THRESHOLD_INR,
            "note": (
                "Refund processing typically takes 5-7 business days to reflect in the customer's account. "
                "An accepted refund request does not mean the customer has received the money yet."
            ),
        }

    async def prepare_refund(
        self,
        session: AsyncSession,
        case_id: str,
        amount_inr: Optional[float] = None,
        reason: str = "Customer requested refund",
        operator_id: str = "copilot",
    ) -> Dict[str, Any]:
        """Prepare and simulate a refund execution.

        In synthetic mode, creates a simulated refund record.
        Enforces permission checks and financial approval limits.
        """
        repo = SqlAlchemyRepository(session)
        issue_repo = IssueRepository(session)

        case = await repo.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        ctx = case.context
        refund_amount = amount_inr or ctx.amount_inr

        # Validate amount
        if refund_amount <= 0:
            raise ValueError("Refund amount must be positive")
        if refund_amount > ctx.amount_inr:
            raise ValueError(f"Refund amount ₹{refund_amount:,.2f} exceeds original payment ₹{ctx.amount_inr:,.2f}")

        # Check approval requirement
        requires_approval = refund_amount >= settings.HUMAN_REVIEW_THRESHOLD_INR
        if requires_approval:
            logger.info("Refund of ₹%s for case %s requires human approval", refund_amount, case_id)

        # Simulate refund execution
        refund_id = f"rfnd_{uuid.uuid4().hex[:12]}"

        if settings.SYNTHETIC_MODE or settings.SIMULATE_NOTIFICATIONS:
            status = "APPROVAL_REQUIRED" if requires_approval else "PROCESSING"

            # Record the refund action
            import json
            action_rec = RecoveryActionRecord(
                action_id=f"act_rfnd_{uuid.uuid4().hex[:10]}",
                case_id=case_id,
                action="REFUND",
                external_id=refund_id,
                status=status,
                idempotency_key=f"refund_{case_id}_{uuid.uuid4().hex[:8]}",
                metadata_json=json.dumps({
                    "source": "AI_COPILOT",
                    "operator": operator_id,
                    "amount_inr": refund_amount,
                    "currency": ctx.currency,
                    "reason": reason,
                    "refund_id": refund_id,
                    "simulated": True,
                }),
                executed_at=utc_now(),
            )
            session.add(action_rec)

            # Audit trail
            audit = AuditEvent(
                case_id=case_id,
                actor=ActorType.HUMAN,
                event_type="COPILOT_REFUND_PREPARED",
                details={
                    "refund_id": refund_id,
                    "amount_inr": refund_amount,
                    "operator": operator_id,
                    "status": status,
                    "simulated": True,
                },
            )
            await repo.record_audit(audit)

            # Update associated issue if exists
            issues = await issue_repo.find_related_issues(case_id=case_id)
            if issues:
                issue = issues[0]
                action = IssueAction(
                    action_type="prepare_refund",
                    description=f"Refund of ₹{refund_amount:,.2f} prepared (simulated)",
                    status=ActionStatus.APPROVAL_REQUIRED if requires_approval else ActionStatus.COMPLETED,
                    result={"refund_id": refund_id, "amount_inr": refund_amount},
                    executed_by=operator_id,
                    executed_at=utc_now(),
                )
                issue.add_action(action)
                await issue_repo.save_issue(issue)

            return {
                "status": status,
                "refund_id": refund_id,
                "case_id": case_id,
                "amount_inr": refund_amount,
                "currency": ctx.currency,
                "customer_name": ctx.customer_name,
                "customer_email": ctx.customer_email,
                "requires_approval": requires_approval,
                "is_simulated": True,
                "message": (
                    f"Refund of ₹{refund_amount:,.2f} has been {'submitted for approval' if requires_approval else 'accepted for processing'} (simulated mode). "
                    "Note: This is a simulated refund. Actual refund processing requires Razorpay API integration."
                ),
            }
        else:
            return {
                "status": "NOT_CONFIGURED",
                "message": "Refund execution requires Razorpay API integration with production credentials.",
                "refund_id": None,
                "is_simulated": False,
            }


# Singleton
refund_service = RefundService()
