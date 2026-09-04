"""
Hinglish Conversational Voice Recovery Agent.
Analyzes customer speech in English, Hindi, and Hinglish, reasons over failure context,
and generates empathetic, policy-compliant recovery responses.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from recovery_autopilot.config import get_settings
from recovery_autopilot.domain.models import PaymentCase
from recovery_autopilot.voice.voice_guardrails import VoiceGuardrails
from recovery_autopilot.voice.voice_models import (
    LanguageDetected,
    VoiceAgentAnalysis,
    VoiceIntent,
    VoiceTurn,
)

logger = logging.getLogger(__name__)


VOICE_AGENT_SYSTEM_PROMPT = """
You are "Aarav", an empathetic, polite, and professional AI Voice Recovery Agent representing a subscription service powered by Razorpay.
Your goal is to help customers whose subscription payment has failed, understand why, and offer safe, policy-approved solutions in natural Indian Hinglish (conversational mix of Hindi and English) and clear English.

CORE RULES:
1. NEVER ASK FOR OR ACCEPT SENSITIVE CREDENTIALS (OTP, UPI PIN, ATM PIN, CVV, Netbanking Password, or full 16-digit card numbers).
   If customer mentions these, firmly remind them that we NEVER ask for OTPs or PINs.
2. IF CUSTOMER SAYS "ALREADY PAID" or "PAISE KAT GAYE": Do not argue. Acknowledge immediately, state that we will check bank confirmation / escalate to finance support, and pause retries.
3. IF CUSTOMER SAYS "STOP CALLING" / "DO NOT CALL" / DND: Apologize politely, confirm registration into Do Not Disturb list, and stop immediately.
4. IF CUSTOMER ASKS FOR HUMAN AGENT: Immediately agree and transfer to human support specialist.
5. IF CUSTOMER PROMISES TO PAY LATER: Extract the promised date/time, thank them, and agree to send a payment link before that time.
6. IF CUSTOMER WANTS A PAYMENT LINK: Confirm sending a secure Razorpay payment link via WhatsApp / SMS / Email.
7. TONE: Warm, respectful, reassuring, helpful, concise (conversational speech suitable for voice/TTS).
"""


class VoiceRecoveryAgent:
    """
    Conversational agent supporting Gemini, Ollama, and Deterministic fallback engines.
    """

    def __init__(self, provider_name: Optional[str] = None):
        self.settings = get_settings()
        self.provider_name = provider_name or self.settings.MODEL_PROVIDER

    def _detect_language(self, text: str) -> LanguageDetected:
        text_lower = text.lower()
        hindi_keywords = ["hai", "nahi", "karo", "bhejo", "kat", "gaye", "karna", "baat", "paise", "aaj", "kal", "kripya", "dhanyawad", "raha", "rahi"]
        matched_hindi = sum(1 for kw in hindi_keywords if re.search(rf"\b{kw}\b", text_lower))

        # Check devanagari script
        if re.search(r"[\u0900-\u097F]", text):
            return LanguageDetected.HINDI
        if matched_hindi >= 1:
            return LanguageDetected.HINGLISH
        return LanguageDetected.ENGLISH

    def _rule_based_fallback(self, customer_text: str, case: Optional[PaymentCase] = None) -> VoiceAgentAnalysis:
        """
        Deterministic intent analysis for high accuracy and instant offline evaluation.
        """
        sanitized_text, safety_flags = VoiceGuardrails.inspect_and_sanitize_input(customer_text)
        override_intent = VoiceGuardrails.evaluate_override_intents(sanitized_text)

        text_lower = sanitized_text.lower()
        lang = self._detect_language(sanitized_text)

        # 0. Check for sensitive credential input attempt
        if "SENSITIVE_CREDENTIAL_DETECTED" in safety_flags:
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.UNCLEAR,
                confidence=0.99,
                detected_language=lang,
                customer_sentiment="anxious",
                reasoning="Customer attempted to share OTP, PIN, or CVV; blocked by anti-fraud guardrail",
                is_safe=False,
                safety_flags=safety_flags,
                recommended_action="clarify",
                agent_response_hinglish="Suraksha ke liye, hum aapse kabhi bhi OTP ya PIN nahi maangte. Kripya kisi ke saath apna OTP share na karein.",
                agent_response_english="For your security, we never request OTPs or PINs. Please do not share sensitive credentials with anyone.",
                requires_confirmation=False,
                requires_human_escalation=False,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        # 1. Check override intents
        if override_intent == VoiceIntent.STOP_CONTACT:
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.STOP_CONTACT,
                confidence=0.98,
                detected_language=lang,
                customer_sentiment="frustrated",
                reasoning="Customer requested not to be contacted or DND",
                is_safe=True,
                recommended_action="dnd_opt_out",
                agent_response_hinglish="Theek hai ji, maine aapka number DND list mein daal diya hai. Aapko aage se koi reminder nahi aayega. Dhanyawad.",
                agent_response_english="Understood, I have placed your number on the DND list. You will not receive any further reminders. Thank you.",
                requires_confirmation=False,
                requires_human_escalation=False,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        if override_intent == VoiceIntent.REQUEST_HUMAN:
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.REQUEST_HUMAN,
                confidence=0.96,
                detected_language=lang,
                customer_sentiment="frustrated",
                reasoning="Customer requested a human agent or manager",
                is_safe=True,
                recommended_action="human_escalation",
                agent_response_hinglish="Zaroor, main aapki call turant hamare senior customer support executive ko transfer kar raha hoon. Kripya line par bane rahein.",
                agent_response_english="Certainly, I am transferring your call immediately to a senior customer support specialist. Please stay on the line.",
                requires_confirmation=False,
                requires_human_escalation=True,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        if override_intent == VoiceIntent.ALREADY_PAID:
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.ALREADY_PAID,
                confidence=0.95,
                detected_language=lang,
                customer_sentiment="neutral",
                reasoning="Customer stated money was already deducted",
                is_safe=True,
                recommended_action="human_escalation",
                agent_response_hinglish="Samajh gaya. Agar aapke account se paise kat chuke hain, toh main payment verify karne ke liye case finance team ko bhej raha hoon. Hum dobara deduct nahi karenge.",
                agent_response_english="Understood. If the amount was already deducted, I will flag this case for our finance team to verify bank reconciliation. We will not charge again.",
                requires_confirmation=False,
                requires_human_escalation=True,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        if override_intent == VoiceIntent.DISPUTE:
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.DISPUTE,
                confidence=0.92,
                detected_language=lang,
                customer_sentiment="frustrated",
                reasoning="Customer disputes the charge or subscription validity",
                is_safe=True,
                recommended_action="human_escalation",
                agent_response_hinglish="Aapki baat note kar li gayi hai. Main is transaction ko dispute review ke liye hamare compliance specialist ko forward kar raha hoon.",
                agent_response_english="Your concern has been noted. I am escalating this transaction to our compliance team for formal dispute review.",
                requires_confirmation=False,
                requires_human_escalation=True,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        # 2. Check Negative / No / Cancel
        if any(w in text_lower for w in ["nahi abhi", "not right now", "don't want to proceed", "नहीं, अभी", "not now", "cancel"]):
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.CONFIRM_NO,
                confidence=0.90,
                detected_language=lang,
                customer_sentiment="neutral",
                reasoning="Customer indicated no or declined option",
                is_safe=True,
                recommended_action="clarify",
                agent_response_hinglish="Koi baat nahi. Kya aap baad mein payment karna chahenge ya kisi aur madad ki zaroorat hai?",
                agent_response_english="No problem. Would you prefer to pay at a later time, or is there anything else I can help you with?",
                requires_confirmation=False,
                requires_human_escalation=False,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        # 3. Check Affirmative / Yes
        if any(w in text_lower for w in ["haan bilkul", "theek hai, done", "yes please proceed", "sure, send it", "हाँ, कृपया", "हाँ ठीक", "yes please", "sure proceed"]):
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.CONFIRM_YES,
                confidence=0.94,
                detected_language=lang,
                customer_sentiment="cooperative",
                reasoning="Customer confirmed affirmative agreement",
                is_safe=True,
                recommended_action="send_link",
                agent_response_hinglish="Shukriya! Maine payment link aapke number par share kar diya hai. Link par click karke aap payment poori kar sakte hain.",
                agent_response_english="Thank you! I have sent the payment link to your mobile number. You can complete the payment by clicking the link.",
                requires_confirmation=False,
                requires_human_escalation=False,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        # 4. Check Promise to Pay / Later / Tomorrow / Kal / Shaam / Monday
        promise_keywords = [
            "kal", "tomorrow", "evening", "shaam", "baad me", "later", "monday", "somvaar", "next week",
            "agle", "salary", "payday", "3 din", "2 days", "remind", "dopahar", "settle", "arrange",
            "वेतन", "शाम तक", "दोपहर में", "भुगतान कर दूंगा", "पैसे भर दूंगा"
        ]
        if any(w in text_lower for w in promise_keywords):
            extracted_date = "tomorrow" if ("kal" in text_lower or "tomorrow" in text_lower or "कल" in text_lower) else "in 2 days"
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.PROMISE_TO_PAY,
                confidence=0.93,
                detected_language=lang,
                customer_sentiment="cooperative",
                extracted_entities={"promise_date": extracted_date},
                reasoning=f"Customer promised to pay on {extracted_date}",
                is_safe=True,
                recommended_action="promise_to_pay",
                agent_response_hinglish=f"Bilkul theek hai ji. Maine aapka promise to pay note kar liya hai ({extracted_date}). Hum tab tak koi extra charge nahi lagayenge aur aapko payment link reminder bhejenge. Kya yeh theek hai?",
                agent_response_english=f"Sure! I have recorded your promise to pay for {extracted_date}. We will pause retries until then and send a reminder link. Is that okay?",
                requires_confirmation=True,
                requires_human_escalation=False,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        # 5. Check Link Request / Pay Now / UPI / WhatsApp / SMS
        if any(w in text_lower for w in ["link", "whatsapp", "bhej", "send", "sms", "text me", "message", "qr", "upi", "gpay", "phonepe", "लिंक", "भेजें", "भेज दीजिए", "शेयर", "email"]):
            analysis = VoiceAgentAnalysis(
                detected_intent=VoiceIntent.SEND_PAYMENT_LINK,
                confidence=0.94,
                detected_language=lang,
                customer_sentiment="cooperative",
                reasoning="Customer requested a payment link or WhatsApp/SMS option",
                is_safe=True,
                recommended_action="send_link",
                agent_response_hinglish="Ji bilkul, main aapke registered WhatsApp aur SMS par direct Razorpay payment link bhej raha hoon jisse aap UPI ya card se pay kar sakein. Kya main link send kar doon?",
                agent_response_english="Certainly! I will send a direct Razorpay payment link to your registered WhatsApp and SMS so you can pay via UPI or card. Shall I send it now?",
                requires_confirmation=True,
                requires_human_escalation=False,
            )
            return VoiceGuardrails.validate_agent_output(analysis)

        # 6. Default Unclear / Clarification
        analysis = VoiceAgentAnalysis(
            detected_intent=VoiceIntent.UNCLEAR,
            confidence=0.60,
            detected_language=lang,
            customer_sentiment="neutral",
            reasoning="Utterance did not match standard intents clearly",
            is_safe=True,
            recommended_action="clarify",
            agent_response_hinglish="Kya aap dobara bata sakte hain? Aap payment link chahte hain, baad mein pay karna chahte hain, ya kisi executive se baat karni hai?",
            agent_response_english="Could you please clarify? Would you like a payment link, schedule a later payment, or speak with an executive?",
            requires_confirmation=False,
            requires_human_escalation=False,
        )
        return VoiceGuardrails.validate_agent_output(analysis)

    async def analyze_utterance(
        self,
        customer_text: str,
        conversation_history: List[VoiceTurn],
        case: Optional[PaymentCase] = None,
    ) -> VoiceAgentAnalysis:
        sanitized_text, flags = VoiceGuardrails.inspect_and_sanitize_input(customer_text)

        # Immediate deterministic overrides (DND / Human / Credentials / Already paid)
        override = VoiceGuardrails.evaluate_override_intents(sanitized_text)
        if override or "SENSITIVE_CREDENTIAL_DETECTED" in flags:
            return self._rule_based_fallback(customer_text, case)

        # If provider is fake or synthetic mode, use rule engine directly
        if self.provider_name.lower() in ["fake", "synthetic", "mock"]:
            return self._rule_based_fallback(customer_text, case)

        # Try LLM inference with Gemini if available
        if self.provider_name.lower() == "gemini" and self.settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.settings.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-2.5-flash")

                history_context = "\n".join(
                    [f"{t.role.value}: {t.text}" for t in conversation_history[-4:]]
                )
                case_context = (
                    f"Customer: {case.context.customer_id if hasattr(case, 'context') else 'Unknown'}, "
                    f"Amount: Rs {case.context.amount_inr if hasattr(case, 'context') else '999'}, "
                    f"Failure Reason: {case.context.failure_reason if hasattr(case, 'context') else 'Insufficient funds'}"
                )

                prompt = (
                    f"{VOICE_AGENT_SYSTEM_PROMPT}\n\n"
                    f"Case Context:\n{case_context}\n\n"
                    f"Recent Conversation:\n{history_context}\n\n"
                    f"Customer Latest Utterance: \"{sanitized_text}\"\n\n"
                    f"Output strictly valid JSON:"
                )

                response = await model.generate_content_async(prompt)
                raw_json = response.text.strip()
                if "```json" in raw_json:
                    raw_json = raw_json.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_json:
                    raw_json = raw_json.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw_json)
                analysis = VoiceAgentAnalysis(
                    detected_intent=VoiceIntent(parsed.get("detected_intent", "unclear")),
                    confidence=float(parsed.get("confidence", 0.85)),
                    detected_language=LanguageDetected(parsed.get("detected_language", "hinglish")),
                    customer_sentiment=parsed.get("customer_sentiment", "neutral"),
                    extracted_entities=parsed.get("extracted_entities", {}),
                    reasoning=parsed.get("reasoning", "LLM reasoning"),
                    is_safe=bool(parsed.get("is_safe", True)),
                    safety_flags=flags,
                    recommended_action=parsed.get("recommended_action"),
                    agent_response_hinglish=parsed.get("agent_response_hinglish", ""),
                    agent_response_english=parsed.get("agent_response_english", ""),
                    requires_confirmation=bool(parsed.get("requires_confirmation", False)),
                    requires_human_escalation=bool(parsed.get("requires_human_escalation", False)),
                )
                return VoiceGuardrails.validate_agent_output(analysis)
            except Exception as exc:
                logger.warning("Gemini voice reasoning failed, falling back to rule engine: %s", exc)

        return self._rule_based_fallback(customer_text, case)
