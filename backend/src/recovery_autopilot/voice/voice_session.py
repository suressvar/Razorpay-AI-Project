"""
Voice Session Orchestrator and Lifecycle Manager.
Manages multi-turn conversation state, consent gating, policy enforcement,
and Promise-to-Pay registration.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from recovery_autopilot.domain.enums import CaseStatus
from recovery_autopilot.domain.models import PaymentCase, PromiseToPay, utc_now
from recovery_autopilot.persistence.models import VoiceSessionRecord
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.voice.voice_agent import VoiceRecoveryAgent
from recovery_autopilot.voice.voice_guardrails import VoiceGuardrails
from recovery_autopilot.voice.voice_models import (
    LanguageDetected,
    PromiseToPayDraft,
    VoiceAgentAnalysis,
    VoiceIntent,
    VoiceScenarioPreset,
    VoiceSessionState,
    VoiceTurn,
    VoiceTurnRole,
)

logger = logging.getLogger(__name__)


# 8 Interactive Demo Scenario Presets for judges
VOICE_SCENARIOS: List[VoiceScenarioPreset] = [
    VoiceScenarioPreset(
        scenario_id="scenario_hinglish_link",
        title="1. Hinglish WhatsApp Link Request",
        description="Customer wants payment link sent to their WhatsApp to pay via UPI",
        customer_persona="Tech-savvy subscriber",
        sample_utterances=[
            "Haan mujhe WhatsApp pe payment link bhej do, main UPI se pay kar deta hoon",
            "Bhejo link, abhi kar deta hoon pay",
        ],
        expected_intent=VoiceIntent.SEND_PAYMENT_LINK,
        expected_outcome="Generates instant Razorpay link & requests confirmation",
    ),
    VoiceScenarioPreset(
        scenario_id="scenario_promise_tomorrow",
        title="2. Promise to Pay (Kal Shaam / Tomorrow)",
        description="Customer promises to pay after salary/funds are deposited tomorrow evening",
        customer_persona="Salaried subscriber awaiting paycheck",
        sample_utterances=[
            "Mera salary kal aayega, main kal shaam ko pakka pay kar dunga",
            "Kal 5 baje tak ho jayega pay",
        ],
        expected_intent=VoiceIntent.PROMISE_TO_PAY,
        expected_outcome="Registers structured Promise-to-Pay & schedules pause",
    ),
    VoiceScenarioPreset(
        scenario_id="scenario_already_paid",
        title="3. Already Paid / Bank Deduction Claim",
        description="Customer claims amount was already deducted from their account",
        customer_persona="Concerned subscriber with bank SMS",
        sample_utterances=[
            "Mere bank se paise kat gaye hain already, dubara charge mat karo",
            "Paise cut gaye account se, check karo",
        ],
        expected_intent=VoiceIntent.ALREADY_PAID,
        expected_outcome="Pauses recovery, routes to bank reconciliation & human escalation",
    ),
    VoiceScenarioPreset(
        scenario_id="scenario_anti_otp",
        title="4. Anti-OTP / Security Defense",
        description="Simulates safety response when customer or fraudster attempts OTP sharing",
        customer_persona="User offering OTP",
        sample_utterances=[
            "Mera OTP 492810 hai, le lo aur payment complete kar lo",
            "PIN bataun kya payment karne ke liye?",
        ],
        expected_intent=VoiceIntent.UNCLEAR,
        expected_outcome="Deterministic OTP block with zero-credential warning",
    ),
    VoiceScenarioPreset(
        scenario_id="scenario_human_escalation",
        title="5. Request Human Executive",
        description="Customer asks to speak with a human agent or manager",
        customer_persona="User wanting human touch",
        sample_utterances=[
            "Mujhe kisi human agent se baat karni hai, manager se connect karo",
            "Kisi insaan se baat karao",
        ],
        expected_intent=VoiceIntent.REQUEST_HUMAN,
        expected_outcome="Transfers session gracefully to Human Escalation queue",
    ),
    VoiceScenarioPreset(
        scenario_id="scenario_stop_contact",
        title="6. DND / Stop Calling Opt-Out",
        description="Customer asks not to be contacted anymore",
        customer_persona="User requesting DND",
        sample_utterances=[
            "Mujhe call mat karo, remove my number from your list",
            "Stop calling, DND me daal do",
        ],
        expected_intent=VoiceIntent.STOP_CONTACT,
        expected_outcome="Immediate termination & persistent DND suppression",
    ),
    VoiceScenarioPreset(
        scenario_id="scenario_pure_hindi",
        title="7. Pure Hindi Conversational Flow",
        description="Customer conversing purely in standard Hindi",
        customer_persona="Hindi speaker",
        sample_utterances=[
            "कृपया मुझे भुगतान करने के लिए लिंक भेजें",
            "मैं कल सुबह तक पैसे जमा कर दूंगा",
        ],
        expected_intent=VoiceIntent.SEND_PAYMENT_LINK,
        expected_outcome="Responds fluently in respectful polite Hindi",
    ),
    VoiceScenarioPreset(
        scenario_id="scenario_dispute_unauthorized",
        title="8. Subscription Dispute / Cancellation",
        description="Customer disputes subscription renewal",
        customer_persona="Disputing customer",
        sample_utterances=[
            "Maine ye subscription cancel kiya tha, fraud mat karo",
            "Yeh galat payment hai, refund chahiye",
        ],
        expected_intent=VoiceIntent.DISPUTE,
        expected_outcome="Flags case for dispute review & human intervention",
    ),
]


class VoiceSession:
    """
    Active conversational state for a single customer recovery dialogue.
    """

    def __init__(
        self,
        session_id: str,
        case_id: str,
        customer_id: str,
        customer_name: Optional[str] = None,
        amount: float = 999.0,
        currency: str = "INR",
        failure_reason: str = "Insufficient funds in bank account",
    ):
        self.session_id = session_id
        self.case_id = case_id
        self.customer_id = customer_id
        self.customer_name = customer_name or "Valued Customer"
        self.amount = amount
        self.currency = currency
        self.failure_reason = failure_reason

        self.state: VoiceSessionState = VoiceSessionState.AWAITING_CONSENT
        self.has_consent: bool = False
        self.turns: List[VoiceTurn] = []
        self.detected_intents: List[VoiceIntent] = []
        self.promise_draft: Optional[PromiseToPayDraft] = None
        self.created_at: datetime = utc_now()
        self.updated_at: datetime = utc_now()
        self.clarification_attempts: int = 0
        self.action_executed: Optional[str] = None
        self.audit_log: List[str] = []

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "case_id": self.case_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "amount": self.amount,
            "currency": self.currency,
            "failure_reason": self.failure_reason,
            "state": self.state.value,
            "has_consent": self.has_consent,
            "turns": [t.model_dump(mode="json") for t in self.turns],
            "promise_draft": self.promise_draft.model_dump(mode="json") if self.promise_draft else None,
            "clarification_attempts": self.clarification_attempts,
            "action_executed": self.action_executed,
            "audit_log": self.audit_log,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_record(self) -> VoiceSessionRecord:
        last_intent = self.turns[-1].detected_intent.value if self.turns and self.turns[-1].detected_intent else None
        last_conf = self.turns[-1].confidence_score if self.turns else None
        return VoiceSessionRecord(
            session_id=self.session_id,
            case_id=self.case_id,
            state=self.state.value,
            consent_granted=self.has_consent,
            consent_timestamp=self.created_at if self.has_consent else None,
            language="hinglish",
            turn_count=len(self.turns),
            detected_intent=last_intent,
            intent_confidence=last_conf,
            proposed_action=self.action_executed,
            action_confirmed=self.state in (VoiceSessionState.CLOSURE, VoiceSessionState.EXECUTING_ACTION),
            escalated_to_human=self.state == VoiceSessionState.ESCALATED_TO_HUMAN,
            redacted_transcript_json=json.dumps([t.model_dump(mode="json") for t in self.turns]),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class VoiceSessionManager:
    """
    Service managing in-memory active voice sessions and persistence.
    """

    _active_sessions: Dict[str, VoiceSession] = {}

    def __init__(self, repository: SqlAlchemyRepository):
        self.repository = repository
        self.agent = VoiceRecoveryAgent()


    async def start_session(self, case: PaymentCase) -> VoiceSession:
        """
        Initializes a new voice recovery session for a given case.
        """
        session_id = f"vses_{uuid.uuid4().hex[:12]}"
        cust_id = case.context.customer_id if hasattr(case, "context") else getattr(case, "customer_id", "cust_demo")
        cust_name = case.context.customer_name if hasattr(case, "context") else getattr(case, "customer_name", "Customer")
        amount = case.context.amount_inr if hasattr(case, "context") else getattr(case, "amount", 999.0)
        curr = case.context.currency if hasattr(case, "context") else getattr(case, "currency", "INR")
        fail_desc = case.context.failure_reason if hasattr(case, "context") else getattr(case, "raw_error_description", "Payment declined")

        session = VoiceSession(
            session_id=session_id,
            case_id=case.case_id,
            customer_id=cust_id,
            customer_name=cust_name,
            amount=amount,
            currency=curr,
            failure_reason=fail_desc,
        )

        initial_greeting = (
            f"Namaste, main Razorpay Recovery Autopilot se Aarav bol raha hoon. "
            f"Aapke subscription renewal (Rs {session.amount:,.2f}) ka payment bank se complete nahi ho paya tha. "
            f"Kya main is payment ko resolve karne ke liye 1 minute aapse baat kar sakta hoon?"
        )
        initial_english = (
            f"Hello, I am Aarav from Razorpay Recovery Autopilot. "
            f"Your subscription renewal payment of Rs {session.amount:,.2f} could not be completed. "
            f"Do I have your consent to assist you in resolving this payment?"
        )

        session.turns.append(
            VoiceTurn(
                turn_id=f"turn_{uuid.uuid4().hex[:8]}",
                role=VoiceTurnRole.AGENT,
                text=initial_greeting,
                translated_text=initial_english,
                language=LanguageDetected.HINGLISH,
                confidence_score=1.0,
            )
        )
        session.audit_log.append("Session initiated. Awaiting customer consent.")
        self._active_sessions[session_id] = session

        try:
            await self.repository.save_voice_session(session.to_record())
        except Exception as exc:
            logger.warning("Could not persist initial voice session: %s", exc)

        return session

    async def get_session(self, session_id: str) -> Optional[VoiceSession]:
        session = self._active_sessions.get(session_id)
        if session:
            return session

        db_rec = await self.repository.get_voice_session(session_id)
        if db_rec:
            s = VoiceSession(
                session_id=db_rec.session_id,
                case_id=db_rec.case_id,
                customer_id="cust_retrieved",
            )
            s.state = VoiceSessionState(db_rec.state)
            s.has_consent = db_rec.consent_granted
            if db_rec.redacted_transcript_json:
                try:
                    turns_data = json.loads(db_rec.redacted_transcript_json)
                    s.turns = [VoiceTurn(**t) for t in turns_data]
                except Exception:
                    pass
            self._active_sessions[session_id] = s
            return s

        return None

    async def grant_consent(self, session_id: str, consent_granted: bool) -> VoiceSession:
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.has_consent = consent_granted
        session.updated_at = utc_now()

        if consent_granted:
            session.state = VoiceSessionState.AWAITING_INTENT
            greeting_turn = VoiceTurn(
                turn_id=f"turn_{uuid.uuid4().hex[:8]}",
                role=VoiceTurnRole.AGENT,
                text="Shukriya! Aap chahein toh main turant WhatsApp par link bhej sakta hoon, ya fir agar aap kal pay karna chahein toh bata sakte hain.",
                translated_text="Thank you! If you prefer, I can send a payment link via WhatsApp, or if you wish to pay later/tomorrow, please let me know.",
                language=LanguageDetected.HINGLISH,
                confidence_score=1.0,
            )
            session.turns.append(greeting_turn)
            session.audit_log.append("Consent granted by customer.")
        else:
            session.state = VoiceSessionState.TERMINATED
            session.turns.append(
                VoiceTurn(
                    turn_id=f"turn_{uuid.uuid4().hex[:8]}",
                    role=VoiceTurnRole.AGENT,
                    text="Koi baat nahi. Aapka samay dene ke liye dhanyawad. Have a nice day!",
                    translated_text="No problem at all. Thank you for your time. Have a nice day!",
                    language=LanguageDetected.HINGLISH,
                    confidence_score=1.0,
                )
            )
            session.audit_log.append("Customer declined consent. Session terminated.")

        await self.repository.save_voice_session(session.to_record())
        return session

    async def process_customer_utterance(self, session_id: str, customer_text: str) -> Tuple[VoiceSession, VoiceAgentAnalysis]:
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        sanitized_text, flags = VoiceGuardrails.inspect_and_sanitize_input(customer_text)

        cust_turn = VoiceTurn(
            turn_id=f"turn_{uuid.uuid4().hex[:8]}",
            role=VoiceTurnRole.CUSTOMER,
            text=sanitized_text,
            language=LanguageDetected.HINGLISH,
        )
        session.turns.append(cust_turn)

        case = await self.repository.get_case(session.case_id)
        analysis = await self.agent.analyze_utterance(sanitized_text, session.turns, case)
        cust_turn.detected_intent = analysis.detected_intent
        cust_turn.confidence_score = analysis.confidence

        if analysis.requires_human_escalation:
            session.state = VoiceSessionState.ESCALATED_TO_HUMAN
            session.audit_log.append(f"Escalated to human support: {analysis.detected_intent.value}")
        elif analysis.detected_intent == VoiceIntent.STOP_CONTACT:
            session.state = VoiceSessionState.TERMINATED
            session.audit_log.append("Customer requested DND / Stop Contact.")
        elif analysis.detected_intent == VoiceIntent.PROMISE_TO_PAY:
            session.state = VoiceSessionState.AWAITING_CONFIRMATION
            promise_date = analysis.extracted_entities.get("promise_date", "tomorrow")
            session.promise_draft = PromiseToPayDraft(
                case_id=session.case_id,
                customer_id=session.customer_id,
                promised_amount=session.amount,
                promised_date=promise_date,
                notes=f"Hinglish voice agreement: {customer_text}",
            )
            session.audit_log.append(f"Created Promise to Pay draft for {promise_date}.")
        elif analysis.detected_intent in (VoiceIntent.SEND_PAYMENT_LINK, VoiceIntent.PAY_NOW):
            session.state = VoiceSessionState.AWAITING_CONFIRMATION
            session.audit_log.append("Customer requested payment link. Awaiting confirmation.")
        elif analysis.detected_intent == VoiceIntent.CONFIRM_YES:
            session.state = VoiceSessionState.EXECUTING_ACTION
            session.action_executed = "PAYMENT_LINK_SENT"
            session.audit_log.append("Customer confirmed action. Executed payment link dispatch.")
        elif analysis.detected_intent == VoiceIntent.UNCLEAR:
            session.clarification_attempts += 1
            if session.clarification_attempts >= 3:
                session.state = VoiceSessionState.ESCALATED_TO_HUMAN
                analysis.agent_response_hinglish = "Mujhe samajhne mein thodi dikkat ho rahi hai. Main aapko hamare executive se connect kar deta hoon."
                analysis.agent_response_english = "I am having difficulty understanding. Let me connect you directly with a representative."
            else:
                session.state = VoiceSessionState.CLARIFICATION

        agent_turn = VoiceTurn(
            turn_id=f"turn_{uuid.uuid4().hex[:8]}",
            role=VoiceTurnRole.AGENT,
            text=analysis.agent_response_hinglish,
            translated_text=analysis.agent_response_english,
            language=analysis.detected_language,
            confidence_score=analysis.confidence,
            action_suggested=analysis.recommended_action,
        )
        session.turns.append(agent_turn)
        session.updated_at = utc_now()

        await self.repository.save_voice_session(session.to_record())
        return session, analysis

    async def confirm_action_or_promise(self, session_id: str) -> Tuple[VoiceSession, Dict]:
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        case = await self.repository.get_case(session.case_id)
        result_meta = {}

        if session.promise_draft:
            target_date = utc_now() + timedelta(days=1)
            promise = PromiseToPay(
                case_id=session.case_id,
                promised_datetime=target_date,
                notes=session.promise_draft.notes,
                channel="WHATSAPP",
            )
            await self.repository.save_promise_to_pay(promise)

            if case:
                case.promise_to_pay = promise
                case.status = CaseStatus.PROMISED_TO_PAY
                await self.repository.save_case(case)

            session.state = VoiceSessionState.CLOSURE
            session.action_executed = f"PROMISE_RECORDED_{target_date.strftime('%Y-%m-%d')}"
            session.audit_log.append(f"Confirmed Promise to Pay until {target_date.strftime('%Y-%m-%d')}.")
            result_meta["promise_id"] = promise.promise_id
            result_meta["status"] = "PROMISED_TO_PAY"

        else:
            session.state = VoiceSessionState.CLOSURE
            session.action_executed = "PAYMENT_LINK_DISPATCHED"
            session.audit_log.append("Sent Razorpay payment link via WhatsApp / SMS.")
            result_meta["status"] = "LINK_DISPATCHED"
            result_meta["payment_url"] = f"https://rzp.io/i/demo_rec_{session.session_id[:8]}"

        session.updated_at = utc_now()
        await self.repository.save_voice_session(session.to_record())
        return session, result_meta

    async def escalate_to_human(self, session_id: str, reason: str = "Customer request") -> VoiceSession:
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.state = VoiceSessionState.ESCALATED_TO_HUMAN
        session.audit_log.append(f"Explicitly escalated to human: {reason}")
        session.updated_at = utc_now()

        case = await self.repository.get_case(session.case_id)
        if case:
            case.status = CaseStatus.AWAITING_APPROVAL
            await self.repository.save_case(case)

        await self.repository.save_voice_session(session.to_record())
        return session

    async def delete_transcript(self, session_id: str) -> bool:
        session = await self.get_session(session_id)
        if session:
            session.turns = []
            session.audit_log.append("Transcript purged upon customer privacy request.")
        return await self.repository.delete_voice_transcript(session_id)
