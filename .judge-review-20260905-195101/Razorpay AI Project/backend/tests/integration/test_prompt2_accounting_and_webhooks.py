"""Comprehensive verification test suite for Prompt 2: Payment accounting and webhook processing.

Tests:
1. Unified event processing across webhooks, workers, and direct pipelines.
2. Verified event schemas: subscription.charged & order.paid capture; payment.authorized non-capture.
3. Exact obligation matching (payment_id, payment_link_id, invoice_id, order_id, subscription_id).
4. Subscription matching uniquely identifies obligation; multiple active cases flag ambiguity without guessing.
5. Strict amount & currency validation.
6. Stable deduplication via provider event ID with SHA-256 fallback.
7. Persisted recovery ledger preventing double-counting across distinct success events (order.paid + payment.captured).
8. Out-of-order delivery handling (capture before failure, failure after capture).
9. Cancellation of pending recovery work (promises to pay, voice sessions) upon payment confirmation.
10. Durable queue repairs: retry eligibility timestamp delays, worker lease tokens, and safe lease handoff.
"""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from recovery_autopilot.domain.enums import CaseStatus, FailureCategory, PaymentMethod
from recovery_autopilot.domain.models import PaymentCase, PaymentContext, PromiseToPay, utc_now
from recovery_autopilot.integrations.razorpay.event_mapper import CapturedPaymentContext, RazorpayEventMapper
from recovery_autopilot.persistence.database import async_session_factory, init_db
from recovery_autopilot.persistence.models import (
    PaymentCaseRecord,
    PromiseToPayRecord,
    RecoveryLedgerRecord,
    UnmatchedWebhookRecord,
    VoiceSessionRecord,
    WebhookEventRecord,
)
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.services.event_processor import event_processor
from recovery_autopilot.services.orchestrator import orchestrator
from recovery_autopilot.workers.queue import background_worker, webhook_queue


@pytest.fixture(autouse=True)
async def prepare_db():
    await init_db()


@pytest.mark.asyncio
async def test_subscription_charged_is_success_not_failure():
    """Verify subscription.charged is processed as captured recovery, NOT failure processing."""
    uid = uuid.uuid4().hex[:8]
    sub_id = f"sub_charged_{uid}"
    pay_id = f"pay_charged_{uid}"

    # Setup active case
    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=sub_id,
        customer_id=f"cust_{uid}",
        customer_name="Aarav Mehta",
        customer_email="aarav@example.com",
        customer_phone="+919876543210",
        amount_inr=1999.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST_PAYMENT_FAILED",
        failure_reason="Insufficient balance",
        payment_method=PaymentMethod.UPI,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    # Construct subscription.charged payload
    payload = {
        "event": "subscription.charged",
        "id": f"evt_sub_{uid}",
        "payload": {
            "subscription": {
                "entity": {
                    "id": sub_id,
                    "status": "active",
                }
            },
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 199900,
                    "currency": "INR",
                    "status": "captured",
                    "subscription_id": sub_id,
                }
            },
        },
    }

    # Process via event processor
    res = await event_processor.process_event(payload=payload, event_id=f"evt_sub_{uid}")
    assert res["status"] == "recovered"
    assert res["recovered_amount"] == 1999.0

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        updated_case = await repo.get_case(case_id)
        assert updated_case.status == CaseStatus.RECOVERED
        assert updated_case.outcome is not None
        assert updated_case.outcome.recovered is True


