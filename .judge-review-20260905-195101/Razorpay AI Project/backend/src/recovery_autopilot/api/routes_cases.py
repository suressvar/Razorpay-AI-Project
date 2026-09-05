"""API endpoints for managing payment recovery cases and human review."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.persistence.database import get_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.security.rbac import require_reviewer
from recovery_autopilot.services.orchestrator import orchestrator

router = APIRouter(prefix="/cases", tags=["Cases"])


class ApproveRequest(BaseModel):
    operator_id: Optional[str] = None
    notes: Optional[str] = None
    action_version: Optional[int] = None


class RejectRequest(BaseModel):
    operator_id: Optional[str] = None
    reason: str
    action_version: Optional[int] = None


@router.get("", response_model=List[Dict[str, Any]])
async def list_cases(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List recovery cases with optional filtering."""
    repo = SqlAlchemyRepository(db)
    cases = await repo.list_cases(status=status, category=category, limit=limit, offset=offset)
    return [c.model_dump(mode="json") for c in cases]


@router.get("/{case_id}", response_model=Dict[str, Any])
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch details of a single recovery case."""
    repo = SqlAlchemyRepository(db)
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case.model_dump(mode="json")


@router.get("/{case_id}/audit", response_model=List[Dict[str, Any]])
async def get_case_audit_trail(case_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve complete chronological audit trail for a case."""
    repo = SqlAlchemyRepository(db)
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    events = await repo.get_audit_events(case_id)
    return [e.model_dump(mode="json") for e in events]


@router.get("/{case_id}/notifications", response_model=List[Dict[str, Any]])
async def get_case_notifications(case_id: str):
    """Retrieve simulated customer notifications for UI preview."""
    notifs = orchestrator.unified_executor.get_notifications_for_case(case_id)
    return [n.model_dump(mode="json") for n in notifs]


@router.post("/{case_id}/approve")
async def approve_case(
    case_id: str,
    req: ApproveRequest = ApproveRequest(),
    operator_id: str = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    """Approve a case held for human operator review (requires reviewer or admin role)."""
    repo = SqlAlchemyRepository(db)
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    workflow = orchestrator.create_workflow(repo)
    try:
        await workflow.handle_human_approval(
            case,
            operator_id=operator_id,
            notes=req.notes if req else None,
            action_version=req.action_version if req else None,
        )
        await db.commit()
        return {
            "status": "approved",
            "case_id": case_id,
            "new_status": case.status.value,
            "action_version": case.action_version,
            "approved_by": operator_id,
        }
    except ValueError as exc:
        if "Stale approval" in str(exc) or "not AWAITING_APPROVAL" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Approval execution error: {str(exc)}")


@router.post("/{case_id}/reject")
async def reject_case(
    case_id: str,
    req: RejectRequest,
    operator_id: str = Depends(require_reviewer),
    db: AsyncSession = Depends(get_db),
):
    """Reject a case held for human operator review and stop recovery (requires reviewer or admin role)."""
    repo = SqlAlchemyRepository(db)
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    workflow = orchestrator.create_workflow(repo)
    try:
        await workflow.handle_human_rejection(
            case,
            operator_id=operator_id,
            reason=req.reason,
            action_version=req.action_version,
        )
        await db.commit()
        return {
            "status": "rejected",
            "case_id": case_id,
            "new_status": case.status.value,
            "action_version": case.action_version,
            "rejected_by": operator_id,
        }
    except ValueError as exc:
        if "Stale rejection" in str(exc) or "not AWAITING_APPROVAL" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Rejection execution error: {str(exc)}")


@router.post("/{case_id}/retry")
async def retry_case(case_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger an immediate retry execution for a case."""
    repo = SqlAlchemyRepository(db)
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    workflow = orchestrator.create_workflow(repo)
    try:
        await workflow.handle_human_approval(case, operator_id="manual_retry_trigger")
        await db.commit()
        return {"status": "retried", "case_id": case_id, "new_status": case.status.value}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


