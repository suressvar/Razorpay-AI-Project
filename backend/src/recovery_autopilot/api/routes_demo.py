"""Demo and evaluation sandbox endpoints (synthetic-mode only)."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from recovery_autopilot.config import settings
from recovery_autopilot.evaluation.runner import run_evaluation
from recovery_autopilot.services.orchestrator import orchestrator

router = APIRouter(prefix="/demo", tags=["Demo Simulation"])

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
EVAL_RESULTS_PATH = REPO_ROOT / "data" / "scenarios" / "evaluation_results.json"


class SeedRequest(BaseModel):
    count: int = 50
    seed: int = 42


class EvalRequest(BaseModel):
    size: int = 500
    seed: int = 42


class WebhookSimRequest(BaseModel):
    event_type: str = "payment.failed"
    category: str = "INSUFFICIENT_FUNDS"
    amount_inr: float = 3499.0
    customer_name: Optional[str] = "Synthetic Test User"


@router.post("/seed")
async def seed_demo_data(req: SeedRequest):
    """Seed the database with synthetic cases for live demonstration."""
    if not settings.SYNTHETIC_MODE:
        raise HTTPException(status_code=403, detail="Demo seeding disabled in non-synthetic environments")

    count = await orchestrator.seed_demo_data(count=req.count, seed=req.seed)
    return {"status": "success", "seeded_count": count, "seed": req.seed}


@router.post("/run-evaluation")
async def trigger_evaluation_run(req: EvalRequest):
    """Run 500-case simulation benchmark comparing Autopilot to Baseline."""
    if not settings.SYNTHETIC_MODE:
        raise HTTPException(status_code=403, detail="Evaluation runs disabled in non-synthetic environments")

    report = run_evaluation(dataset_size=req.size, seed=req.seed, output_path=EVAL_RESULTS_PATH)
    return report.model_dump(mode="json")


@router.post("/simulate-webhook")
async def simulate_webhook_event(req: WebhookSimRequest):
    """Simulate an incoming Razorpay webhook directly with HMAC signature."""
    if not settings.SYNTHETIC_MODE:
        raise HTTPException(status_code=403, detail="Webhook simulation disabled in non-synthetic environments")

    import time
    timestamp = int(time.time())
    event_id = f"evt_sim_{timestamp}"

    if req.event_type == "payment.captured":
        payload = {
            "entity": "event",
            "id": event_id,
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_sim_{timestamp}",
                        "amount": int(req.amount_inr * 100),
                        "status": "captured",
                        "currency": "INR",
                    }
                }
            },
        }
    else:
        payload = {
            "entity": "event",
            "id": event_id,
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_sim_{timestamp}",
                        "subscription_id": f"sub_sim_{timestamp}",
                        "amount": int(req.amount_inr * 100),
                        "currency": "INR",
                        "method": "card",
                        "error_code": "BAD_REQUEST_PAYMENT_FAILED" if req.category == "INSUFFICIENT_FUNDS" else "GATEWAY_TIMEOUT",
                        "error_description": f"Simulated failure: {req.category}",
                        "notes": {"customer_name": req.customer_name},
                        "email": "demo.user@synthetic-test.example.com",
                        "contact": "+919800099887",
                    }
                }
            },
        }

    raw_body = json.dumps(payload).encode("utf-8")
    signature = orchestrator.webhook_verifier.compute_signature(raw_body)
    res = await orchestrator.handle_webhook(raw_body, signature)
    return {"status": "simulated", "webhook_result": res}
