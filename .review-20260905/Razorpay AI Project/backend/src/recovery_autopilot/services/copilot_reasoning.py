"""AI Copilot reasoning engine with structured tool calling and evidence-based investigation.

The model proposes tool actions; the backend independently validates permissions,
merchant scope, environment, inputs, and approval requirements.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.config import settings
from recovery_autopilot.domain.enums import ActorType, CaseStatus, FailureCategory
from recovery_autopilot.domain.issue_models import (
    ActionStatus,
    ConfidenceLevel,
    CustomerIssue,
    EnvironmentMode,
    IssueAction,
    IssueCategory,
    IssueCause,
    IssueEvidence,
    IssueSeverity,
    IssueStatus,
    utc_now,
)
from recovery_autopilot.domain.models import AuditEvent
from recovery_autopilot.model_providers.factory import get_model_provider
from recovery_autopilot.persistence.issue_repository import IssueRepository
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.policies.copilot_reasons import get_reason_detail
from recovery_autopilot.services.copilot_service import CopilotService, mask_phone

logger = logging.getLogger("recovery_autopilot.services.copilot_reasoning")


# --- Tool Definitions (structured schemas for model interaction) ---

COPILOT_TOOLS = {
    "lookup_payment": {
        "description": "Look up a payment case by payment ID, case ID, email, or customer name",
        "parameters": {
            "payment_id": {"type": "string", "description": "Razorpay payment ID (e.g. pay_xxx)"},
            "case_id": {"type": "string", "description": "Internal case ID (e.g. case_xxx)"},
            "email": {"type": "string", "description": "Customer email address"},
            "customer_name": {"type": "string", "description": "Customer name"},
        },
    },
    "lookup_customer_cases": {
        "description": "Find all payment cases for a customer by email or name",
        "parameters": {
            "email": {"type": "string"},
            "customer_name": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
        },
    },
    "check_webhook_events": {
        "description": "Check webhook event history for a payment or case",
        "parameters": {
            "case_id": {"type": "string"},
            "payment_id": {"type": "string"},
        },
    },
    "check_payment_link_status": {
        "description": "Check the current status of a payment link",
        "parameters": {
            "payment_link_id": {"type": "string"},
            "case_id": {"type": "string"},
        },
    },
    "create_payment_link": {
        "description": "Create a Razorpay payment link for a case",
        "parameters": {
            "case_id": {"type": "string", "required": True},
            "amount_inr": {"type": "number", "required": True},
            "customer_email": {"type": "string", "required": True},
            "customer_phone": {"type": "string", "required": True},
            "note": {"type": "string"},
        },
    },
    "draft_email": {
        "description": "Generate an email draft from a template",
        "parameters": {
            "template": {"type": "string", "enum": ["payment_failure", "payment_link", "refund_update", "resolution", "escalation"]},
            "issue_id": {"type": "string"},
            "case_id": {"type": "string"},
        },
    },
    "update_issue_status": {
        "description": "Transition the issue status",
        "parameters": {
            "issue_id": {"type": "string", "required": True},
            "new_status": {"type": "string", "required": True, "enum": ["INVESTIGATING", "AWAITING_INFO", "ACTION_IN_PROGRESS", "MONITORING", "RESOLVED", "CLOSED"]},
            "reason": {"type": "string"},
        },
    },
}


class CopilotStep:
    """Represents a single step in the Copilot investigation."""

    def __init__(self, step_type: str, title: str, status: str = "pending"):
        self.step_id = f"step_{uuid.uuid4().hex[:8]}"
        self.step_type = step_type  # query_understanding, evidence_gathering, analysis, recommendation, action
        self.title = title
        self.status = status  # pending, running, completed, failed
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def start(self):
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)

    def complete(self, result: Dict[str, Any]):
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error: str):
        self.status = "failed"
        self.error = error
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type,
            "title": self.title,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


class CopilotReasoningEngine:
    """Orchestrates multi-step Copilot investigations with evidence-based reasoning.

    Architecture:
    - Model proposes what to do (or heuristic engine if no model configured)
    - Backend validates permissions, merchant scope, environment
    - Tools execute with narrowly scoped DB access
    - Results are verified before presentation
    - Credentials never sent to model
    """

    def __init__(self):
        self.copilot_service = CopilotService()

    async def investigate(
        self,
        session: AsyncSession,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        image_base64: Optional[str] = None,
        operator_id: str = "copilot",
    ) -> Dict[str, Any]:
        """Run a full investigation pipeline.

        Returns structured result with steps, evidence, causes, recommendations, and available actions.
        """
        steps: List[CopilotStep] = []
        repo = SqlAlchemyRepository(session)
        issue_repo = IssueRepository(session)

        # Step 1: Understand the request
        step1 = CopilotStep("query_understanding", "Understanding your request")
        step1.start()
        entities = self.copilot_service.extract_entities(query)
        context_info = context or {}
        step1.complete({
            "entities_found": {k: v for k, v in entities.items() if v is not None},
            "context_page": context_info.get("current_page"),
            "context_case_id": context_info.get("case_id"),
            "context_customer": context_info.get("customer_email"),
        })
        steps.append(step1)

        # Merge context into entity extraction
        if context_info.get("case_id") and not entities.get("case_id"):
            entities["case_id"] = context_info["case_id"]
        if context_info.get("customer_email") and not entities.get("email"):
            entities["email"] = context_info["customer_email"]
        if context_info.get("payment_id") and not entities.get("payment_id"):
            entities["payment_id"] = context_info["payment_id"]

        # Step 2: Retrieve relevant records
        step2 = CopilotStep("evidence_gathering", "Retrieving payment records and evidence")
        step2.start()

        matched_record = await self.copilot_service.match_case(session, entities, query)
        if not matched_record:
            step2.complete({"found": False, "message": "No matching payment record found"})
            steps.append(step2)
            return self._build_no_match_response(steps, entities, query)

        # Build evidence from matched record
        evidence_items: List[IssueEvidence] = []
        evidence_items.append(IssueEvidence(
            source="payment_record",
            description=f"Payment {matched_record.payment_id} for ₹{matched_record.amount_inr:,.2f} by {matched_record.customer_name}",
            raw_data={
                "payment_id": matched_record.payment_id,
                "case_id": matched_record.case_id,
                "customer_name": matched_record.customer_name,
                "customer_email": matched_record.customer_email,
                "amount_inr": matched_record.amount_inr,
                "currency": matched_record.currency or "INR",
                "status": matched_record.status,
                "failure_category": matched_record.failure_category,
                "failure_code": matched_record.failure_code,
                "failure_reason": matched_record.failure_reason,
                "payment_method": matched_record.payment_method,
                "bank_name": matched_record.bank_name,
                "bank_degraded": matched_record.bank_degraded,
                "contact_count": matched_record.contact_count,
                "created_at": matched_record.created_at.isoformat() if matched_record.created_at else None,
            },
            confidence=ConfidenceLevel.HIGH,
        ))

        # Check for existing payment links
        if matched_record.payment_link_id:
            evidence_items.append(IssueEvidence(
                source="payment_link_record",
                description=f"Existing payment link {matched_record.payment_link_id} found for this case",
                raw_data={"payment_link_id": matched_record.payment_link_id},
                confidence=ConfidenceLevel.HIGH,
            ))

        # Check webhook events for this case
        audit_events = await repo.get_audit_events(matched_record.case_id)
        if audit_events:
            evidence_items.append(IssueEvidence(
                source="audit_trail",
                description=f"{len(audit_events)} audit events found for this case",
                raw_data={"event_count": len(audit_events), "latest_event": audit_events[-1].event_type if audit_events else None},
                confidence=ConfidenceLevel.HIGH,
            ))

        step2.complete({
            "found": True,
            "case_id": matched_record.case_id,
            "payment_id": matched_record.payment_id,
            "customer": matched_record.customer_name,
            "amount_inr": matched_record.amount_inr,
            "evidence_count": len(evidence_items),
        })
        steps.append(step2)

        # Step 3: Analyze and identify causes
        step3 = CopilotStep("analysis", "Analyzing evidence and identifying causes")
        step3.start()

        category_enum = FailureCategory(matched_record.failure_category) if matched_record.failure_category in FailureCategory.__members__ else FailureCategory.UNKNOWN_FAILURE
        reason_detail = get_reason_detail(category_enum)

        causes: List[IssueCause] = []

        # Primary cause from failure category
        primary_cause = IssueCause(
            description=reason_detail.explanation,
            confidence=ConfidenceLevel.HIGH,
            supporting_evidence=[evidence_items[0].evidence_id],
            is_confirmed=True,
            recommended_action=reason_detail.resolution_instruction,
        )
        causes.append(primary_cause)

        # Additional causes based on context
        if matched_record.bank_degraded:
            causes.append(IssueCause(
                description="Bank network is currently experiencing degradation, which may have contributed to the failure",
                confidence=ConfidenceLevel.MEDIUM,
                supporting_evidence=[evidence_items[0].evidence_id],
                recommended_action="Wait for bank network recovery and then retry the payment",
            ))

        if matched_record.contact_count >= 3:
            causes.append(IssueCause(
                description="Customer has been contacted multiple times without resolution — escalation may be needed",
                confidence=ConfidenceLevel.MEDIUM,
                supporting_evidence=[evidence_items[0].evidence_id],
                recommended_action="Escalate to senior support or offer alternative payment arrangement",
            ))

        step3.complete({
            "primary_cause": primary_cause.description[:80],
            "cause_count": len(causes),
            "confidence": primary_cause.confidence.value,
        })
        steps.append(step3)

        # Step 4: Generate recommendations
        step4 = CopilotStep("recommendation", "Preparing evidence-backed recommendations")
        step4.start()

        formatted_amount = f"{matched_record.amount_inr:,.0f}" if matched_record.amount_inr == int(matched_record.amount_inr) else f"{matched_record.amount_inr:,.2f}"
        headline = reason_detail.headline_template.format(
            customer=matched_record.customer_name,
            amount=formatted_amount,
        )
        recommendation = reason_detail.recommendation.format(customer=matched_record.customer_name)

        # Build available actions
        available_actions = []
        available_actions.append({
            "action": "create_payment_link",
            "label": f"Generate payment link for {matched_record.customer_name}",
            "enabled": True,
            "requires_approval": matched_record.amount_inr >= settings.HUMAN_REVIEW_THRESHOLD_INR,
        })
        available_actions.append({
            "action": "draft_email",
            "label": f"Draft email to {matched_record.customer_name}",
            "enabled": True,
            "requires_approval": False,
        })
        available_actions.append({
            "action": "check_refund",
            "label": "Check refund eligibility",
            "enabled": True,
            "requires_approval": False,
        })
        available_actions.append({
            "action": "escalate",
            "label": "Escalate issue",
            "enabled": True,
            "requires_approval": False,
        })

        step4.complete({
            "headline": headline,
            "recommendation": recommendation,
            "actions_available": len(available_actions),
        })
        steps.append(step4)

        # Step 5: Create or update issue
        step5 = CopilotStep("issue_tracking", "Recording investigation in issue tracker")
        step5.start()

        # Check for existing issue to avoid duplicates
        existing_issues = await issue_repo.find_related_issues(
            payment_id=matched_record.payment_id,
            case_id=matched_record.case_id,
        )

        if existing_issues:
            issue = existing_issues[0]
            # Update with new evidence
            for ev in evidence_items:
                issue.add_evidence(ev)
            for cause in causes:
                # Avoid duplicate causes
                existing_descs = [c.description for c in issue.possible_causes]
                if cause.description not in existing_descs:
                    issue.add_cause(cause)
            if issue.status == IssueStatus.NEW:
                issue.transition_status(IssueStatus.INVESTIGATING, actor=operator_id, reason="Copilot investigation started")
        else:
            issue = CustomerIssue(
                title=headline,
                category=self._map_failure_to_issue_category(category_enum),
                severity=self._assess_severity(matched_record.amount_inr, matched_record.contact_count),
                status=IssueStatus.INVESTIGATING,
                environment=EnvironmentMode.TEST if settings.SYNTHETIC_MODE else EnvironmentMode.LIVE,
                customer_id=matched_record.customer_id,
                customer_name=matched_record.customer_name,
                customer_email=matched_record.customer_email,
                payment_id=matched_record.payment_id,
                case_id=matched_record.case_id,
                owner=operator_id,
                reported_symptoms=query,
                actual_behavior=matched_record.failure_reason,
                evidence=evidence_items,
                possible_causes=causes,
            )
            issue.transition_status(IssueStatus.INVESTIGATING, actor="copilot", reason="Auto-created from Copilot investigation")

        await issue_repo.save_issue(issue)

        step5.complete({"issue_id": issue.issue_id, "is_new": len(existing_issues) == 0})
        steps.append(step5)

        # Build the full response
        return {
            "type": "investigation",
            "issue_id": issue.issue_id,
            "case_id": matched_record.case_id,
            "steps": [s.to_dict() for s in steps],
            "what_happened": {
                "headline": headline,
                "explanation": reason_detail.explanation,
                "auto_reversal_timeline": reason_detail.auto_reversal_timeline,
                "timeline": [
                    {
                        "timestamp": matched_record.created_at.isoformat() if matched_record.created_at else None,
                        "event": f"Payment {matched_record.payment_id} failed",
                        "details": matched_record.failure_reason,
                    },
                ] + [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "event": e.event_type.replace("_", " ").title(),
                        "details": str(e.details.get("reason", e.details.get("operator", "")))[:100],
                    }
                    for e in audit_events[-5:]  # Last 5 events
                ],
            },
            "verified_evidence": [
                {
                    "evidence_id": ev.evidence_id,
                    "source": ev.source,
                    "description": ev.description,
                    "confidence": ev.confidence.value,
                }
                for ev in evidence_items
            ],
            "possible_causes": [
                {
                    "cause_id": c.cause_id,
                    "description": c.description,
                    "confidence": c.confidence.value,
                    "supporting_evidence": c.supporting_evidence,
                    "contradicting_evidence": c.contradicting_evidence,
                    "missing_evidence": c.missing_evidence,
                    "recommended_action": c.recommended_action,
                    "is_confirmed": c.is_confirmed,
                }
                for c in causes
            ],
            "recommended_solution": {
                "resolution_name": reason_detail.resolution_name,
                "resolution_instruction": reason_detail.resolution_instruction,
                "recommendation": recommendation,
            },
            "available_actions": available_actions,
            "diagnosis": {
                "case_id": matched_record.case_id,
                "payment_id": matched_record.payment_id,
                "customer_name": matched_record.customer_name,
                "customer_email": matched_record.customer_email,
                "customer_phone": matched_record.customer_phone,
                "masked_phone": mask_phone(matched_record.customer_phone),
                "amount_inr": matched_record.amount_inr,
                "currency": matched_record.currency or "INR",
                "failure_category": matched_record.failure_category,
                "failure_reason": matched_record.failure_reason,
                "headline": headline,
                "explanation": reason_detail.explanation,
                "auto_reversal_timeline": reason_detail.auto_reversal_timeline,
                "resolution_name": reason_detail.resolution_name,
                "resolution_instruction": reason_detail.resolution_instruction,
                "recommendation": recommendation,
            },
            "suggestions": self._build_suggestions(matched_record, reason_detail),
        }

    def _build_no_match_response(self, steps: List[CopilotStep], entities: Dict, query: str) -> Dict[str, Any]:
        return {
            "type": "no_match",
            "steps": [s.to_dict() for s in steps],
            "what_happened": {
                "headline": "No matching payment record found",
                "explanation": "Could not locate a payment record matching the provided information.",
            },
            "message": (
                "I couldn't locate a matching payment record for this query. "
                "Please provide a **Payment ID** (e.g., `pay_xxx`), **Customer Email**, "
                "or **Customer Name** to investigate the issue."
            ),
            "verified_evidence": [],
            "possible_causes": [],
            "recommended_solution": None,
            "available_actions": [],
            "suggestions": [
                {"id": "s_1", "text": "Analyse all my failed payments", "action": "ANALYZE_ALL"},
                {"id": "s_2", "text": "Search by Customer Email", "action": "SEARCH_EMAIL"},
                {"id": "s_3", "text": "How do I create a payment link?", "action": "HELP_PAYMENT_LINK"},
            ],
        }

    def _build_suggestions(self, record, reason_detail) -> List[Dict]:
        followup_texts = [f.format(customer=record.customer_name) for f in reason_detail.default_followups]
        suggestions = []
        for i, text in enumerate(followup_texts):
            suggestions.append({
                "id": f"sug_{i+1}",
                "number": i + 1,
                "text": text,
                "action": "CREATE_PAYMENT_LINK" if i == 0 else "INFO_QUERY",
                "case_id": record.case_id,
            })
        # Add email and refund suggestions
        suggestions.append({
            "id": "sug_email",
            "text": f"Draft email to {record.customer_name}",
            "action": "DRAFT_EMAIL",
            "case_id": record.case_id,
        })
        suggestions.append({
            "id": "sug_refund",
            "text": "Check refund status",
            "action": "CHECK_REFUND",
            "case_id": record.case_id,
        })
        return suggestions

    def _map_failure_to_issue_category(self, fc: FailureCategory) -> IssueCategory:
        mapping = {
            FailureCategory.INSUFFICIENT_FUNDS: IssueCategory.PAYMENT_FAILURE,
            FailureCategory.BANK_TIMEOUT: IssueCategory.PAYMENT_FAILURE,
            FailureCategory.EXPIRED_CARD: IssueCategory.PAYMENT_FAILURE,
            FailureCategory.MANDATE_REVOKED: IssueCategory.PAYMENT_FAILURE,
            FailureCategory.LIMIT_EXCEEDED: IssueCategory.PAYMENT_FAILURE,
            FailureCategory.NETWORK_FAILURE: IssueCategory.PAYMENT_FAILURE,
            FailureCategory.CUSTOMER_ACTION_REQUIRED: IssueCategory.PAYMENT_FAILURE,
            FailureCategory.UNKNOWN_FAILURE: IssueCategory.PAYMENT_FAILURE,
        }
        return mapping.get(fc, IssueCategory.GENERAL_INQUIRY)

    def _assess_severity(self, amount_inr: float, contact_count: int) -> IssueSeverity:
        if amount_inr >= 50000 or contact_count >= 5:
            return IssueSeverity.CRITICAL
        elif amount_inr >= 15000 or contact_count >= 3:
            return IssueSeverity.HIGH
        elif amount_inr >= 5000:
            return IssueSeverity.MEDIUM
        return IssueSeverity.LOW

    async def get_context_suggestions(
        self,
        session: AsyncSession,
        current_page: Optional[str] = None,
        case_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        payment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate context-aware quick action suggestions based on the current page and selected entity."""
        suggestions = []

        if case_id:
            repo = SqlAlchemyRepository(session)
            case = await repo.get_case(case_id)
            if case:
                ctx = case.context
                suggestions.extend([
                    {"id": "ctx_investigate", "text": f"Investigate {ctx.customer_name}'s payment failure", "action": "INVESTIGATE", "icon": "search", "case_id": case_id},
                    {"id": "ctx_explain", "text": f"Explain why {ctx.customer_name}'s payment failed", "action": "EXPLAIN_FAILURE", "icon": "info", "case_id": case_id},
                    {"id": "ctx_timeline", "text": f"View {ctx.customer_name}'s timeline", "action": "VIEW_TIMELINE", "icon": "clock", "case_id": case_id},
                    {"id": "ctx_plink", "text": f"Generate payment link for ₹{ctx.amount_inr:,.0f}", "action": "CREATE_PAYMENT_LINK", "icon": "link", "case_id": case_id},
                    {"id": "ctx_refund", "text": "Check refund status", "action": "CHECK_REFUND", "icon": "refund", "case_id": case_id},
                    {"id": "ctx_email", "text": f"Draft email to {ctx.customer_name}", "action": "DRAFT_EMAIL", "icon": "mail", "case_id": case_id},
                    {"id": "ctx_escalate", "text": "Escalate issue", "action": "ESCALATE", "icon": "alert", "case_id": case_id},
                ])
        else:
            # Generic suggestions
            suggestions.extend([
                {"id": "gen_investigate", "text": "Investigate a payment issue", "action": "INVESTIGATE", "icon": "search"},
                {"id": "gen_failed", "text": "View all failed payments", "action": "ANALYZE_ALL", "icon": "list"},
                {"id": "gen_plink", "text": "Create a payment link", "action": "HELP_PAYMENT_LINK", "icon": "link"},
                {"id": "gen_refund", "text": "Check refund status", "action": "CHECK_REFUND", "icon": "refund"},
                {"id": "gen_email", "text": "Draft a customer email", "action": "DRAFT_EMAIL", "icon": "mail"},
                {"id": "gen_webhook", "text": "Investigate webhook issues", "action": "INVESTIGATE_WEBHOOK", "icon": "webhook"},
            ])

        return {
            "current_page": current_page,
            "case_id": case_id,
            "suggestions": suggestions,
        }


# Singleton
copilot_reasoning = CopilotReasoningEngine()