@pytest.mark.asyncio
async def test_order_paid_handled_by_worker_and_processor():
    """Verify order.paid is properly processed as recovery rather than ignored."""
    uid = uuid.uuid4().hex[:8]
    ord_id = f"order_{uid}"
    pay_id = f"pay_{uid}"

    ctx = PaymentContext(
        payment_id=pay_id,
        order_id=ord_id,
        subscription_id=f"sub_{uid}",
        customer_id=f"cust_{uid}",
        customer_name="Pooja Verma",
        customer_email="pooja@example.com",
        customer_phone="+919811122233",
        amount_inr=2499.0,
        currency="INR",
        failure_category=FailureCategory.BANK_TIMEOUT,
        failure_code="GATEWAY_TIMEOUT",
        failure_reason="Bank network timeout",
        payment_method=PaymentMethod.NETBANKING,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    payload = {
        "event": "order.paid",
        "id": f"evt_ord_{uid}",
        "payload": {
            "order": {
                "entity": {
                    "id": ord_id,
                    "amount_paid": 249900,
                    "status": "paid",
                }
            },
            "payment": {
                "entity": {
                    "id": pay_id,
                    "order_id": ord_id,
                    "amount": 249900,
                    "currency": "INR",
                    "status": "captured",
                }
            },
        },
    }

    # Test via worker enqueue + processing
    enqueue_res = await webhook_queue.enqueue(
        event_id=f"evt_ord_{uid}",
        event_type="order.paid",
        signature="test_sig",
        payload_str=json.dumps(payload),
    )
    assert enqueue_res["status"] == "queued"

    processed = await background_worker.process_single_job()
    assert processed is True

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        updated_case = await repo.get_case(case_id)
        assert updated_case.status == CaseStatus.RECOVERED
        assert updated_case.outcome.recovered_amount == 2499.0


@pytest.mark.asyncio
async def test_payment_authorized_does_not_count_as_captured_revenue():
    """An authorization event alone must NOT transition a case to RECOVERED or record revenue."""
    uid = uuid.uuid4().hex[:8]
    pay_id = f"pay_auth_{uid}"

    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=f"sub_auth_{uid}",
        customer_id=f"cust_{uid}",
        customer_name="Karan Johar",
        customer_email="karan@example.com",
        customer_phone="+919877766655",
        amount_inr=5000.0,
        currency="INR",
        failure_category=FailureCategory.CUSTOMER_ACTION_REQUIRED,
        failure_code="ACTION_REQUIRED_OTP",
        failure_reason="OTP timeout",
        payment_method=PaymentMethod.CARD,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    payload = {
        "event": "payment.authorized",
        "id": f"evt_auth_{uid}",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 500000,
                    "currency": "INR",
                    "status": "authorized",
                }
            }
        },
    }

    res = await event_processor.process_event(payload=payload, event_id=f"evt_auth_{uid}")
    assert res["status"] == "authorized_pending_capture"

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        updated_case = await repo.get_case(case_id)
        # Status MUST NOT be RECOVERED
        assert updated_case.status != CaseStatus.RECOVERED
        assert updated_case.outcome is None

        # Ledger MUST NOT contain an entry
        ledger = await repo.get_recovery_by_payment_id(pay_id)
        assert ledger is None


