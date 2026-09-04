"""
Voice Safety Guardrails and Deterministic Policy Enforcers.
"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from recovery_autopilot.voice.voice_models import VoiceAgentAnalysis, VoiceIntent

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
]

ALREADY_PAID_PATTERNS = [
    r"\b(?:already paid|paise kat gaye|paise cut gaye|kat gaya|cut gaya|de diya|paid successfully|amount deducted)\b",
    r"\b(?:account se kat gaye|paise chale gaye|receipt|already transfer|deducted|successful debit|debit card)\b",
    r"(?:कट चुके|पहले ही|भुगतान.*?हो गया|खाते से)",
]


DISPUTE_PATTERNS = [
    r"\b(?:fraud|scam|dhokha|galat hai|fake|unauthorized|not my payment|maine nahi kiya|fraudulent)\b",
    r"\b(?:cancel subscription|refund chahiye|refund|money back|canceled my subscription|cancellation)\b",
    r"(?:गलत कटौती|रद्द कर दी)",
]

HUMAN_ESCALATION_PATTERNS = [
    r"\b(?:human|agent|manager|senior|kisi insaan se baat karao|executive se baat|talk to a person|supervisor)\b",
    r"\b(?:representative|customer care executive|support person|real representative|support specialist)\b",
    r"(?:अधिकारी|प्रतिनिधि|जीवित प्रतिनिधि)",
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
        response_text = f"{analysis.agent_response_hinglish} {analysis.agent_response_english}".lower()

        for pattern in OTP_PATTERNS:
            if re.search(pattern, response_text):
                analysis.is_safe = False
                analysis.safety_flags.append("BLOCKED_AGENT_SENSITIVE_REQUEST")
                analysis.agent_response_hinglish = (
                    "Suraksha ke liye, hum aapse kabhi bhi OTP, PIN ya passwords nahi maangte. "
                    "Aap hamare secure Razorpay link ke zariye payment kar sakte hain."
                )
                analysis.agent_response_english = (
                    "For your security, we never ask for OTP, PIN, or passwords. "
                    "You can safely complete payment via our secure Razorpay link."
                )

        if analysis.detected_intent in (VoiceIntent.DISPUTE, VoiceIntent.ALREADY_PAID, VoiceIntent.REQUEST_HUMAN):
            analysis.requires_human_escalation = True

        if analysis.detected_intent == VoiceIntent.STOP_CONTACT:
            analysis.recommended_action = "dnd_opt_out"
            analysis.agent_response_hinglish = "Maine aapka number DND list mein daal diya hai. Hum aage se call nahi karenge. Dhanyawad."
            analysis.agent_response_english = "I have added your number to the DND list. We will not contact you further. Thank you."

        return analysis
