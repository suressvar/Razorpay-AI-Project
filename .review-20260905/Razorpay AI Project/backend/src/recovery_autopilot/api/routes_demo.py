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
    payment_id: Optional[str] = None
    subscription_id: Optional[str] = None
    order_id: Optional[str] = None
    invoice_id: Optional[str] = None
    payment_link_id: Optional[str] = None


import logging
from recovery_autopilot.config import get_settings

logger = logging.getLogger("recovery_autopilot.api.routes_demo")


@router.post("/seed")
async def seed_demo_data(req: SeedRequest):
    """Seed the database with synthetic cases for live demonstration."""
    cfg = get_settings()
    if not cfg.SYNTHETIC_MODE and cfg.PAYMENT_EXECUTION_MODE == "production":
        raise HTTPException(status_code=403, detail="Demo seeding disabled in live production environments")

    try:
        count = await orchestrator.seed_demo_data(count=req.count, seed=req.seed)
        return {"status": "success", "seeded_count": count, "seed": req.seed}
    except Exception as e:
        logger.exception("Demo seeding error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to seed demo data: {str(e)}")


@router.post("/clear")
@router.delete("/clear")
async def clear_all_demo_data():
    """Clear all records (payment cases, audit logs, webhooks, voice sessions) from the database."""
    cfg = get_settings()
    if not cfg.SYNTHETIC_MODE and cfg.PAYMENT_EXECUTION_MODE == "production":
        raise HTTPException(status_code=403, detail="Demo clearing disabled in live production environments")

    try:
        counts = await orchestrator.clear_all_data()
        return {"status": "success", "deleted": counts}
    except Exception as e:
        logger.exception("Demo data clearing error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear demo data: {str(e)}")


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

    pay_id = req.payment_id or f"pay_sim_{timestamp}"
    sub_id = req.subscription_id or f"sub_sim_{timestamp}"
    ord_id = req.order_id or f"order_sim_{timestamp}"
    inv_id = req.invoice_id or f"inv_sim_{timestamp}"

    if req.event_type in ("payment.captured", "order.paid"):
        payload = {
            "entity": "event",
            "id": event_id,
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "order_id": ord_id if req.order_id else None,
                        "invoice_id": inv_id if req.invoice_id else None,
                        "subscription_id": sub_id if req.subscription_id else None,
                        "payment_link_id": req.payment_link_id,
                        "amount": int(req.amount_inr * 100),
                        "status": "captured",
                        "currency": "INR",
                        "notes": {
                            "case_id": req.payment_id or "",
                            "payment_link_id": req.payment_link_id or "",
                        },
                    }
                }
            },
        }
    elif req.category == "CHECKOUT_ABANDONED":
        payload = {
            "entity": "event",
            "id": event_id,
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "order_id": ord_id,
                        "amount": int(req.amount_inr * 100),
                        "currency": "INR",
                        "method": "upi",
                        "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                        "error_description": "Customer dropped off at checkout / UPI intent timed out",
                        "notes": {"customer_name": req.customer_name, "cart_id": f"cart_{timestamp}"},
                        "email": "checkout.dropoff@example.com",
                        "contact": "+919876543210",
                    }
                }
            },
        }
    elif req.category == "OVERDUE_RECEIVABLE":
        payload = {
            "entity": "event",
            "id": event_id,
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "invoice_id": inv_id,
                        "amount": int(req.amount_inr * 100),
                        "currency": "INR",
                        "method": "netbanking",
                        "error_code": "GATEWAY_ERROR_ISSUER_DOWN",
                        "error_description": "B2B Netbanking overdue invoice settlement failed (HDFC)",
                        "notes": {"customer_name": req.customer_name, "invoice_ref": f"INV-{timestamp}"},
                        "email": "b2b.finance@enterprise-client.example.com",
                        "contact": "+919811122233",
                    }
                }
            },
        }
    else:
        error_code = "BAD_REQUEST_PAYMENT_FAILED" if req.category == "INSUFFICIENT_FUNDS" else (
            "EXPIRED_CARD" if req.category == "EXPIRED_CARD" else "GATEWAY_TIMEOUT"
        )
        payload = {
            "entity": "event",
            "id": event_id,
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": pay_id,
                        "subscription_id": sub_id,
                        "amount": int(req.amount_inr * 100),
                        "currency": "INR",
                        "method": "card" if req.category == "EXPIRED_CARD" else "upi",
                        "error_code": error_code,
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
    return {"status": "simulated", "event_id": event_id, "payment_id": pay_id, "webhook_result": res}