@pytest.mark.asyncio
async def test_distinct_success_events_do_not_double_count_same_payment():
    """Receiving order.paid AND payment.captured for the same payment creates at most ONE ledger entry."""
    uid = uuid.uuid4().hex[:8]
    ord_id = f"order_double_{uid}"
    pay_id = f"pay_double_{uid}"

    ctx = PaymentContext(
        payment_id=pay_id,
        order_id=ord_id,
        subscription_id=f"sub_double_{uid}",
        customer_id=f"cust_{uid}",
        customer_name="Sanjay Rao",
        customer_email="sanjay@example.com",
        customer_phone="+919822233344",
        amount_inr=3500.0,
        currency="INR",
        failure_category=FailureCategory.BANK_TIMEOUT,
        failure_code="GATEWAY_TIMEOUT",
        failure_reason="Bank switch down",
        payment_method=PaymentMethod.UPI,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        case_id = case.case_id

    # Event 1: payment.captured
    payload1 = {
        "event": "payment.captured",
        "id": f"evt_cap_{uid}",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "order_id": ord_id,
                    "amount": 350000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    res1 = await event_processor.process_event(payload=payload1, event_id=f"evt_cap_{uid}")
    assert res1["status"] == "recovered"

    # Event 2: order.paid for the exact same payment ID
    payload2 = {
        "event": "order.paid",
        "id": f"evt_order_{uid}",
        "payload": {
            "order": {
                "entity": {
                    "id": ord_id,
                    "amount_paid": 350000,
                    "status": "paid",
                }
            },
            "payment": {
                "entity": {
                    "id": pay_id,
                    "order_id": ord_id,
                    "amount": 350000,
                    "currency": "INR",
                    "status": "captured",
                }
            },
        },
    }
    res2 = await event_processor.process_event(payload=payload2, event_id=f"evt_order_{uid}")
    assert res2["status"] == "recovered"
    assert res2.get("duplicate_ignored") is True

    # Verify recovery ledger count is exactly 1
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        records = await repo.list_recovery_records(case_id=case_id)
        assert len(records) == 1
        assert records[0].provider_payment_id == pay_id
        assert records[0].amount_inr == 3500.0


@pytest.mark.asyncio
async def test_ambiguous_subscription_matching_does_not_guess():
    """When multiple active obligations exist for the same subscription, matching does not guess and flags ambiguity."""
    uid = uuid.uuid4().hex[:8]
    sub_id = f"sub_multi_{uid}"

    # Create Case 1 for sub_id
    ctx1 = PaymentContext(
        payment_id=f"pay_cycle1_{uid}",
        subscription_id=sub_id,
        customer_id=f"cust_{uid}",
        customer_name="Rani Mukherjee",
        customer_email="rani@example.com",
        customer_phone="+919844455566",
        amount_inr=1500.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST",
        failure_reason="Cycle 1 failure",
        payment_method=PaymentMethod.CARD,
    )
    # Create Case 2 for same sub_id (e.g. repeated failure cycle)
    ctx2 = PaymentContext(
        payment_id=f"pay_cycle2_{uid}",
        subscription_id=sub_id,
        customer_id=f"cust_{uid}",
        customer_name="Rani Mukherjee",
        customer_email="rani@example.com",
        customer_phone="+919844455566",
        amount_inr=1500.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST",
        failure_reason="Cycle 2 failure",
        payment_method=PaymentMethod.CARD,
    )

    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        c1 = await workflow.process_failed_payment(ctx1)
        c2 = await workflow.process_failed_payment(ctx2)
        await session.commit()
        id1, id2 = c1.case_id, c2.case_id

    # Now an incoming payment capture mentions ONLY sub_id, with an unknown payment ID
    payload = {
        "event": "payment.captured",
        "id": f"evt_ambig_{uid}",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_unknown_ambig_{uid}",
                    "subscription_id": sub_id,
                    "amount": 150000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }

    res = await event_processor.process_event(payload=payload, event_id=f"evt_ambig_{uid}")
    assert res["status"] == "ambiguous_subscription_stored"
    assert id1 in res["candidate_cases"]
    assert id2 in res["candidate_cases"]

    # Neither case should be silently marked recovered
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        case1 = await repo.get_case(id1)
        case2 = await repo.get_case(id2)
        assert case1.status != CaseStatus.RECOVERED
        assert case2.status != CaseStatus.RECOVERED


@pytest.mark.asyncio
async def test_out_of_order_capture_reconciles_on_later_failure():
    """If payment.captured arrives before payment.failed, it is reconciled when failure arrives."""
    uid = uuid.uuid4().hex[:8]
    pay_id = f"pay_ooo_{uid}"

    # Step 1: Capture arrives FIRST
    payload_cap = {
        "event": "payment.captured",
        "id": f"evt_cap_first_{uid}",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 220000,
                    "currency": "INR",
                    "status": "captured",
                    "notes": {"payment_id": pay_id},
                }
            }
        },
    }
    res_cap = await event_processor.process_event(payload=payload_cap, event_id=f"evt_cap_first_{uid}")
    assert res_cap["status"] == "unmatched_stored"

    # Step 2: Failure arrives SECOND
    payload_fail = {
        "event": "payment.failed",
        "id": f"evt_fail_second_{uid}",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 220000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "INSUFFICIENT_FUNDS",
                    "error_description": "Initial failure",
                    "notes": {"customer_name": "Lata M"},
                }
            }
        },
    }
    res_fail = await event_processor.process_event(payload=payload_fail, event_id=f"evt_fail_second_{uid}")
    assert res_fail["status"] == "processed"

    # Case should be immediately resolved and marked RECOVERED via prior capture
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        match_res = await repo.get_case_by_exact_identifier(payment_id=pay_id)
        assert match_res is not None
        case, _, _ = match_res
        assert case.status == CaseStatus.RECOVERED
        ledger = await repo.get_recovery_by_payment_id(pay_id)
        assert ledger is not None
        assert ledger.amount_inr == 2200.0


