import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.integrations.razorpay.webhook_verifier import WebhookVerificationError
from recovery_autopilot.persistence.database import get_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.services.orchestrator import orchestrator
from recovery_autopilot.workers.queue import background_worker, webhook_queue

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger("recovery_autopilot.api.webhooks")


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: Optional[str] = Header(None, alias="X-Razorpay-Event-Id"),
    async_mode: bool = True,
):
    """Ingest, verify, and enqueue incoming Razorpay webhooks within <50ms.

    Fast-path guarantees:
    1. Signature verification before acceptance.
    2. Atomic idempotent database enqueue.
    3. Immediate 200 ACK with queue job ID.
    4. Async processing via background worker.
    """
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    # Read raw body bytes
    raw_body = await request.body()

    try:
        # Verify HMAC signature
        orchestrator.webhook_verifier.verify(raw_body, x_razorpay_signature)
    except WebhookVerificationError as exc:
        logger.warning("Webhook signature verification failed: %s", str(exc))
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload_str = raw_body.decode("utf-8")
        payload = json.loads(payload_str)
        event_type = payload.get("event", "unknown")
        event_id = (
            x_razorpay_event_id
            or payload.get("event_id")
            or payload.get("id")
            or f"evt_wh_{uuid.uuid4().hex[:12]}"
        )

        enqueue_result = await webhook_queue.enqueue(
            event_id=event_id,
            event_type=event_type,
            signature=x_razorpay_signature,
            payload_str=payload_str,
        )

        # If synchronous processing was requested (e.g., in unit tests) or background worker not started
        if not async_mode:
            await background_worker.process_single_job()

        return JSONResponse(
            status_code=200,
            content={
                "status": enqueue_result["status"],
                "event_id": event_id,
                "event_type": event_type,
                "duplicate": enqueue_result["duplicate"],
                "message": enqueue_result["message"],
            },
        )

    except Exception as exc:
        logger.error("Error ingesting webhook: %s", str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal webhook ingestion error: {str(exc)}")


from recovery_autopilot.security.rbac import require_reviewer


@router.get("/queue/stats", response_model=Dict[str, Any])
async def get_queue_statistics():
    """Retrieve queue depth, active leases, completed, unmatched, and dead-letter metrics."""
    return await webhook_queue.get_stats()


@router.post("/process-pending")
async def process_pending_webhooks(operator_id: str = Depends(require_reviewer)):
    """Manually drain pending queued webhooks (requires reviewer or admin role)."""
    count = 0
    while await background_worker.process_single_job():
        count += 1
        if count >= 100:
            break
    return {"processed": count, "stats": await webhook_queue.get_stats(), "authorized_by": operator_id}


@router.get("/unmatched", response_model=List[Dict[str, Any]])
async def list_unmatched_webhooks(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List uncorrelatable webhook events stored for operator investigation."""
    repo = SqlAlchemyRepository(db)
    return await repo.list_unmatched_events(limit=limit, offset=offset)


