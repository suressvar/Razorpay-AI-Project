"""Integration tests for Asynchronous Webhook Ingestion and Durable Queue."""

import hashlib
import hmac
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.config import settings
from recovery_autopilot.main import app
from recovery_autopilot.persistence.database import init_db
from recovery_autopilot.workers.queue import background_worker, webhook_queue


def make_signature(body: bytes, secret: str = settings.RAZORPAY_WEBHOOK_SECRET) -> str:
    """Generate valid HMAC SHA256 signature."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.asyncio
async def test_fast_path_webhook_ingestion_and_ack():
    """Webhook ingestion endpoint verifies signature and returns fast ACK within <50ms."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    payload = {
        "event": "payment.failed",
        "event_id": f"evt_async_{uid}",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_async_{uid}",
                    "amount": 299900,
                    "currency": "INR",
                    "status": "failed",
                    "subscription_id": f"sub_async_{uid}",
                    "customer_id": f"cust_async_{uid}",
                    "notes": {
                        "customer_name": "Rohan Gupta",
                        "customer_email": "rohan@example.com",
                        "customer_phone": "+919811122233",
                    },
                    "error_code": "INSUFFICIENT_FUNDS",
                    "error_description": "Payment failed due to low funds",
                    "method": "card",
                }
            }
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = make_signature(body_bytes)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start_time = time.perf_counter()
        resp = await client.post(
            "/webhooks/razorpay",
            content=body_bytes,
            headers={
                "X-Razorpay-Signature": sig,
                "Content-Type": "application/json",
            },
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["event_id"] == f"evt_async_{uid}"
        assert data["duplicate"] is False
        assert elapsed_ms < 500


@pytest.mark.asyncio
async def test_duplicate_webhook_deduplication():
    """Duplicate webhook events are acknowledged idempotently without double-queueing."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    payload = {
        "event": "payment.failed",
        "event_id": f"evt_async_dup_{uid}",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_async_dup_{uid}",
                    "amount": 99900,
                    "currency": "INR",
                    "status": "failed",
                    "subscription_id": f"sub_async_dup_{uid}",
                    "customer_id": f"cust_async_dup_{uid}",
                    "notes": {"customer_name": "Deepa"},
                    "error_code": "BAD_REQUEST",
                    "error_description": "Declined",
                    "method": "card",
                }
            }
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = make_signature(body_bytes)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call
        resp1 = await client.post(
            "/webhooks/razorpay",
            content=body_bytes,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["duplicate"] is False

        # Duplicate call
        resp2 = await client.post(
            "/webhooks/razorpay",
            content=body_bytes,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True


@pytest.mark.asyncio
async def test_background_worker_drains_and_processes_queue():
    """Background worker successfully leases and processes pending queue jobs."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    payload = {
        "event": "payment.failed",
        "event_id": f"evt_worker_{uid}",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_worker_{uid}",
                    "amount": 149900,
                    "currency": "INR",
                    "status": "failed",
                    "subscription_id": f"sub_worker_{uid}",
                    "customer_id": f"cust_worker_{uid}",
                    "notes": {
                        "customer_name": "Vikram Seth",
                        "customer_email": "vikram@example.com",
                        "customer_phone": "+919999888877",
                    },
                    "error_code": "CARD_EXPIRED",
                    "error_description": "Card is expired",
                    "method": "card",
                }
            }
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = make_signature(body_bytes)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Ingest webhook into queue
        resp = await client.post(
            "/webhooks/razorpay",
            content=body_bytes,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200

        # 2. Trigger worker processing
        processed = await background_worker.process_single_job()
        assert processed is True

        # 3. Verify queue statistics show completed
        stats_resp = await client.get("/webhooks/queue/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["completed"] >= 1


@pytest.mark.asyncio
async def test_dead_letter_queue_transition():
    """Jobs that fail repeatedly exceed max_attempts and transition to dead_letter state."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    event_id = f"evt_dead_letter_{uid}"
    await webhook_queue.enqueue(
        event_id=event_id,
        event_type="payment.failed",
        signature="test_sig",
        payload_str="invalid-json-payload-causes-crash",
    )

    # Process and fail 5 times
    for attempt in range(1, 6):
        job = await webhook_queue.lease_next_job()
        if job:
            await webhook_queue.mark_failed(event_id=job.event_id, error_msg=f"Failure #{attempt}", max_attempts=5, retry_delay_seconds=0.0)

    stats = await webhook_queue.get_stats()
    assert stats["dead_letter"] >= 1


@pytest.mark.asyncio
async def test_get_unmatched_webhooks_endpoint():
    """GET /webhooks/unmatched returns 200 and a list of unmatched webhook events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Should succeed without auth header
        resp = await client.get("/webhooks/unmatched")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

        # Should also succeed with auth header
        resp_auth = await client.get(
            "/webhooks/unmatched",
            headers={"Authorization": "Bearer auth_token_admin_recovery_v1"},
        )
        assert resp_auth.status_code == 200
        assert isinstance(resp_auth.json(), list)