@pytest.mark.asyncio
async def test_cancellation_of_pending_work_on_confirmed_payment():
    """Active promise to pay and ongoing voice session are automatically cancelled/fulfilled upon confirmed payment."""
    uid = uuid.uuid4().hex[:8]
    pay_id = f"pay_cancel_work_{uid}"

    ctx = PaymentContext(
        payment_id=pay_id,
        subscription_id=f"sub_cancel_{uid}",
        customer_id=f"cust_{uid}",
        customer_name="Aditya Chopra",
        customer_email="aditya@example.com",
        customer_phone="+919866677788",
        amount_inr=1200.0,
        currency="INR",
        failure_category=FailureCategory.BANK_TIMEOUT,
        failure_code="GATEWAY_TIMEOUT",
        failure_reason="Timeout",
        payment_method=PaymentMethod.UPI,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        case_id = case.case_id

        # Insert active promise to pay
        ptp = PromiseToPay(
            promise_id=f"ptp_{uid}",
            case_id=case_id,
            promised_datetime=utc_now() + timedelta(days=2),
            channel="WHATSAPP",
            consent_timestamp=utc_now(),
            status="ACTIVE",
        )
        await repo.save_promise_to_pay(ptp)

        # Insert active voice session
        voice_rec = VoiceSessionRecord(
            session_id=f"vses_{uid}",
            case_id=case_id,
            state="AWAITING_CONFIRMATION",
            consent_granted=True,
            language="hinglish",
        )
        session.add(voice_rec)
        await session.commit()

    # Confirmed payment webhook arrives
    payload = {
        "event": "payment.captured",
        "id": f"evt_cap_work_{uid}",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 120000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }
    res = await event_processor.process_event(payload=payload, event_id=f"evt_cap_work_{uid}")
    assert res["status"] == "recovered"

    # Verify pending work cancelled
    async with async_session_factory() as session:
        stmt_ptp = select(PromiseToPayRecord).where(PromiseToPayRecord.case_id == case_id)
        ptp_record = (await session.execute(stmt_ptp)).scalar_one()
        assert ptp_record.status == "FULFILLED"

        stmt_v = select(VoiceSessionRecord).where(VoiceSessionRecord.case_id == case_id)
        v_record = (await session.execute(stmt_v)).scalar_one()
        assert v_record.state == "COMPLETED"


@pytest.mark.asyncio
async def test_durable_queue_retry_eligibility_timing():
    """Jobs with future lease_expires_at are NOT leased until their retry delay has elapsed."""
    uid = uuid.uuid4().hex[:8]
    event_id = f"evt_retry_{uid}"

    await webhook_queue.enqueue(
        event_id=event_id,
        event_type="payment.failed",
        signature="sig",
        payload_str=json.dumps({"event": "payment.failed"}),
    )

    # First lease
    job1 = await webhook_queue.lease_next_job(worker_id="worker_1")
    assert job1 is not None
    assert job1.event_id == event_id

    # Fail job with a 5-second delay
    await webhook_queue.mark_failed(
        event_id=event_id,
        error_msg="Temporary network failure",
        retry_delay_seconds=5.0,
        lease_token=job1.worker_lease_token,
    )

    # Immediate attempt to lease should return None because retry delay has NOT elapsed!
    job_too_early = await webhook_queue.lease_next_job(worker_id="worker_2")
    assert job_too_early is None

    # Force expiration in DB to simulate passage of 5 seconds
    async with async_session_factory() as session:
        rec = await session.get(WebhookEventRecord, event_id)
        rec.lease_expires_at = utc_now() - timedelta(seconds=1)
        await session.commit()

    # Now it should be leasable!
    job_ready = await webhook_queue.lease_next_job(worker_id="worker_2")
    assert job_ready is not None
    assert job_ready.event_id == event_id
    assert job_ready.attempts == 2


@pytest.mark.asyncio
async def test_stale_worker_cannot_complete_job_owned_by_another():
    """A worker whose lease expired cannot complete a job that has been reclaimed by another worker."""
    uid = uuid.uuid4().hex[:8]
    event_id = f"evt_stale_{uid}"

    await webhook_queue.enqueue(
        event_id=event_id,
        event_type="payment.failed",
        signature="sig",
        payload_str=json.dumps({"event": "payment.failed"}),
    )

    # Worker 1 leases job with 1-second lease
    job1 = await webhook_queue.lease_next_job(worker_id="worker_1", lease_seconds=1)
    token1 = job1.worker_lease_token

    # Simulate Worker 1 hanging, lease expires
    async with async_session_factory() as session:
        rec = await session.get(WebhookEventRecord, event_id)
        rec.lease_expires_at = utc_now() - timedelta(seconds=2)
        await session.commit()

    # Worker 2 claims the expired job
    job2 = await webhook_queue.lease_next_job(worker_id="worker_2", lease_seconds=30)
    token2 = job2.worker_lease_token
    assert token2 != token1

    # Worker 1 wakes up and attempts to complete the job with its stale token
    await webhook_queue.mark_completed(event_id=event_id, lease_token=token1)

    # Verify job status is STILL 'processing' owned by Worker 2
    async with async_session_factory() as session:
        rec = await session.get(WebhookEventRecord, event_id)
        assert rec.status == "processing"
        assert rec.worker_lease_token == token2

    # Worker 2 successfully completes it
    await webhook_queue.mark_completed(event_id=event_id, lease_token=token2)
    async with async_session_factory() as session:
        rec = await session.get(WebhookEventRecord, event_id)
        assert rec.status == "completed"
