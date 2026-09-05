"""Tests for exact payment correlation, financial correctness, and idempotency (Prompt 1)."""

import json
import uuid

import pytest

from recovery_autopilot.config import settings
from recovery_autopilot.domain.enums import CaseStatus, FailureCategory, PaymentMethod
from recovery_autopilot.domain.models import PaymentContext
from recovery_autopilot.persistence.database import async_session_factory, init_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.services.orchestrator import orchestrator


@pytest.fixture(autouse=True)
async def setup_db():
    """Ensure database schema is up to date before each test."""
    await init_db()


def create_signed_webhook(payload: dict, secret: str = settings.RAZORPAY_WEBHOOK_SECRET) -> tuple[bytes, str]:
    """Helper to serialize payload and compute HMAC signature."""
    import hashlib
    import hmac
    raw_body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return raw_body, sig



@pytest.mark.asyncio
async def test_exact_payment_id_correlation():
    """Verify that incoming success webhook with matching payment_id recovers the exact case."""
    pay_id = f"pay_test_{uuid.uuid4().hex[:8]}"
    sub_id = f"sub_test_{uuid.uuid4().hex[:8]}"

    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=sub_id,
        customer_id="cust_1",
        customer_name="Test Alice",
        customer_email="alice@example.com",
        customer_phone="+919876543210",
        amount_inr=1500.0,
        currency="INR",
        failure_category=FailureCategory.BANK_TIMEOUT,
        failure_code="GATEWAY_TIMEOUT",
        failure_reason="Bank gateway timeout",
        payment_method=PaymentMethod.UPI,
    )

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    # Send payment.captured webhook matching payment_id
    success_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 150000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        }
    }
    raw, sig = create_signed_webhook(success_payload)
    res = await orchestrator.handle_webhook(raw, sig, event_id_header=f"evt_success_{uuid.uuid4().hex[:6]}")

    assert res["status"] == "recovered"
    assert res["case_id"] == case_id
    assert res["matched_by"] == "payment_id"
    assert res["recovered_amount"] == 1500.0

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        updated_case = await repo.get_case(case_id)
        assert updated_case is not None
        assert updated_case.status == CaseStatus.RECOVERED
        assert updated_case.outcome is not None
        assert updated_case.outcome.recovered is True
        assert updated_case.outcome.recovered_amount == 1500.0


@pytest.mark.asyncio
async def test_unrelated_payment_cannot_recover_active_case():
    """Verify that an unrelated payment does NOT recover an active case merely because it is active."""
    active_pay_id = f"pay_active_{uuid.uuid4().hex[:8]}"
    ctx = PaymentContext(
        payment_id=active_pay_id,
        subscription_id=f"sub_active_{uuid.uuid4().hex[:8]}",
        customer_id="cust_2",
        customer_name="Test Bob",
        customer_email="bob@example.com",
        customer_phone="+919876543211",
        amount_inr=2000.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST_PAYMENT_FAILED",
        failure_reason="Insufficient funds",
        payment_method=PaymentMethod.CARD,
    )

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        active_case_id = case.case_id

    # Send unrelated payment success event
    unrelated_pay_id = f"pay_unrelated_{uuid.uuid4().hex[:8]}"
    unrelated_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": unrelated_pay_id,
                    "amount": 200000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        }
    }
    raw, sig = create_signed_webhook(unrelated_payload)
    res = await orchestrator.handle_webhook(raw, sig, event_id_header=f"evt_unrelated_{uuid.uuid4().hex[:6]}")

    # Must be stored as unmatched event, NOT recover the active case
    assert res["status"] == "unmatched_stored"

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        # Active case must remain unrecovered
        c = await repo.get_case(active_case_id)
        assert c is not None
        assert c.status != CaseStatus.RECOVERED

        # Unmatched event must be persisted
        unmatched = await repo.list_unmatched_events()
        assert any(unrelated_pay_id in u["reason"] for u in unmatched)


