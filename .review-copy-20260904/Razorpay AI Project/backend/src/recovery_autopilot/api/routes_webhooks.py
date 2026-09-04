"""Razorpay webhook ingress API endpoint."""

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from recovery_autopilot.integrations.razorpay.webhook_verifier import WebhookVerificationError
from recovery_autopilot.services.orchestrator import orchestrator

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger("recovery_autopilot.api.webhooks")


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
):
    """Ingest, verify, deduplicate, and process incoming Razorpay webhooks.

    Requirements:
    1. Preserves exact raw body bytes.
    2. Validates HMAC signature.
    3. Stores event idempotently.
    4. Returns quickly.
    5. Dispatches background recovery workflow.
    """
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    # Read raw body bytes
    raw_body = await request.body()

    try:
        result = await orchestrator.handle_webhook(raw_body, x_razorpay_signature)
        return JSONResponse(status_code=200, content=result)
    except WebhookVerificationError as exc:
        logger.warning("Webhook signature verification failed: %s", str(exc))
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as exc:
        logger.error("Error processing webhook: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal webhook processing error: {str(exc)}")
