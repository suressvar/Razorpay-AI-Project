"""Unit and integration tests for Security Hardening, RBAC, and Emergency Kill Switch."""

import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.config import settings
from recovery_autopilot.integrations.razorpay.payment_links import redact_metadata
from recovery_autopilot.main import app
from recovery_autopilot.persistence.database import init_db


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()
    settings.KILL_SWITCH_ACTIVE = False


def test_pii_redaction_utility():
    """Verify that email and phone number identifiers are properly masked."""
    data = {
        "email": "siddharth.rao@example.com",
        "phone": "+919876543210",
        "amount": 4999.0,
    }
    redacted = redact_metadata(data)
    assert redacted["email"] == "sid***@example.com"
    assert redacted["phone"] == "+91****210"
    assert redacted["amount"] == 4999.0


@pytest.mark.asyncio
async def test_rbac_approval_access_control():
    """Ensure viewer role cannot approve cases, but reviewer and admin can."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Viewer attempt to approve -> 403 Forbidden
        resp = await client.post(
            "/cases/case_nonexistent_01/approve",
            json={"operator_id": "viewer_user"},
            headers={"X-Operator-Role": "viewer"},
        )
        assert resp.status_code == 403
        assert "lacks required permissions" in resp.json()["detail"]

        # 2. Reviewer role allowed past RBAC gate (will return 404 for nonexistent case, not 403)
        resp2 = await client.post(
            "/cases/case_nonexistent_01/approve",
            json={"operator_id": "reviewer_user"},
            headers={"X-Operator-Role": "reviewer"},
        )
        assert resp2.status_code == 404  # Reached application logic past RBAC check


@pytest.mark.asyncio
async def test_admin_emergency_kill_switch():
    """Admin can toggle emergency kill switch; non-admin cannot."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-admin attempt -> 403
        resp = await client.post(
            "/admin/kill-switch",
            json={"active": True, "reason": "Test non-admin block"},
            headers={"X-Operator-Role": "reviewer"},
        )
        assert resp.status_code == 403

        # Admin toggle -> 200
        resp_admin = await client.post(
            "/admin/kill-switch",
            json={"active": True, "reason": "Drill test emergency stop"},
            headers={"X-Operator-Role": "admin"},
        )
        assert resp_admin.status_code == 200
        assert resp_admin.json()["kill_switch_active"] is True
        assert settings.KILL_SWITCH_ACTIVE is True

        # Deactivate
        resp_deact = await client.post(
            "/admin/kill-switch",
            json={"active": False, "reason": "Restore normal operations"},
            headers={"X-Operator-Role": "admin"},
        )
        assert resp_deact.status_code == 200
        assert settings.KILL_SWITCH_ACTIVE is False
