"""
Voice Safety Guardrails and Deterministic Policy Enforcers.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from recovery_autopilot.voice.prompts import localized_responses
from recovery_autopilot.voice.voice_models import LanguageDetected, VoiceAgentAnalysis, VoiceIntent

OTP_PATTERNS = [
    r"\b\d{4,6}\b.*?(?:otp|code|pin)",
    r"(?:otp|code|pin|cvv|password|passcode)\s*(?:is|hai|batao|share|bhejo|de do|hai)?\s*[:=]?\s*\b\d{3,6}\b",
    r"\b(?:cvv|cvc|security code)\b",
    r"\b(?:atm pin|upi pin|mpin|netbanking password)\b",
    r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b",  # 16-digit card number
]

DND_PATTERNS = [
    r"\b(?:stop calling|don't call|do not call|dnd|mat call karo|call mat karo|phone mat karo|never call|stop harassing)\b",
    r"\b(?:unsubscribe|opt out|remove my number|complaint karunga|police|harass|hata|registry)\b",
    r"(?:कॉल न करें|नंबर.*?हटा)",
    r"(?:ফোন করবেন না|কল করবেন না|নম্বর.*?সরান)",
    r"(?:அழைக்க வேண்டாம்|என் எண்ணை.*?நீக்கு)",
    r"(?:కాల్ చేయవద్దు|నా నంబర్.*?తొలగించ)",
    r"(?:फोन करू नका|माझा नंबर.*?काढा)",
    r"(?:ಕರೆ ಮಾಡಬೇಡಿ|ನನ್ನ ನಂಬರ್.*?ತೆಗೆ)",
]

ALREADY_PAID_PATTERNS = [
    r"\b(?:already paid|paise kat gaye|paise cut gaye|kat gaya|cut gaya|de diya|paid successfully|amount deducted)\b",
    r"\b(?:account se kat gaye|paise chale gaye|receipt|already transfer|deducted|successful debit|debit card)\b",
    r"(?:कट चुके|पहले ही|भुगतान.*?हो गया|खाते से)",
    r"(?:আগেই.*?পেমেন্ট|টাকা.*?কেটে|payment.*?হয়ে গেছে)",
    r"(?:ஏற்கனவே.*?payment|பணம்.*?கழிக்கப்பட்ட)",
    r"(?:ఇప్పటికే.*?payment|డబ్బు.*?కట్)",
    r"(?:आधीच.*?payment|पैसे.*?कापले)",
    r"(?:ಈಗಾಗಲೇ.*?payment|ಹಣ.*?ಕಟ್)",
]


DISPUTE_PATTERNS = [
    r"\b(?:fraud|scam|dhokha|galat hai|fake|unauthorized|not my payment|maine nahi kiya|fraudulent)\b",
    r"\b(?:cancel subscription|refund chahiye|refund|money back|canceled my subscription|cancellation)\b",
    r"(?:गलत कटौती|रद्द कर दी)",
    r"(?:অননুমোদিত|ভুল.*?চার্জ|refund.*?চাই)",
    r"(?:அங்கீகரிக்காத|தவறான.*?charge|refund.*?வேண்டும்)",
    r"(?:అనధికార|తప్పు.*?charge|refund.*?కావాలి)",
    r"(?:अनधिकृत|चुकीचा.*?charge|refund.*?हवा)",
    r"(?:ಅನಧಿಕೃತ|ತಪ್ಪಾದ.*?charge|refund.*?ಬೇಕು)",
]

HUMAN_ESCALATION_PATTERNS = [
    r"\b(?:human|agent|manager|senior|kisi insaan se baat karao|executive se baat|talk to a person|supervisor)\b",
    r"\b(?:representative|customer care executive|support person|real representative|support specialist)\b",
    r"(?:अधिकारी|प्रतिनिधि|जीवित प्रतिनिधि)",
    r"(?:মানুষের সঙ্গে|প্রতিনিধির সঙ্গে|customer care)",
    r"(?:மனிதருடன்|நபருடன் பேச|customer care)",
    r"(?:మనిషితో|వ్యక్తితో మాట్లాడ|customer care)",
    r"(?:माणसाशी|प्रतिनिधीशी|customer care)",
    r"(?:ವ್ಯಕ್ತಿಯೊಂದಿಗೆ|ಮನುಷ್ಯರೊಂದಿಗೆ|customer care)",
]


class VoiceGuardrails:
    """
    Deterministic safety engine evaluating speech inputs and agent responses before execution.
    """

    @staticmethod
    def inspect_and_sanitize_input(text: str) -> Tuple[str, List[str]]:
        """
        Detects any sensitive info (OTP/PIN/Card), redacts them from transcripts, and flags violations.
        """
        flags = []
        sanitized = text

        # Check for OTP / sensitive credentials
        for pattern in OTP_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append("SENSITIVE_CREDENTIAL_DETECTED")
                sanitized = re.sub(r"\b\d{3,6}\b", "[REDACTED_CODE]", sanitized)
                sanitized = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[REDACTED_CARD]", sanitized)

        # Redact generic phone numbers if 10 digits
        sanitized = re.sub(r"\b[6-9]\d{9}\b", "[REDACTED_PHONE]", sanitized)
        # Redact email addresses
        sanitized = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "[REDACTED_EMAIL]", sanitized)

        return sanitized, flags

    @staticmethod
    def evaluate_override_intents(text: str) -> Optional[VoiceIntent]:
        """
        Checks for high-priority deterministic intents (DND, Already Paid, Human Escalation, Dispute).
        """
        text_lower = text.lower()

        for pat in DND_PATTERNS:
            if re.search(pat, text_lower, re.IGNORECASE):
                return VoiceIntent.STOP_CONTACT

        for pat in HUMAN_ESCALATION_PATTERNS:
            if re.search(pat, text_lower, re.IGNORECASE):
                return VoiceIntent.REQUEST_HUMAN

        for pat in ALREADY_PAID_PATTERNS:
            if re.search(pat, text_lower, re.IGNORECASE):
                return VoiceIntent.ALREADY_PAID

        for pat in DISPUTE_PATTERNS:
            if re.search(pat, text_lower, re.IGNORECASE):
                return VoiceIntent.DISPUTE

        return None

    @staticmethod
    def validate_agent_output(analysis: VoiceAgentAnalysis) -> VoiceAgentAnalysis:
        """
        Ensures agent response never asks for credentials, complies with safety rules, and marks human escalation.
        """
        response_text = " ".join(
            [analysis.agent_response, analysis.agent_response_hinglish, analysis.agent_response_english]
            + list(analysis.localized_responses.values())
        ).lower()

        for pattern in OTP_PATTERNS:
            if re.search(pattern, response_text):
                analysis.is_safe = False
                analysis.safety_flags.append("BLOCKED_AGENT_SENSITIVE_REQUEST")
                responses = localized_responses("security")
                analysis.localized_responses = responses
                analysis.agent_response_hinglish = responses[LanguageDetected.HINGLISH.value]
                analysis.agent_response_english = responses[LanguageDetected.ENGLISH.value]
                analysis.agent_response = analysis.response_for(analysis.response_language)

        if analysis.detected_intent in (VoiceIntent.DISPUTE, VoiceIntent.ALREADY_PAID, VoiceIntent.REQUEST_HUMAN):
            analysis.requires_human_escalation = True

        if analysis.detected_intent == VoiceIntent.STOP_CONTACT:
            analysis.recommended_action = "dnd_opt_out"
            responses = localized_responses("dnd")
            analysis.localized_responses = responses
            analysis.agent_response_hinglish = responses[LanguageDetected.HINGLISH.value]
            analysis.agent_response_english = responses[LanguageDetected.ENGLISH.value]
            analysis.agent_response = analysis.response_for(analysis.response_language)

        return analysis
