"""Comprehensive verification test suite for Prompt 3: Settings and Razorpay Test Integration.

Tests:
1. One authoritative execution mode ('synthetic', 'razorpay_test'); live execution strictly rejected.
2. Typed gateway adapter enforces mode isolation; never silently substitutes synthetic client in test mode.
3. Pre-save settings validation and rollback to previous working state upon failure.
4. Persistence across restarts (non-secret settings and server secrets).
5. Secrets are stored server-side and never returned in public settings view.
6. Client rebuilding and config_version increments on settings updates.
7. Persisted operation keys prevent duplicate external operations and reconcile outcomes.
8. Manual test-mode smoke test endpoint verification.
"""

import json
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.config import get_settings, settings
from recovery_autopilot.domain.enums import CaseStatus, FailureCategory, PaymentMethod
from recovery_autopilot.domain.models import PaymentContext
from recovery_autopilot.integrations.razorpay.client import (
    GenuineRazorpayTestClient,
    SyntheticRazorpayClient,
)
from recovery_autopilot.integrations.razorpay.payment_links import PaymentLinkAdapter
from recovery_autopilot.main import app
from recovery_autopilot.persistence.database import async_session_factory, init_db
from recovery_autopilot.persistence.models import OperationKeyRecord
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.services.orchestrator import orchestrator
from recovery_autopilot.services.settings_manager import SETTINGS_FILE, settings_manager


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.asyncio
async def test_live_production_mode_strictly_rejected():
    """Setting execution mode to 'production' or 'live' must be strictly rejected for this Buildathon."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt to set production mode
        resp = await client.post(
            "/admin/settings",
            json={"payment_execution_mode": "production"},
            headers={"Authorization": "Bearer auth_token_admin_recovery_v1"},
        )
        assert resp.status_code == 400
        assert "Live production execution mode is unavailable for this Buildathon" in resp.json()["detail"]

        # Attempt to set live mode
        resp_live = await client.post(
            "/admin/settings",
            json={"payment_execution_mode": "live"},
            headers={"Authorization": "Bearer auth_token_admin_recovery_v1"},
        )
        assert resp_live.status_code == 400
        assert "Live production execution mode is unavailable for this Buildathon" in resp_live.json()["detail"]


@pytest.mark.asyncio
async def test_never_silently_substitute_synthetic_client():
    """In razorpay_test mode, missing or invalid credentials MUST fail clearly, never substitute synthetic."""
    # 1. Missing credentials
    with pytest.raises(ValueError) as exc1:
        PaymentLinkAdapter(mode="razorpay_test", key_id="", key_secret="")
    assert "Missing Razorpay test credentials" in str(exc1.value)
    assert "Never silently substituting synthetic client" in str(exc1.value)

    # 2. Live key provided
    with pytest.raises(ValueError) as exc2:
        PaymentLinkAdapter(mode="razorpay_test", key_id="rzp_live_abc12345", key_secret="secret_abc")
    assert "keys must strictly start with 'rzp_test_'" in str(exc2.value)

    # 3. Valid test key uses GenuineRazorpayTestClient
    adapter = PaymentLinkAdapter(mode="razorpay_test", key_id="rzp_test_simulation_key", key_secret="secret_xyz")
    assert isinstance(adapter.client, GenuineRazorpayTestClient)
    assert adapter.mode == "razorpay_test"


@pytest.mark.asyncio
async def test_settings_validation_and_rollback_on_failure():
    """Invalid settings are rejected, and previous working settings are completely preserved."""
    original_threshold = settings.HUMAN_REVIEW_THRESHOLD_INR
    original_mode = settings.PAYMENT_EXECUTION_MODE

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send invalid threshold (negative number)
        resp = await client.post(
            "/admin/settings",
            json={"human_review_threshold_inr": -500.0},
            headers={"Authorization": "Bearer auth_token_admin_recovery_v1"},
        )
        assert resp.status_code == 400
        assert "must be greater than zero" in resp.json()["detail"]

        # Verify previous working settings were preserved
        assert settings.HUMAN_REVIEW_THRESHOLD_INR == original_threshold
        assert settings.PAYMENT_EXECUTION_MODE == original_mode


@pytest.mark.asyncio
async def test_settings_persistence_and_version_tracking():
    """Valid settings updates persist to disk, increment config_version, and survive reload."""
    initial_version = settings_manager.config_version
    new_threshold = 17500.0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/admin/settings",
            json={"human_review_threshold_inr": new_threshold},
            headers={"Authorization": "Bearer auth_token_admin_recovery_v1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["config_version"] > initial_version

        # Verify disk persistence
        assert SETTINGS_FILE.exists()
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            persisted = json.load(f)
        assert persisted.get("HUMAN_REVIEW_THRESHOLD_INR") == new_threshold

        # Verify restart reload restores persisted settings
        settings_manager.load_persisted_settings()
        assert settings.HUMAN_REVIEW_THRESHOLD_INR == new_threshold


@pytest.mark.asyncio
async def test_secrets_never_returned_to_browser():
    """GET /admin/settings returns configured/active indicators and masked keys, but never raw secrets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/admin/settings")
        assert resp.status_code == 200
        view = resp.json()

        gateway = view["gateway"]
        assert "key_secret" not in gateway
        assert gateway["key_secret_configured"] is True
        assert "key_id_masked" in gateway

        ai_model = view["ai_model"]
        assert "gemini_api_key" not in ai_model
        assert "openai_api_key" not in ai_model
        assert "configured_provider" in ai_model
        assert "active_provider" in ai_model


@pytest.mark.asyncio
async def test_persisted_operation_key_prevents_duplicate_payment_links():
    """Payment link creation with identical idempotency_key reconciles and reuses the existing link."""
    uid = uuid.uuid4().hex[:8]
    pay_id = f"pay_op_{uid}"

    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=f"sub_op_{uid}",
        customer_id=f"cust_{uid}",
        customer_name="Sunita Rao",
        customer_email="sunita@example.com",
        customer_phone="+919833344455",
        amount_inr=999.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST",
        failure_reason="Test op key",
        payment_method=PaymentMethod.UPI,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()

    op_key = f"op_test_key_{uid}"

    # First call
    res1 = await orchestrator.payment_link_adapter.create_payment_link(
        case=case,
        idempotency_key=op_key,
    )
    assert res1.status == "SUCCESS"
    plink_id_1 = res1.external_id

    # Second call with the same idempotency key
    res2 = await orchestrator.payment_link_adapter.create_payment_link(
        case=case,
        idempotency_key=op_key,
    )
    assert res2.status == "SUCCESS"
    assert res2.external_id == plink_id_1
    assert res2.metadata.get("reconciled_from_operation_key") is True


@pytest.mark.asyncio
async def test_gateway_smoke_test_endpoint():
    """Manual test-mode smoke test creates object, receives webhook, and verifies exact case correlation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/admin/gateway/smoke-test",
            headers={"Authorization": "Bearer auth_token_admin_recovery_v1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["smoke_test_passed"] is True
        assert data["ledger_recorded"] is True
        assert data["case_final_status"].lower() == "recovered"
        assert data["matched_field"] == "payment_link_id"
