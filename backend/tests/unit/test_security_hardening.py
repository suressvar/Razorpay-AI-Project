"""Unit and integration tests for Security Hardening, Server-Side Authentication, RBAC, and Kill Switch.

Tests:
1. Missing authentication returns 401 Unauthorized.
2. Spoofed role headers (e.g. sending X-Operator-Role: admin) cannot elevate permissions.
3. Server-side token authentication derives viewer, reviewer, and admin roles.
4. Approval bound to action_version: rejects stale, repeated, or version-mismatched approvals with 409 Conflict.
5. Emergency kill switch checked immediately before side effects.
6. PII redaction masks email and phone numbers in audit and metadata.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.config import settings
from recovery_autopilot.domain.enums import CaseStatus, FailureCategory, PaymentMethod, RecoveryAction
from recovery_autopilot.domain.models import ExecutionResult, PaymentCase, PaymentContext
from recovery_autopilot.integrations.notifications.simulator import UnifiedActionExecutor
from recovery_autopilot.integrations.razorpay.payment_links import redact_metadata
from recovery_autopilot.main import app
from recovery_autopilot.persistence.database import async_session_factory, init_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.services.orchestrator import orchestrator


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()
    settings.KILL_SWITCH_ACTIVE = False
    try:
        yield
    finally:
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
async def test_missing_authentication_rejected():
    """Requests without a valid Bearer token are rejected with 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Protected admin endpoint without auth header
        resp = await client.post("/admin/settings", json={"human_review_threshold_inr": 10000.0})
        assert resp.status_code == 401
        assert "Authentication required" in resp.json()["detail"]

        # Protected approval endpoint without auth header
        resp2 = await client.post("/cases/case_test_01/approve", json={"notes": "Approve"})
        assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_spoofed_role_header_cannot_grant_privileges():
    """Supplying X-Operator-Role: admin with viewer token or no token CANNOT grant admin access."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Spoofed role with NO token -> 401 Unauthorized
        resp1 = await client.post(
            "/admin/kill-switch",
            json={"active": True, "reason": "Spoofed attempt"},
            headers={"X-Operator-Role": "admin"},
        )
        assert resp1.status_code == 401

        # 2. Spoofed role with VIEWER token -> 403 Forbidden (server sees viewer identity, ignores header)
        resp2 = await client.post(
            "/admin/kill-switch",
            json={"active": True, "reason": "Spoofed attempt with viewer token"},
            headers={
                "Authorization": "Bearer auth_token_viewer_recovery_v1",
                "X-Operator-Role": "admin",
            },
        )
        assert resp2.status_code == 403
        assert "lacks required permissions" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_rbac_server_side_permission_hierarchy():
    """Ensure viewer cannot approve, reviewer can approve, admin can manage settings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Viewer token attempting approval -> 403 Forbidden
        resp_viewer = await client.post(
            "/cases/case_nonexistent_01/approve",
            json={"notes": "Approve attempt"},
            headers={"Authorization": "Bearer auth_token_viewer_recovery_v1"},
        )
        assert resp_viewer.status_code == 403

        # 2. Reviewer token allowed to access approval endpoint (reaches logic, 404 for nonexistent case)
        resp_reviewer = await client.post(
            "/cases/case_nonexistent_01/approve",
            json={"notes": "Approve attempt"},
            headers={"Authorization": "Bearer auth_token_reviewer_recovery_v1"},
        )
        assert resp_reviewer.status_code == 404

        # 3. Reviewer attempting admin endpoint -> 403 Forbidden
        resp_rev_admin = await client.post(
            "/admin/kill-switch",
            json={"active": True, "reason": "Reviewer attempt"},
            headers={"Authorization": "Bearer auth_token_reviewer_recovery_v1"},
        )
        assert resp_rev_admin.status_code == 403

        # 4. Admin token allowed to toggle kill switch
        resp_admin = await client.post(
            "/admin/kill-switch",
            json={"active": True, "reason": "Admin test"},
            headers={"Authorization": "Bearer auth_token_admin_recovery_v1"},
        )
        assert resp_admin.status_code == 200
        assert resp_admin.json()["kill_switch_active"] is True


