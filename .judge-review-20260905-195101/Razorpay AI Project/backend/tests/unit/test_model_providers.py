"""Unit tests for Model Providers (all using mocks/fakes with zero quota consumption)."""

import pytest

from recovery_autopilot.config import Settings
from recovery_autopilot.domain.enums import FailureCategory, RecoveryAction
from recovery_autopilot.domain.models import PaymentCase, PaymentContext
from recovery_autopilot.model_providers.factory import get_model_provider
from recovery_autopilot.model_providers.fake import FakeModelProvider
from recovery_autopilot.model_providers.gemini import GeminiProvider
from recovery_autopilot.model_providers.ollama import OllamaProvider


def create_test_case(category: FailureCategory = FailureCategory.BANK_TIMEOUT, amount: float = 2999.0) -> PaymentCase:
    """Create a sample payment case for provider testing."""
    ctx = PaymentContext(
        payment_id="pay_unit_001",
        subscription_id="sub_unit_001",
        customer_id="cust_unit_001",
        customer_name="Test Customer",
        customer_email="test@synthetic-test.example.com",
        customer_phone="+919800011111",
        amount_inr=amount,
        failure_category=category,
        failure_code="GATEWAY_ERROR",
        failure_reason="Bank timed out",
        payment_method="CARD",  # type: ignore
        previous_failures=1,
        previous_contacts=0,
    )
    return PaymentCase(context=ctx)


@pytest.mark.asyncio
async def test_fake_provider_diagnosis_and_proposal():
    """FakeModelProvider generates expected domain proposals deterministically."""
    provider = FakeModelProvider()
    case = create_test_case(FailureCategory.BANK_TIMEOUT)

    diagnosis = await provider.diagnose_failure(case)
    assert diagnosis.failure_category == FailureCategory.BANK_TIMEOUT
    assert diagnosis.suggested_action == RecoveryAction.WAIT_FOR_RETRY
    assert diagnosis.is_transient is True

    proposal = await provider.propose_recovery(case)
    assert proposal.action == RecoveryAction.WAIT_FOR_RETRY
    assert proposal.confidence >= 0.80
    assert proposal.delay_minutes > 0


@pytest.mark.asyncio
async def test_fake_provider_expired_card():
    """Expired card must propose REQUEST_METHOD_UPDATE, never WAIT_FOR_RETRY."""
    provider = FakeModelProvider()
    case = create_test_case(FailureCategory.EXPIRED_CARD)

    proposal = await provider.propose_recovery(case)
    assert proposal.action == RecoveryAction.REQUEST_METHOD_UPDATE


@pytest.mark.asyncio
async def test_fake_provider_high_value_human_escalation():
    """Amounts >= 15,000 INR must propose HUMAN_REVIEW with requires_human_approval=True."""
    provider = FakeModelProvider()
    case = create_test_case(FailureCategory.INSUFFICIENT_FUNDS, amount=25000.0)

    proposal = await provider.propose_recovery(case)
    assert proposal.action == RecoveryAction.HUMAN_REVIEW
    assert proposal.requires_human_approval is True


@pytest.mark.asyncio
async def test_fake_provider_error_simulation():
    """Simulated provider timeout throws TimeoutError."""
    provider = FakeModelProvider(simulate_error="timeout")
    case = create_test_case()

    with pytest.raises(TimeoutError):
        await provider.diagnose_failure(case)


@pytest.mark.asyncio
async def test_gemini_fallback_on_error():
    """GeminiProvider safely falls back to HUMAN_REVIEW if network or client fails."""
    provider = GeminiProvider(api_key="mock_key", model_name="gemini-3.7-flash")
    case = create_test_case()

    # Model call will fail because no valid API server or key is present
    proposal = await provider.propose_recovery(case)
    assert proposal.action == RecoveryAction.HUMAN_REVIEW
    assert proposal.requires_human_approval is True
    assert "MODEL_PROVIDER_ERROR_FALLBACK" in proposal.reason_codes


@pytest.mark.asyncio
async def test_ollama_fallback_on_network_error():
    """OllamaProvider safely falls back to HUMAN_REVIEW when local server is offline."""
    provider = OllamaProvider(base_url="http://localhost:99999", timeout_seconds=0.5)
    case = create_test_case()

    proposal = await provider.propose_recovery(case)
    assert proposal.action == RecoveryAction.HUMAN_REVIEW
    assert proposal.requires_human_approval is True
    assert "OLLAMA_FALLBACK_TO_HUMAN" in proposal.reason_codes


def test_provider_factory():
    """Factory instantiates corresponding provider type based on settings."""
    settings_fake = Settings(MODEL_PROVIDER="fake")
    assert isinstance(get_model_provider(settings_fake), FakeModelProvider)

    settings_gemini = Settings(MODEL_PROVIDER="gemini", GEMINI_API_KEY="test")
    assert isinstance(get_model_provider(settings_gemini), GeminiProvider)

    settings_ollama = Settings(MODEL_PROVIDER="ollama")
    assert isinstance(get_model_provider(settings_ollama), OllamaProvider)
