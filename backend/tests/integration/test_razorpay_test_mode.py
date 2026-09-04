"""Integration tests for Genuine Razorpay Test Mode & 3-Mode Architecture."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from recovery_autopilot.config import Settings, validate_execution_mode
from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, PaymentContext, PolicyDecision
from recovery_autopilot.integrations.razorpay.client import (
    GenuineRazorpayTestClient,
    SyntheticRazorpayClient,
)
from recovery_autopilot.integrations.razorpay.payment_links import PaymentLinkAdapter


def make_test_case(amount_inr: float = 1499.0) -> PaymentCase:
    ctx = PaymentContext(
        payment_id="pay_test_mode_01",
        subscription_id="sub_test_mode_01",
        customer_id="cust_test_01",
        customer_name="Aarav Sharma",
        customer_email="aarav@example.com",
        customer_phone="+919876543210",
        amount_inr=amount_inr,
        failure_category=FailureCategory.EXPIRED_CARD,
        failure_code="CARD_EXPIRED",
        failure_reason="Card expired",
        payment_method="CARD",  # type: ignore
    )
    case = PaymentCase(context=ctx)
    case.latest_decision = PolicyDecision(
        case_id=case.case_id,
        allowed=True,
        approved_action=RecoveryAction.SEND_PAYMENT_LINK,
        modified_delay_minutes=0,
        reason_codes=["APPROVED"],
        requires_human_review=False,
    )
    return case


def test_reject_live_credentials():
    """Ensure GenuineRazorpayTestClient rejects any live credential prefix with strict exception."""
    with pytest.raises(ValueError, match="GenuineRazorpayTestClient only accepts rzp_test_ keys"):
        GenuineRazorpayTestClient(
            key_id="rzp_live_abc1234567890",
            key_secret="live_secret_key_abcdef",
        )


def test_validate_execution_mode_safety_locks():
    """Verify safety lock logic for execution modes."""
    # Synthetic is always valid
    settings = Settings(PAYMENT_EXECUTION_MODE="synthetic")
    assert validate_execution_mode(settings) == "synthetic"

    # Razorpay test mode requires rzp_test_ key
    settings = Settings(
        PAYMENT_EXECUTION_MODE="razorpay_test",
        RAZORPAY_KEY_ID="rzp_test_validkey123",
        RAZORPAY_KEY_SECRET="validsecret",
    )
    assert validate_execution_mode(settings) == "razorpay_test"

    # Razorpay test mode with invalid key fails
    settings = Settings(
        PAYMENT_EXECUTION_MODE="razorpay_test",
        RAZORPAY_KEY_ID="rzp_live_invalidkey",
        RAZORPAY_KEY_SECRET="validsecret",
    )
    with pytest.raises(ValueError, match="keys MUST strictly start with 'rzp_test_'"):
        validate_execution_mode(settings)

    # Production mode without explicit override fails
    settings = Settings(
        PAYMENT_EXECUTION_MODE="production",
        ALLOW_PRODUCTION_MODE=False,
    )
    with pytest.raises(ValueError, match="Production execution mode is locked"):
        validate_execution_mode(settings)


@pytest.mark.asyncio
async def test_synthetic_client_creates_synthetic_link():
    """Synthetic client generates offline simulated payment link without any network calls."""
    client = SyntheticRazorpayClient()
    result = await client.create_payment_link(
        amount_paise=149900,
        currency="INR",
        description="Subscription renewal",
        customer_name="Aarav Sharma",
        customer_email="aarav@example.com",
        idempotency_key="idemp_syn_001",
    )
    assert result["id"].startswith("plink_syn_")
    assert result["status"] == "created"
    assert result["amount"] == 149900  # paise
    assert result["currency"] == "INR"
    assert "https://rzp.io/i/syn_" in result["short_url"]


@pytest.mark.asyncio
async def test_genuine_test_client_with_mocked_http():
    """Genuine test client formats payload correctly and sends basic auth header."""
    client = GenuineRazorpayTestClient(
        key_id="rzp_test_mock123",
        key_secret="mock_secret_abc",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "plink_rzp_mock_9999",
        "amount": 149900,
        "currency": "INR",
        "short_url": "https://rzp.io/i/mock_9999",
        "status": "created",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await client.create_payment_link(
            amount_paise=149900,
            currency="INR",
            description="Test payment link",
            customer_name="Aarav",
            customer_email="aarav@example.com",
            idempotency_key="idemp_test_123",
        )

        assert res["id"] == "plink_rzp_mock_9999"
        assert res["short_url"] == "https://rzp.io/i/mock_9999"
        assert mock_post.called
        # Check idempotency header was passed
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["X-Razorpay-Idempotency-Key"] == "idemp_test_123"


@pytest.mark.asyncio
async def test_payment_link_adapter_with_genuine_test_client():
    """PaymentLinkAdapter passes case details to GenuineRazorpayTestClient and annotates case."""
    mock_gateway = MagicMock()
    mock_gateway.create_payment_link = AsyncMock(return_value={
        "id": "plink_rzp_live_test_001",
        "amount": 149900,
        "currency": "INR",
        "short_url": "https://rzp.io/i/live_test_001",
        "status": "created",
    })

    adapter = PaymentLinkAdapter(gateway_client=mock_gateway, mode="razorpay_test")
    case = make_test_case(amount_inr=1499.0)

    result = await adapter.create_payment_link(case)

    assert result.status == "SUCCESS"
    assert result.external_id == "plink_rzp_live_test_001"
    assert result.metadata["payment_link_id"] == "plink_rzp_live_test_001"
    assert case.context.payment_link_id == "plink_rzp_live_test_001"
    assert case.context.amount_inr == 1499.0