@pytest.mark.asyncio
async def test_approval_binding_to_action_version_and_stale_rejection():
    """Approvals are bound to a specific action_version; stale/version-mismatched approvals are rejected with 409."""
    uid = uuid.uuid4().hex[:8]
    pay_id = f"pay_apprv_{uid}"

    # Setup case in AWAITING_APPROVAL
    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=f"sub_apprv_{uid}",
        customer_id=f"cust_{uid}",
        customer_name="Sunil Gavaskar",
        customer_email="sunil@example.com",
        customer_phone="+919811122299",
        amount_inr=25000.0,  # High value triggers human review
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST",
        failure_reason="High value failure",
        payment_method=PaymentMethod.CARD,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        case_id = case.case_id
        await session.commit()

    assert case.status == CaseStatus.AWAITING_APPROVAL
    assert case.action_version == 1

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Stale approval with wrong action_version (e.g. version 99) -> 409 Conflict
        resp_stale = await client.post(
            f"/cases/{case_id}/approve",
            json={"action_version": 99, "notes": "Outdated approval"},
            headers={"Authorization": "Bearer auth_token_reviewer_recovery_v1"},
        )
        assert resp_stale.status_code == 409
        assert "Stale approval rejected" in resp_stale.json()["detail"]

        # 2. Correct approval with matching action_version (version 1) -> 200 OK
        resp_ok = await client.post(
            f"/cases/{case_id}/approve",
            json={"action_version": 1, "notes": "Verified by reviewer"},
            headers={"Authorization": "Bearer auth_token_reviewer_recovery_v1"},
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["status"] == "approved"

        # 3. Repeated / replay approval on already-approved case -> 409 Conflict
        resp_replay = await client.post(
            f"/cases/{case_id}/approve",
            json={"action_version": 1, "notes": "Replay attempt"},
            headers={"Authorization": "Bearer auth_token_reviewer_recovery_v1"},
        )
        assert resp_replay.status_code == 409


@pytest.mark.asyncio
async def test_kill_switch_checked_immediately_before_side_effects():
    """When kill switch is active, all recovery side effects are immediately halted and audited."""
    settings.KILL_SWITCH_ACTIVE = True

    uid = uuid.uuid4().hex[:8]
    ctx = PaymentContext(
        payment_id=f"pay_ks_{uid}",
        subscription_id=f"sub_ks_{uid}",
        customer_id=f"cust_{uid}",
        customer_name="Test User",
        customer_email="test@example.com",
        customer_phone="+919876543210",
        amount_inr=999.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST",
        failure_reason="Test reason",
        payment_method=PaymentMethod.UPI,
    )
    case = PaymentCase(case_id=f"case_ks_{uid}", context=ctx)

    # 1. Check UnifiedActionExecutor respects kill switch
    executor = orchestrator.unified_executor
    res = await executor.execute_action(case, RecoveryAction.SEND_PAYMENT_LINK)
    assert res.status == "BLOCKED_BY_KILL_SWITCH"
    assert "Emergency Kill Switch is active" in (res.error or "")

    # 2. Check PaymentLinkAdapter respects kill switch
    adapter = orchestrator.payment_link_adapter
    res_link = await adapter.create_payment_link(case)
    assert res_link.status == "BLOCKED_BY_KILL_SWITCH"


@pytest.mark.asyncio
async def test_operator_login_logout_and_session_expiration():
    """Verify login issues valid session token, logout revokes it, and expired sessions are rejected."""
    import time
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Invalid credentials -> 401
        bad_login = await client.post("/auth/login", json={"username": "admin", "password": "wrong_password"})
        assert bad_login.status_code == 401

        # 2. Valid login -> returns new dynamic token
        good_login = await client.post("/auth/login", json={"username": "admin", "password": "admin_recovery_demo_2026"})
        assert good_login.status_code == 200
        data = good_login.json()
        token = data["access_token"]
        assert token.startswith("tok_")
        assert data["role"] == "admin"

        # 3. Access protected endpoint using newly issued token -> 200
        auth_headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/auth/me", headers=auth_headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["username"] == "admin"

        # 4. Logout -> token revoked
        logout_resp = await client.post("/auth/logout", headers=auth_headers)
        assert logout_resp.status_code == 200

        # 5. Subsequent access using revoked token -> 401 Unauthorized
        revoked_resp = await client.get("/auth/me", headers=auth_headers)
        assert revoked_resp.status_code == 401

        # 6. Expired session test
        expired_login = await client.post("/auth/login", json={"username": "viewer", "password": "viewer_recovery_demo_2026"})
        exp_token = expired_login.json()["access_token"]
        # Artificially expire the token in registry
        from recovery_autopilot.security.auth import TOKEN_REGISTRY
        if exp_token in TOKEN_REGISTRY:
            TOKEN_REGISTRY[exp_token].expires_at = time.time() - 10

        exp_resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {exp_token}"})
        assert exp_resp.status_code == 401
        assert "expired" in exp_resp.json()["detail"].lower()

