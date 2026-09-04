"""API endpoints for live recovery metrics and benchmark results."""

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.evaluation.runner import run_evaluation
from recovery_autopilot.persistence.database import get_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository

router = APIRouter(prefix="/metrics", tags=["Metrics"])

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
EVAL_RESULTS_PATH = REPO_ROOT / "data" / "scenarios" / "evaluation_results.json"


@router.get("/summary", response_model=Dict[str, Any])
async def get_metrics_summary(db: AsyncSession = Depends(get_db)):
    """Fetch live operational recovery metrics and recent audit stream."""
    repo = SqlAlchemyRepository(db)
    summary = await repo.get_summary_metrics()
    recent_audits = await repo.list_recent_audit_events(limit=15)
    summary["recent_audits"] = [a.model_dump(mode="json") for a in recent_audits]
    return summary


@router.get("/evaluation", response_model=Dict[str, Any])
async def get_evaluation_metrics():
    """Retrieve 500-case simulation benchmark metrics against fixed-rule baseline."""
    if EVAL_RESULTS_PATH.exists():
        with open(EVAL_RESULTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # Compute on the fly if file not found
    report = run_evaluation(dataset_size=500, seed=42, output_path=EVAL_RESULTS_PATH)
    return report.model_dump(mode="json")
