"""Enhanced AI Copilot API v2 — investigation, issue tracking, email, refund, and automation endpoints.

All endpoints enforce RBAC, merchant isolation, and audit logging.
Backwards compatible: existing /copilot/ endpoints remain unchanged.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.domain.issue_models import IssueStatus
from recovery_autopilot.persistence.database import get_db
from recovery_autopilot.persistence.issue_repository import IssueRepository
from recovery_autopilot.security.rbac import OperatorRole, verify_operator_role
from recovery_autopilot.services.automation_service import automation_service
from recovery_autopilot.services.copilot_reasoning import copilot_reasoning
from recovery_autopilot.services.copilot_service import copilot_service
from recovery_autopilot.services.email_service import email_service
from recovery_autopilot.services.refund_service import refund_service

logger = logging.getLogger("recovery_autopilot.api.routes_copilot_v2")

router = APIRouter(prefix="/copilot/v2", tags=["AI Copilot V2"])


# --- Request/Response Schemas ---

class InvestigateRequest(BaseModel):
    query: str = Field(..., description="User query describing the issue to investigate")
    context: Optional[Dict[str, Any]] = Field(None, description="Current page context: {current_page, case_id, customer_email, payment_id}")
    image_base64: Optional[str] = Field(None, description="Optional base64 screenshot")

class ContextRequest(BaseModel):
    current_page: Optional[str] = Field(None)
    case_id: Optional[str] = Field(None)
    customer_email: Optional[str] = Field(None)
    payment_id: Optional[str] = Field(None)

class PaymentLinkRequest(BaseModel):
    case_id: str = Field(...)
    amount_inr: float = Field(..., gt=0)
    customer_email: str = Field(...)
    customer_phone: str = Field(...)
    expiry_date: Optional[str] = Field(None)
    note: Optional[str] = Field(None)

class EmailDraftRequest(BaseModel):
    template: Optional[str] = Field(None, description="Template ID: payment_failure, payment_link, refund_update, resolution, escalation")
    template_id: Optional[str] = Field(None, description="Template ID alias")
    case_id: Optional[str] = Field(None)
    issue_id: Optional[str] = Field(None)
    recipient_email: Optional[str] = Field(None, description="Override recipient. If not provided, uses case/issue customer email.")
    recipient_name: Optional[str] = Field(None)
    template_vars: Optional[Dict[str, Any]] = Field(None, description="Additional template variables")
    variables: Optional[Dict[str, Any]] = Field(None, description="Alias for template_vars")

class EmailSendRequest(BaseModel):
    draft_id: str = Field(...)

class RefundRequest(BaseModel):
    case_id: str = Field(...)
    amount_inr: Optional[float] = Field(None, gt=0, description="Refund amount. Defaults to original payment amount.")
    reason: str = Field("Customer requested refund")

class IssueCreateRequest(BaseModel):
    title: str = Field(...)
    category: str = Field("PAYMENT_FAILURE")
    severity: Optional[str] = Field("MEDIUM")
    customer_name: Optional[str] = Field(None)
    customer_email: Optional[str] = Field(None)
    payment_id: Optional[str] = Field(None)
    order_id: Optional[str] = Field(None)
    reported_symptoms: Optional[str] = Field(None)
    case_id: Optional[str] = Field(None)

class IssueUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="New status")
    severity: Optional[str] = Field(None)
    owner: Optional[str] = Field(None)
    resolution_summary: Optional[str] = Field(None)
    next_action: Optional[str] = Field(None)
    resolution_verified: Optional[bool] = Field(None)
    resolution_evidence: Optional[str] = Field(None)


# --- Investigation Endpoints ---

@router.post("/investigate", response_model=Dict[str, Any])
async def investigate(
    req: InvestigateRequest,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Run a full Copilot investigation pipeline.

    Returns structured results with steps, evidence, causes, recommendations, and available actions.
    """
    try:
        result = await copilot_reasoning.investigate(
            session=db,
            query=req.query,
            context=req.context,
            image_base64=req.image_base64,
            operator_id=operator_id or "copilot",
        )
        return result
    except Exception as exc:
        logger.error("Investigation failed: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Investigation failed: {str(exc)}")


