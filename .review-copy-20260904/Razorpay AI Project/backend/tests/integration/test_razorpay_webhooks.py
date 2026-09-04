"""Integration tests for Razorpay webhook verification and payload mapping."""

import json
from pathlib import Path

import pytest

from recovery_autopilot.domain.enums import FailureCategory
from recovery_autopilot.integrations.razorpay.event_mapper import RazorpayEventMapper
from recovery_autopilot.integrations.razorpay.webhook_verifier import (
    RazorpayWebhookVerifier,
    WebhookVerificationError,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "razorpay_events"
TEST_SECRET = "rzp_whsec_test_secret_12345"


def test_signature_verification_success():
    """Valid HMAC SHA256 signature calculated on exact bytes must pass verification."""
    verifier = RazorpayWebhookVerifier(TEST_SECRET)
    raw_body = b'{"event":"payment.failed","payload":{}}'
    sig = verifier.compute_signature(raw_body)

    assert verifier.verify(raw_body, sig) is True


def test_signature_verification_failure_tampered_body():
    """Tampering with body bytes must fail verification."""
    verifier = RazorpayWebhookVerifier(TEST_SECRET)
    raw_body = b'{"event":"payment.failed","amount":100}'
    sig = verifier.compute_signature(raw_body)

    tampered_body = b'{"event":"payment.failed","amount":999}'
    with pytest.raises(WebhookVerificationError):
        verifier.verify(tampered_body, sig)


def test_signature_verification_missing_signature():
    """Empty or missing signature must raise WebhookVerificationError."""
    verifier = RazorpayWebhookVerifier(TEST_SECRET)
    with pytest.raises(WebhookVerificationError):
        verifier.verify(b'{"test":1}', "")


def test_map_payment_failed_fixture():
    """Map payment_failed.json fixture into domain PaymentContext."""
    with open(FIXTURES_DIR / "payment_failed.json", "r") as f:
        payload = json.load(f)

    ctx = RazorpayEventMapper.map_payment_failed(payload)
    assert ctx.payment_id == "pay_failed_test_01"
    assert ctx.subscription_id == "sub_test_01"
    assert ctx.amount_inr == 2999.00  # 299900 paise
    assert ctx.failure_category == FailureCategory.BANK_TIMEOUT
    assert ctx.failure_code == "GATEWAY_TIMEOUT"
    assert ctx.bank_name == "HDFC"
    assert ctx.bank_degraded is True


def test_map_payment_captured_fixture():
    """Extract payment recovery data from payment_captured.json."""
    with open(FIXTURES_DIR / "payment_captured.json", "r") as f:
        payload = json.load(f)

    pay_id, amount_inr = RazorpayEventMapper.map_payment_captured(payload)
    assert pay_id == "pay_captured_test_01"
    assert amount_inr == 2999.00


def test_map_order_paid_fixture():
    """Extract payment recovery data from order_paid.json."""
    with open(FIXTURES_DIR / "order_paid.json", "r") as f:
        payload = json.load(f)

    pay_id, amount_inr = RazorpayEventMapper.map_payment_captured(payload)
    assert pay_id == "pay_order_paid_01"
    assert amount_inr == 2999.00
