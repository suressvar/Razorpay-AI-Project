"""
Integration tests for Voice Session Orchestrator and API lifecycle.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.domain.enums import CaseStatus, CustomerSegment, FailureCategory, PaymentMethod
from recovery_autopilot.domain.models import PaymentCase, PaymentContext
from recovery_autopilot.main import app
from recovery_autopilot.persistence.database import async_session_factory, init_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository


@pytest.fixture
async def sample_case():
    await init_db()
    async with async_session_factory() as session:


        repo = SqlAlchemyRepository(session)
        ctx = PaymentContext(
            payment_id="pay_voice_demo_01",
            subscription_id="sub_voice_01",
            customer_id="cust_voice_01",
            customer_name="Rohan Sharma",
            customer_email="rohan@example.com",
            customer_phone="+919876543210",
            amount_inr=1499.0,
            currency="INR",
            failure_category=FailureCategory.INSUFFICIENT_FUNDS,
            failure_code="BAD_REQUEST_INSUFFICIENT_FUNDS",
            failure_reason="Card declined due to insufficient balance",
            payment_method=PaymentMethod.CARD,
            customer_segment=CustomerSegment.SMB,
        )
        case = PaymentCase(
            case_id="case_voice_demo_01",
            context=ctx,
            status=CaseStatus.NEW,
        )
        await repo.save_case(case)
        await session.commit()
        return case


@pytest.mark.asyncio
async def test_full_voice_session_lifecycle(sample_case):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Start Session
        start_res = await ac.post("/voice/sessions/start", json={"case_id": sample_case.case_id})
        assert start_res.status_code == 200
        session_data = start_res.json()
        session_id = session_data["session_id"]
        assert session_data["state"] == "AWAITING_CONSENT"
        assert len(session_data["turns"]) == 1

        # 2. Grant Consent
        consent_res = await ac.post(f"/voice/sessions/{session_id}/consent", json={"consent_granted": True})
        assert consent_res.status_code == 200
        assert consent_res.json()["state"] == "AWAITING_INTENT"

        # 3. Customer Utterance: Promise to Pay
        utt_res = await ac.post(
            f"/voice/sessions/{session_id}/utterance",
            json={"text": "Mera salary kal aayega, main kal shaam ko pakka pay kar dunga"},
        )
        assert utt_res.status_code == 200
        utt_data = utt_res.json()
        assert utt_data["session"]["state"] == "AWAITING_CONFIRMATION"
        assert utt_data["session"]["promise_draft"] is not None

        # 4. Confirm Promise
        conf_res = await ac.post(f"/voice/sessions/{session_id}/confirm")
        assert conf_res.status_code == 200
        conf_data = conf_res.json()
        assert conf_data["session"]["state"] == "CLOSURE"
        assert conf_data["result"]["status"] == "PROMISED_TO_PAY"

        # 5. Delete transcript privacy check
        del_res = await ac.delete(f"/voice/sessions/{session_id}/transcript")
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True