@router.post("/context", response_model=Dict[str, Any])
async def get_context_suggestions(
    req: ContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Get context-aware quick action suggestions based on current page and selected entity."""
    try:
        result = await copilot_reasoning.get_context_suggestions(
            session=db,
            current_page=req.current_page,
            case_id=req.case_id,
            customer_email=req.customer_email,
            payment_id=req.payment_id,
        )
        return result
    except Exception as exc:
        logger.error("Context suggestions failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# --- Payment Link Endpoints ---

@router.post("/payment-link", response_model=Dict[str, Any])
@router.post("/actions/payment-link", response_model=Dict[str, Any])
async def create_payment_link(
    req: PaymentLinkRequest,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Create a Razorpay payment link with validation, duplicate detection, and issue association."""
    try:
        result = await copilot_service.create_payment_link(
            session=db,
            case_id=req.case_id,
            amount_inr=req.amount_inr,
            customer_email=req.customer_email,
            customer_phone=req.customer_phone,
            expiry_date=req.expiry_date,
            note=req.note,
            operator_name=operator_id or "copilot",
        )

        # Update associated issue
        issue_repo = IssueRepository(db)
        issues = await issue_repo.find_related_issues(case_id=req.case_id)
        if issues:
            from recovery_autopilot.domain.issue_models import ActionStatus, IssueAction, utc_now
            issue = issues[0]
            action = IssueAction(
                action_type="create_payment_link",
                description=f"Payment link created: {result.get('short_url', 'N/A')} for ₹{req.amount_inr:,.2f}",
                status=ActionStatus.COMPLETED,
                result=result,
                executed_by=operator_id or "copilot",
                executed_at=utc_now(),
            )
            issue.add_action(action)
            if issue.payment_link_id is None:
                issue.payment_link_id = result.get("payment_link_id")
            await issue_repo.save_issue(issue)

        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Payment link creation failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=f"Payment link creation failed: {str(exc)}")


# --- Email Endpoints ---

