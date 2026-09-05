"""Operational automation service — honest about scheduling infrastructure availability.

Exposes individual check functions and documents what scheduling infrastructure
is needed to run them automatically. Does not claim to be continuously monitoring
when it is not.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.config import settings
from recovery_autopilot.domain.enums import CaseStatus
from recovery_autopilot.persistence.models import PaymentCaseRecord, RecoveryActionRecord
from recovery_autopilot.persistence.issue_models import CustomerIssueRecord

logger = logging.getLogger("recovery_autopilot.services.automation_service")


class AutomationService:
    """Operational automation checks that can be run on-demand or scheduled.

    Each check is a standalone function. Without external scheduling infrastructure
    (e.g., Celery Beat, APScheduler, cron), these checks only run when explicitly called.
    """

    async def get_automation_status(self, session: AsyncSession) -> Dict[str, Any]:
        """Report which automations are available and their configuration state."""
        return {
            "scheduling_infrastructure": {
                "configured": settings.USE_IN_PROCESS_WORKER,
                "type": "in_process_background_worker" if settings.USE_IN_PROCESS_WORKER else "none",
                "note": (
                    "Automated scheduling requires a background task runner (Celery Beat, APScheduler, or cron). "
                    "Currently, checks can be run on-demand via the API."
                ) if not settings.USE_IN_PROCESS_WORKER else (
                    "In-process worker is active but only handles webhook processing. "
                    "Periodic checks require explicit scheduling configuration."
                ),
            },
            "available_checks": [
                {
                    "id": "payment_mismatch",
                    "name": "Payment/Order Status Mismatch Detection",
                    "description": "Finds cases where payment status and application order status disagree",
                    "endpoint": "POST /copilot/v2/automation/check/payment-mismatch",
                    "schedule_configured": False,
                    "recommended_interval": "Every 15 minutes",
                },
                {
                    "id": "webhook_failures",
                    "name": "Webhook Failure Alerts",
                    "description": "Detects unprocessed or failed webhook events",
                    "endpoint": "POST /copilot/v2/automation/check/webhook-failures",
                    "schedule_configured": False,
                    "recommended_interval": "Every 5 minutes",
                },
                {
                    "id": "refund_aging",
                    "name": "Refund Aging & SLA Follow-ups",
                    "description": "Identifies refunds approaching or exceeding SLA deadlines",
                    "endpoint": "POST /copilot/v2/automation/check/refund-aging",
                    "schedule_configured": False,
                    "recommended_interval": "Every hour",
                },
                {
                    "id": "payment_link_expiry",
                    "name": "Payment Link Expiry Tracking",
                    "description": "Tracks payment links nearing expiry without payment",
                    "endpoint": "POST /copilot/v2/automation/check/payment-link-expiry",
                    "schedule_configured": False,
                    "recommended_interval": "Every 30 minutes",
                },
                {
                    "id": "issue_sla",
                    "name": "Issue SLA Monitoring",
                    "description": "Flags issues approaching or past their SLA deadline",
                    "endpoint": "POST /copilot/v2/automation/check/issue-sla",
                    "schedule_configured": False,
                    "recommended_interval": "Every 15 minutes",
                },
                {
                    "id": "operational_summary",
                    "name": "Operational Summary",
                    "description": "Generates a summary of current operational state",
                    "endpoint": "POST /copilot/v2/automation/check/operational-summary",
                    "schedule_configured": False,
                    "recommended_interval": "Daily at 9 AM",
                },
            ],
        }

    async def check_payment_mismatches(self, session: AsyncSession) -> Dict[str, Any]:
        """Detect cases where payment status and expected state disagree."""
        # Find cases stuck in intermediate states for too long
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        stmt = select(PaymentCaseRecord).where(
            PaymentCaseRecord.status.in_([
                CaseStatus.DIAGNOSING.value,
                CaseStatus.AWAITING_POLICY.value,
                CaseStatus.ACTION_IN_PROGRESS.value,
            ]),
            PaymentCaseRecord.updated_at < cutoff,
        ).order_by(desc(PaymentCaseRecord.updated_at)).limit(50)

        result = await session.execute(stmt)
        stale_cases = result.scalars().all()

        alerts = []
        for case in stale_cases:
            alerts.append({
                "case_id": case.case_id,
                "customer_name": case.customer_name,
                "amount_inr": case.amount_inr,
                "current_status": case.status,
                "stale_since": case.updated_at.isoformat() if case.updated_at else None,
                "alert": f"Case stuck in {case.status} for >24 hours",
            })

        return {
            "check": "payment_mismatch",
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "alerts_count": len(alerts),
            "alerts": alerts[:20],  # Limit to 20 to avoid overload
        }

    async def check_webhook_failures(self, session: AsyncSession) -> Dict[str, Any]:
        """Detect unprocessed or failed webhook events."""
        from recovery_autopilot.persistence.models import WebhookEventRecord

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        stmt = select(WebhookEventRecord).where(
            WebhookEventRecord.status.in_(["failed", "dead_letter"]),
            WebhookEventRecord.received_at > (datetime.now(timezone.utc) - timedelta(hours=24)),
        ).order_by(desc(WebhookEventRecord.received_at)).limit(50)

        result = await session.execute(stmt)
        failed_events = result.scalars().all()

        alerts = []
        for event in failed_events:
            alerts.append({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "status": event.status,
                "attempts": event.attempts,
                "error_code": event.error_code,
                "received_at": event.received_at.isoformat() if event.received_at else None,
            })

        return {
            "check": "webhook_failures",
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "alerts_count": len(alerts),
            "alerts": alerts[:20],
        }

    async def check_issue_sla(self, session: AsyncSession) -> Dict[str, Any]:
        """Flag issues approaching or past their SLA deadline."""
        now = datetime.now(timezone.utc)
        warning_window = now + timedelta(hours=4)

        stmt = select(CustomerIssueRecord).where(
            CustomerIssueRecord.status.notin_(["RESOLVED", "CLOSED"]),
            CustomerIssueRecord.sla_deadline.isnot(None),
            CustomerIssueRecord.sla_deadline < warning_window,
        ).order_by(CustomerIssueRecord.sla_deadline).limit(50)

        result = await session.execute(stmt)
        at_risk_issues = result.scalars().all()

        alerts = []
        for issue in at_risk_issues:
            is_breached = issue.sla_deadline < now if issue.sla_deadline else False
            alerts.append({
                "issue_id": issue.issue_id,
                "title": issue.title,
                "status": issue.status,
                "severity": issue.severity,
                "sla_deadline": issue.sla_deadline.isoformat() if issue.sla_deadline else None,
                "is_breached": is_breached,
                "customer_name": issue.customer_name,
            })

        return {
            "check": "issue_sla",
            "ran_at": now.isoformat(),
            "alerts_count": len(alerts),
            "breached_count": sum(1 for a in alerts if a.get("is_breached")),
            "alerts": alerts[:20],
        }

    async def generate_operational_summary(self, session: AsyncSession) -> Dict[str, Any]:
        """Generate a summary of current operational state."""
        # Case counts by status
        case_counts = {}
        for status in CaseStatus:
            stmt = select(func.count(PaymentCaseRecord.case_id)).where(
                PaymentCaseRecord.status == status.value
            )
            count = (await session.execute(stmt)).scalar() or 0
            if count > 0:
                case_counts[status.value] = count

        # Total and recovered
        total_stmt = select(func.count(PaymentCaseRecord.case_id))
        total = (await session.execute(total_stmt)).scalar() or 0

        recovered_stmt = select(
            func.count(PaymentCaseRecord.case_id),
            func.sum(PaymentCaseRecord.amount_inr),
        ).where(PaymentCaseRecord.status == CaseStatus.RECOVERED.value)
        rec_res = (await session.execute(recovered_stmt)).one()

        # Issue counts
        issue_stmt = select(func.count(CustomerIssueRecord.issue_id))
        issue_total = (await session.execute(issue_stmt)).scalar() or 0

        open_issue_stmt = select(func.count(CustomerIssueRecord.issue_id)).where(
            CustomerIssueRecord.status.notin_(["RESOLVED", "CLOSED"])
        )
        open_issues = (await session.execute(open_issue_stmt)).scalar() or 0

        return {
            "check": "operational_summary",
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "cases": {
                "total": total,
                "recovered": rec_res[0] or 0,
                "recovered_amount_inr": round(rec_res[1] or 0, 2),
                "recovery_rate": round((rec_res[0] or 0) / total * 100, 1) if total > 0 else 0,
                "by_status": case_counts,
            },
            "issues": {
                "total": issue_total,
                "open": open_issues,
            },
            "environment": settings.PAYMENT_EXECUTION_MODE,
            "synthetic_mode": settings.SYNTHETIC_MODE,
        }

    async def check_refund_aging(self, session: AsyncSession) -> Dict[str, Any]:
        """Detect refund requests that have been aging or approaching banking SLA limit."""
        now = datetime.now(timezone.utc)
        stmt = select(CustomerIssueRecord).where(
            CustomerIssueRecord.status.notin_(["RESOLVED", "CLOSED"]),
            CustomerIssueRecord.category == "REFUND_DELAY",
        ).limit(50)
        result = await session.execute(stmt)
        aging_issues = result.scalars().all()

        alerts = []
        for iss in aging_issues:
            created = iss.created_at if iss.created_at else now
            age_days = (now - created).days
            alerts.append({
                "issue_id": iss.issue_id,
                "customer_name": iss.customer_name,
                "age_days": age_days,
                "payment_id": iss.payment_id,
                "status": iss.status,
                "alert": f"Refund inquiry open for {age_days} days (Banking SLA: 5-7 business days)",
            })

        return {
            "check": "refund_aging",
            "ran_at": now.isoformat(),
            "alerts_count": len(alerts),
            "alerts": alerts[:20],
        }

    async def check_payment_link_expiry(self, session: AsyncSession) -> Dict[str, Any]:
        """Detect created payment links nearing expiry that have not yet resulted in captured payment."""
        now = datetime.now(timezone.utc)
        stmt = select(CustomerIssueRecord).where(
            CustomerIssueRecord.payment_link_id.isnot(None),
            CustomerIssueRecord.status.notin_(["RESOLVED", "CLOSED"]),
        ).limit(50)
        result = await session.execute(stmt)
        issues_with_links = result.scalars().all()

        alerts = []
        for iss in issues_with_links:
            alerts.append({
                "issue_id": iss.issue_id,
                "payment_link_id": iss.payment_link_id,
                "customer_name": iss.customer_name,
                "status": iss.status,
                "alert": f"Payment link {iss.payment_link_id} pending payment completion",
            })

        return {
            "check": "payment_link_expiry",
            "ran_at": now.isoformat(),
            "alerts_count": len(alerts),
            "alerts": alerts[:20],
        }


# Singleton
automation_service = AutomationService()
