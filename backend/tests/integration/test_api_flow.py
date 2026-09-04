"""Integration tests for FastAPI application, database persistence, and end-to-end API flow."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.main import app
from recovery_autopilot.persistence.database import init_db
from recovery_autopilot.services.orchestrator import orchestrator


@pytest.fixture(autouse=True)
async def setup_db():
    """Ensure database tables exist before running API tests."""
    await init_db()


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """GET /health returns healthy service status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "Recovery Autopilot"


@pytest.mark.asyncio
async def test_demo_seed_and_list_cases():
    """POST /demo/seed populates cases which are then retrievable via GET /cases."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Seed demo cases
        seed_resp = await client.post("/demo/seed", json={"count": 10, "seed": 42})
        assert seed_resp.status_code == 200
        assert seed_resp.json()["seeded_count"] == 10

        # 2. List cases
        list_resp = await client.get("/cases?limit=10")
        assert list_resp.status_code == 200
        cases = list_resp.json()
        assert len(cases) == 10

        first_case = cases[0]
        case_id = first_case["case_id"]

        # 3. Get single case
        case_resp = await client.get(f"/cases/{case_id}")
        assert case_resp.status_code == 200
        assert case_resp.json()["case_id"] == case_id

        # 4. Get audit trail
        audit_resp = await client.get(f"/cases/{case_id}/audit")
        assert audit_resp.status_code == 200
        audit_events = audit_resp.json()
        assert len(audit_events) > 0


@pytest.mark.asyncio
async def test_metrics_summary_endpoint():
    """GET /metrics/summary returns aggregated counts and recent audit events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cases" in data
        assert "total_inr_recovered" in data
        assert "recent_audits" in data


@pytest.mark.asyncio
async def test_metrics_evaluation_endpoint():
    """GET /metrics/evaluation returns benchmark metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/evaluation")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_total_inr_recovered" in data
        assert "incremental_recovery_rate_pct" in data


@pytest.mark.asyncio
async def test_webhook_endpoint_processing():
    """POST /webhooks/razorpay accepts signed payload and handles duplicates."""
    import uuid
    test_evt_id = f"evt_api_test_{uuid.uuid4().hex[:8]}"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "entity": "event",
            "id": test_evt_id,
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_api_test_001",
                        "subscription_id": "sub_api_test_001",
                        "amount": 499900,
                        "currency": "INR",
                        "error_code": "GATEWAY_TIMEOUT",
                        "error_description": "Bank timeout",
                        "method": "card",
                        "email": "api.test@synthetic-test.example.com",
                        "contact": "+919800055555",
                    }
                }
            },
        }
        raw_body = json.dumps(payload).encode("utf-8")
        sig = orchestrator.webhook_verifier.compute_signature(raw_body)

        # First delivery
        resp1 = await client.post(
            "/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] in ("queued", "accepted")
        assert resp1.json()["duplicate"] is False

        # Duplicate delivery
        resp2 = await client.post(
            "/webhooks/razorpay",
            content=raw_body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["duplicate"] is True