@router.post("/email/draft", response_model=Dict[str, Any])
@router.post("/actions/email/draft", response_model=Dict[str, Any])
async def create_email_draft(
    req: EmailDraftRequest,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Generate an email draft from a template with verified issue and transaction information."""
    try:
        from recovery_autopilot.persistence.repository import SqlAlchemyRepository

        repo = SqlAlchemyRepository(db)
        template_vars = req.variables or req.template_vars or {}
        template_id = req.template_id or req.template or "payment_failure"

        # Resolve recipient and template vars from case/issue
        recipient_email = req.recipient_email
        recipient_name = req.recipient_name or "Customer"

        if req.case_id:
            case = await repo.get_case(req.case_id)
            if case:
                ctx = case.context
                recipient_email = recipient_email or ctx.customer_email
                recipient_name = ctx.customer_name if recipient_name == "Customer" else recipient_name
                template_vars.setdefault("amount", f"{ctx.amount_inr:,.2f}")
                template_vars.setdefault("failure_reason", ctx.failure_reason)
                template_vars.setdefault("payment_id", ctx.payment_id)

                # Get reason detail for resolution instruction
                from recovery_autopilot.domain.enums import FailureCategory
                from recovery_autopilot.policies.copilot_reasons import get_reason_detail
                cat = FailureCategory(ctx.failure_category.value) if hasattr(ctx.failure_category, 'value') else FailureCategory.UNKNOWN_FAILURE
                reason_detail = get_reason_detail(cat)
                template_vars.setdefault("resolution_instruction", reason_detail.resolution_instruction)

        if req.issue_id:
            issue_repo = IssueRepository(db)
            issue = await issue_repo.get_issue(req.issue_id)
            if issue:
                recipient_email = recipient_email or issue.customer_email
                recipient_name = issue.customer_name or recipient_name
                template_vars.setdefault("issue_id", issue.issue_id)
                template_vars.setdefault("resolution_summary", issue.resolution_summary or "")

        if not recipient_email:
            raise ValueError("Cannot determine recipient email. Provide recipient_email, case_id, or issue_id.")

        draft = await email_service.generate_draft(
            session=db,
            template_id=template_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            template_vars=template_vars,
            issue_id=req.issue_id,
            case_id=req.case_id,
            created_by=operator_id or "copilot",
        )

        return draft
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Email draft creation failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=f"Email draft creation failed: {str(exc)}")


@router.post("/email/send/{draft_id}", response_model=Dict[str, Any])
async def send_email_by_id(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Send an email draft by ID path parameter."""
    try:
        result = await email_service.send_email(
            session=db,
            draft_id=draft_id,
            operator_id=operator_id or "copilot",
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Email send failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=f"Email send failed: {str(exc)}")


@router.post("/email/send", response_model=Dict[str, Any])
@router.post("/actions/email/send", response_model=Dict[str, Any])
async def send_email(
    req: EmailSendRequest,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Send an email draft after authorization."""
    try:
        result = await email_service.send_email(
            session=db,
            draft_id=req.draft_id,
            operator_id=operator_id or "copilot",
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Email send failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=f"Email send failed: {str(exc)}")


@router.get("/email/draft/{draft_id}", response_model=Dict[str, Any])
@router.get("/actions/email/draft/{draft_id}", response_model=Dict[str, Any])
async def get_email_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve an email draft by ID."""
    issue_repo = IssueRepository(db)
    draft = await issue_repo.get_email_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
    return draft


# --- Refund Endpoints ---

@router.get("/refund/investigate", response_model=Dict[str, Any])
@router.post("/refund/investigate", response_model=Dict[str, Any])
@router.get("/actions/refund/investigate", response_model=Dict[str, Any])
@router.post("/actions/refund/investigate", response_model=Dict[str, Any])
async def investigate_refund(
    case_id: Optional[str] = Query(None),
    payment_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Investigate refund status and eligibility for a payment."""
    if not case_id and not payment_id:
        raise HTTPException(status_code=400, detail="Provide either case_id or payment_id")
    try:
        result = await refund_service.investigate_refund(session=db, case_id=case_id, payment_id=payment_id)
        return result
    except Exception as exc:
        logger.error("Refund investigation failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/refund/prepare", response_model=Dict[str, Any])
@router.post("/actions/refund/prepare", response_model=Dict[str, Any])
async def prepare_refund(
    req: RefundRequest,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Prepare and simulate a refund execution."""
    try:
        result = await refund_service.prepare_refund(
            session=db,
            case_id=req.case_id,
            amount_inr=req.amount_inr,
            reason=req.reason,
            operator_id=operator_id or "copilot",
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Refund preparation failed: %s", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


# --- Issue Tracking Endpoints ---

@router.get("/issues", response_model=List[Dict[str, Any]])
async def list_issues(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    customer_email: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List customer issues with optional filters."""
    issue_repo = IssueRepository(db)
    issues = await issue_repo.list_issues(
        status=status,
        category=category,
        severity=severity,
        customer_email=customer_email,
        limit=limit,
        offset=offset,
    )
    return [issue.model_dump(mode="json") for issue in issues]


@router.post("/issues", response_model=Dict[str, Any])
async def create_issue(
    req: IssueCreateRequest,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Create a new customer issue."""
    from recovery_autopilot.domain.issue_models import CustomerIssue, IssueCategory, IssueSeverity
    issue_repo = IssueRepository(db)

    cat_map = {c.value: c for c in IssueCategory}
    sev_map = {s.value: s for s in IssueSeverity}

    category = cat_map.get(req.category.upper(), IssueCategory.PAYMENT_FAILURE)
    severity = sev_map.get(req.severity.upper() if req.severity else "MEDIUM", IssueSeverity.MEDIUM)

    issue = CustomerIssue(
        title=req.title,
        category=category,
        severity=severity,
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        payment_id=req.payment_id,
        order_id=req.order_id,
        reported_symptoms=req.reported_symptoms,
        case_id=req.case_id,
        owner=operator_id or "copilot",
    )
    await issue_repo.save_issue(issue)
    return issue.model_dump(mode="json")


@router.get("/issues/{issue_id}", response_model=Dict[str, Any])
async def get_issue(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get issue detail by ID."""
    issue_repo = IssueRepository(db)
    issue = await issue_repo.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    return issue.model_dump(mode="json")


@router.patch("/issues/{issue_id}", response_model=Dict[str, Any])
async def update_issue(
    issue_id: str,
    req: IssueUpdateRequest,
    db: AsyncSession = Depends(get_db),
    operator_id: Optional[str] = Header("copilot", alias="X-Operator-Id"),
):
    """Update an issue's status, severity, owner, or resolution."""
    issue_repo = IssueRepository(db)
    issue = await issue_repo.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")

    if req.status:
        try:
            new_status = IssueStatus(req.status)
            issue.transition_status(new_status, actor=operator_id or "copilot")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")

    if req.severity:
        issue.severity = req.severity
    if req.owner:
        issue.owner = req.owner
    if req.resolution_summary:
        issue.resolution_summary = req.resolution_summary
    if req.next_action:
        issue.next_action = req.next_action
    if req.resolution_verified is not None:
        issue.resolution_verified = req.resolution_verified
    if req.resolution_evidence:
        issue.resolution_evidence = req.resolution_evidence

    await issue_repo.save_issue(issue)
    return issue.model_dump(mode="json")


# --- Automation Endpoints ---

@router.get("/automation/status", response_model=Dict[str, Any])
async def get_automation_status(db: AsyncSession = Depends(get_db)):
    """Report which operational automations are available and their configuration state."""
    return await automation_service.get_automation_status(db)


@router.post("/automation/check/{check_id}", response_model=Dict[str, Any])
async def run_automation_check(check_id: str, db: AsyncSession = Depends(get_db)):
    """Run an operational check by ID (supports hyphenated and underscored names)."""
    norm_id = check_id.replace("-", "_")
    if norm_id == "payment_mismatch":
        return await automation_service.check_payment_mismatches(db)
    elif norm_id == "webhook_failures":
        return await automation_service.check_webhook_failures(db)
    elif norm_id == "issue_sla":
        return await automation_service.check_issue_sla(db)
    elif norm_id == "operational_summary":
        return await automation_service.generate_operational_summary(db)
    elif norm_id == "refund_aging":
        return await automation_service.check_refund_aging(db)
    elif norm_id == "payment_link_expiry":
        return await automation_service.check_payment_link_expiry(db)
    else:
        raise HTTPException(status_code=404, detail=f"Unknown automation check: {check_id}")


@router.post("/automation/check/payment-mismatch", response_model=Dict[str, Any])
async def run_payment_mismatch_check(db: AsyncSession = Depends(get_db)):
    """Run payment/order mismatch detection check."""
    return await automation_service.check_payment_mismatches(db)


@router.post("/automation/check/webhook-failures", response_model=Dict[str, Any])
async def run_webhook_failure_check(db: AsyncSession = Depends(get_db)):
    """Run webhook failure alert check."""
    return await automation_service.check_webhook_failures(db)


@router.post("/automation/check/issue-sla", response_model=Dict[str, Any])
async def run_issue_sla_check(db: AsyncSession = Depends(get_db)):
    """Run issue SLA monitoring check."""
    return await automation_service.check_issue_sla(db)


@router.post("/automation/check/operational-summary", response_model=Dict[str, Any])
async def run_operational_summary(db: AsyncSession = Depends(get_db)):
    """Generate operational summary report."""
    return await automation_service.generate_operational_summary(db)
