"""
Integration tests for Prompt 7: End-to-End Voice Recovery Conversation.
Tests multi-turn lifecycle, interruption, confirmation binding, relative date resolution,
and policy routing (stop-contact, already-paid, human escalation).
"""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.domain.enums import FailureCategory, PaymentMethod
from recovery_autopilot.domain.models import PaymentCase, PaymentContext
from recovery_autopilot.main import app
from recovery_autopilot.persistence.database import async_session_factory
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.services.orchestrator import orchestrator


@pytest.fixture
async def sample_case_id():
    uid = uuid.uuid4().hex[:8]
    ctx = PaymentContext(
        payment_id=f"pay_v_{uid}",
        subscription_id=f"sub_v_{uid}",
        customer_id=f"cust_v_{uid}",
        customer_name="Ramesh Gupta",
        customer_email="ramesh@example.com",
        customer_phone="+919876543210",
        amount_inr=1499.0,
        currency="INR",
        failure_category=FailureCategory.INSUFFICIENT_FUNDS,
        failure_code="BAD_REQUEST",
        failure_reason="Insufficient balance for auto-debit",
        payment_method=PaymentMethod.UPI,
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyRepository(session)
        workflow = orchestrator.create_workflow(repo)
        case = await workflow.process_failed_payment(ctx)
        await session.commit()
        return case.case_id


@pytest.mark.asyncio
async def test_full_voice_conversation_to_payment_link_dispatch(sample_case_id):
    """Multi-turn conversation with consent, WhatsApp link request, confirmation, and execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Start voice session
        start_res = await client.post(
            "/voice/sessions/start",
            json={"case_id": sample_case_id, "language_hint": "hinglish"},
        )
        assert start_res.status_code == 200
        session_id = start_res.json()["session_id"]

        # 2. Grant consent
        consent_res = await client.post(
            f"/voice/sessions/{session_id}/consent",
            json={"consent_granted": True},
        )
        assert consent_res.status_code == 200
        assert consent_res.json()["has_consent"] is True

        # 3. Customer asks for WhatsApp link
        utt_res = await client.post(
            f"/voice/sessions/{session_id}/utterance",
            json={
                "text": "Haan mujhe WhatsApp pe payment link bhej do, main UPI se pay kar deta hoon",
                "language_hint": "hinglish",
                "transcription_confidence": 0.95,
            },
        )
        assert utt_res.status_code == 200
        assert utt_res.json()["session"]["state"] == "AWAITING_CONFIRMATION"

        # 4. Confirm proposed payment link
        conf_res = await client.post(
            f"/voice/sessions/{session_id}/confirm",
        )
        assert conf_res.status_code == 200
        assert conf_res.json()["result"]["status"] == "LINK_DISPATCHED"
        assert conf_res.json()["session"]["state"] == "CLOSURE"


@pytest.mark.asyncio
async def test_generic_yes_rejected_when_no_proposal_exists(sample_case_id):
    """Saying 'yes' without a valid proposal must prompt for clarification, not execute actions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Start voice session & grant consent
        start_res = await client.post(
            "/voice/sessions/start",
            json={"case_id": sample_case_id, "language_hint": "english"},
        )
        session_id = start_res.json()["session_id"]
        await client.post(f"/voice/sessions/{session_id}/consent", json={"consent_granted": True})

        # 2. Customer prematurely says "Yes" without any proposal on the table
        utt_res = await client.post(
            f"/voice/sessions/{session_id}/utterance",
            json={
                "text": "Yes",
                "language_hint": "english",
                "transcription_confidence": 0.95,
            },
        )
        assert utt_res.status_code == 200
        # Must be moved to clarification, NOT executing_action
        assert utt_res.json()["session"]["state"] == "CLARIFICATION"
        assert utt_res.json()["session"]["action_executed"] is None


@pytest.mark.asyncio
async def test_interrupt_and_text_correction(sample_case_id):
    """Customer can interrupt agent speech and apply text correction."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start_res = await client.post(
            "/voice/sessions/start",
            json={"case_id": sample_case_id, "language_hint": "english"},
        )
        session_id = start_res.json()["session_id"]
        await client.post(f"/voice/sessions/{session_id}/consent", json={"consent_granted": True})

        # 1. Trigger interrupt
        int_res = await client.post(f"/voice/sessions/{session_id}/interrupt")
        assert int_res.status_code == 200
        assert int_res.json()["status"] == "interrupted"

        # 2. Apply text correction
        corr_res = await client.post(
            f"/voice/sessions/{session_id}/correct-text",
            json={"corrected_text": "I want to pay 1499 tomorrow", "field_name": "promise_date"},
        )
        assert corr_res.status_code == 200
        assert corr_res.json()["status"] == "corrected"
        turns = corr_res.json()["session"]["turns"]
        assert any(t["text"] == "I want to pay 1499 tomorrow" for t in turns)


@pytest.mark.asyncio
async def test_stop_contact_and_human_escalation_routes(sample_case_id):
    """Policy triggers: DND stops contact, while already-paid claims escalate to human review."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test DND Opt-Out
        start_res = await client.post(
            "/voice/sessions/start",
            json={"case_id": sample_case_id, "language_hint": "hinglish"},
        )
        session_id = start_res.json()["session_id"]
        await client.post(f"/voice/sessions/{session_id}/consent", json={"consent_granted": True})

        dnd_res = await client.post(
            f"/voice/sessions/{session_id}/utterance",
            json={
                "text": "Mujhe phone mat karo aage se, stop calling me DND",
                "language_hint": "hinglish",
            },
        )
        assert dnd_res.status_code == 200
        assert dnd_res.json()["session"]["state"] == "TERMINATED"

        # Test Already Paid Escalation
        start2 = await client.post(
            "/voice/sessions/start",
            json={"case_id": sample_case_id, "language_hint": "hinglish"},
        )
        session_id2 = start2.json()["session_id"]
        await client.post(f"/voice/sessions/{session_id2}/consent", json={"consent_granted": True})

        paid_res = await client.post(
            f"/voice/sessions/{session_id2}/utterance",
            json={
                "text": "Mere bank se paise kat gaye hain already, check karo",
                "language_hint": "hinglish",
            },
        )
        assert paid_res.status_code == 200
        assert paid_res.json()["session"]["state"] == "ESCALATED_TO_HUMAN"