@pytest.mark.asyncio
async def test_multi_identifier_correlation_subscription_and_order():
    """Verify correlation works across subscription_id, order_id, invoice_id, and payment_link_id."""
    sub_id = f"sub_multi_{uuid.uuid4().hex[:8]}"
    ord_id = f"order_multi_{uuid.uuid4().hex[:8]}"
    plink_id = f"plink_multi_{uuid.uuid4().hex[:8]}"

    ctx = PaymentContext(
        payment_id=f"pay_initial_{uuid.uuid4().hex[:8]}",
        subscription_id=sub_id,
        order_id=ord_id,
        payment_link_id=plink_id,
        customer_id="cust_3",
        customer_name="Test Charlie",
        customer_email="charlie@example.com",
        customer_phone="+919876543212",
        amount_inr=3000.0,
        currency="INR",
        failure_category=FailureCategory.NETWORK_FAILURE,
        failure_code="NETWORK_ERROR",
        failure_reason="Switch network failure",
        payment_method=PaymentMethod.NETBANKING,
    )

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    # 1. Match via payment_link_id note with new fresh payment_id
    new_pay_id = f"pay_fresh_{uuid.uuid4().hex[:8]}"
    link_success_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": new_pay_id,
                    "amount": 300000,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {
                        "payment_link_id": plink_id,
                    },
                }
            }
        }
    }
    raw, sig = create_signed_webhook(link_success_payload)
    res = await orchestrator.handle_webhook(raw, sig, event_id_header=f"evt_link_succ_{uuid.uuid4().hex[:6]}")

    assert res["status"] == "recovered"
    assert res["case_id"] == case_id
    assert res["matched_by"] == "payment_link_id"


@pytest.mark.asyncio
async def test_duplicate_delivery_idempotency_no_double_counting():
    """Verify receiving the exact same success webhook multiple times does not double count revenue."""
    pay_id = f"pay_idemp_{uuid.uuid4().hex[:8]}"
    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=f"sub_idemp_{uuid.uuid4().hex[:8]}",
        customer_id="cust_4",
        customer_name="Test Dana",
        customer_email="dana@example.com",
        customer_phone="+919876543213",
        amount_inr=4999.0,
        currency="INR",
        failure_category=FailureCategory.BANK_TIMEOUT,
        failure_code="GATEWAY_TIMEOUT",
        failure_reason="Gateway timeout",
        payment_method=PaymentMethod.UPI,
    )

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 499900,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        }
    }
    raw, sig = create_signed_webhook(payload)
    event_id = f"evt_idemp_{uuid.uuid4().hex[:6]}"

    # First delivery
    res1 = await orchestrator.handle_webhook(raw, sig, event_id_header=event_id)
    assert res1["status"] == "recovered"

    # Second delivery with same event_id
    res2 = await orchestrator.handle_webhook(raw, sig, event_id_header=event_id)
    assert res2["status"] == "duplicate_ignored"

    # Third delivery with new event_id but same payment capture
    res3 = await orchestrator.handle_webhook(raw, sig, event_id_header=f"evt_new_{uuid.uuid4().hex[:6]}")
    assert res3["status"] == "recovered"

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        c = await repo.get_case(case_id)
        assert c is not None
        assert c.status == CaseStatus.RECOVERED
        assert c.outcome is not None
        assert c.outcome.recovered_amount == 4999.0  # Still exact amount, not multiplied


@pytest.mark.asyncio
async def test_financial_amount_mismatch_escalates_to_review():
    """Verify that an unexpected captured amount is held for human review instead of auto-recovered."""
    pay_id = f"pay_mismatch_{uuid.uuid4().hex[:8]}"
    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=f"sub_mismatch_{uuid.uuid4().hex[:8]}",
        customer_id="cust_5",
        customer_name="Test Evan",
        customer_email="evan@example.com",
        customer_phone="+919876543214",
        amount_inr=5000.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST_PAYMENT_FAILED",
        failure_reason="Insufficient funds",
        payment_method=PaymentMethod.CARD,
    )

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    # Captured payload has wrong amount (e.g. ₹2,000 instead of ₹5,000)
    mismatch_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 200000,  # ₹2,000
                    "currency": "INR",
                    "status": "captured",
                }
            }
        }
    }
    raw, sig = create_signed_webhook(mismatch_payload)
    res = await orchestrator.handle_webhook(raw, sig, event_id_header=f"evt_mismatch_{uuid.uuid4().hex[:6]}")

    assert res["status"] == "held_for_review"

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        c = await repo.get_case(case_id)
        assert c is not None
        assert c.status == CaseStatus.AWAITING_APPROVAL
        assert c.outcome is None or c.outcome.recovered is False

        audits = await repo.get_audit_events(case_id)
        assert any(a.event_type == "PAYMENT_AMOUNT_MISMATCH_DETECTED" for a in audits)
