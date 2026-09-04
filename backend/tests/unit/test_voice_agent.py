"""
Unit tests for Hinglish Voice Recovery Agent and Safety Guardrails.
"""
import pytest

from recovery_autopilot.voice.voice_agent import VoiceRecoveryAgent
from recovery_autopilot.voice.voice_guardrails import VoiceGuardrails
from recovery_autopilot.voice.voice_models import LanguageDetected, VoiceIntent


@pytest.mark.asyncio
async def test_guardrail_redaction_and_anti_otp():
    # Sensitive credential attempts
    text = "Mera OTP 948192 hai aur CVV 123 hai"
    sanitized, flags = VoiceGuardrails.inspect_and_sanitize_input(text)

    assert "SENSITIVE_CREDENTIAL_DETECTED" in flags
    assert "948192" not in sanitized
    assert "[REDACTED_CODE]" in sanitized


@pytest.mark.asyncio
async def test_guardrail_phone_email_masking():
    text = "Mera phone 9876543210 hai aur email user@example.com hai"
    sanitized, flags = VoiceGuardrails.inspect_and_sanitize_input(text)

    assert "9876543210" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "user@example.com" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized


@pytest.mark.asyncio
async def test_voice_agent_send_payment_link_hinglish():
    agent = VoiceRecoveryAgent(provider_name="fake")
    utterance = "Haan mujhe WhatsApp pe payment link bhej do, main UPI se pay kar deta hoon"

    analysis = await agent.analyze_utterance(utterance, conversation_history=[])

    assert analysis.detected_intent == VoiceIntent.SEND_PAYMENT_LINK
    assert analysis.is_safe is True
    assert "WhatsApp" in analysis.agent_response_hinglish or "link" in analysis.agent_response_hinglish.lower()
    assert analysis.requires_confirmation is True


@pytest.mark.asyncio
async def test_voice_agent_promise_to_pay():
    agent = VoiceRecoveryAgent(provider_name="fake")
    utterance = "Mera salary kal aayega, main kal shaam ko pakka pay kar dunga"

    analysis = await agent.analyze_utterance(utterance, conversation_history=[])

    assert analysis.detected_intent == VoiceIntent.PROMISE_TO_PAY
    assert analysis.extracted_entities.get("promise_date") == "tomorrow"
    assert analysis.requires_confirmation is True


@pytest.mark.asyncio
async def test_voice_agent_already_paid_safe_escalation():
    agent = VoiceRecoveryAgent(provider_name="fake")
    utterance = "Mere bank se paise kat gaye hain already, dubara charge mat karo"

    analysis = await agent.analyze_utterance(utterance, conversation_history=[])

    assert analysis.detected_intent == VoiceIntent.ALREADY_PAID
    assert analysis.requires_human_escalation is True


@pytest.mark.asyncio
async def test_voice_agent_stop_contact_dnd():
    agent = VoiceRecoveryAgent(provider_name="fake")
    utterance = "Mujhe call mat karo, remove my number from your list, put in DND"

    analysis = await agent.analyze_utterance(utterance, conversation_history=[])

    assert analysis.detected_intent == VoiceIntent.STOP_CONTACT
    assert "DND" in analysis.agent_response_hinglish
    assert analysis.recommended_action == "dnd_opt_out"


@pytest.mark.asyncio
async def test_voice_agent_human_escalation():
    agent = VoiceRecoveryAgent(provider_name="fake")
    utterance = "Mujhe kisi human agent ya executive se baat karni hai"

    analysis = await agent.analyze_utterance(utterance, conversation_history=[])

    assert analysis.detected_intent == VoiceIntent.REQUEST_HUMAN
    assert analysis.requires_human_escalation is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "utterance", "expected_script"),
    [
        (LanguageDetected.HINDI, "कृपया WhatsApp पर payment link भेजिए", "भेज"),
        (LanguageDetected.BENGALI, "আমাকে WhatsApp-এ payment link পাঠান", "পাঠ"),
        (LanguageDetected.TAMIL, "WhatsApp-ல் payment link அனுப்புங்கள்", "அனுப்ப"),
        (LanguageDetected.TELUGU, "WhatsAppలో payment link పంపండి", "పంప"),
        (LanguageDetected.MARATHI, "मला WhatsApp वर payment link पाठवा", "पाठव"),
        (LanguageDetected.KANNADA, "WhatsAppನಲ್ಲಿ payment link ಕಳುಹಿಸಿ", "ಕಳುಹ"),
    ],
)
async def test_voice_agent_speaks_selected_indian_language(language, utterance, expected_script):
    agent = VoiceRecoveryAgent(provider_name="fake")

    analysis = await agent.analyze_utterance(
        utterance,
        conversation_history=[],
        language_hint=language,
    )

    assert analysis.detected_intent == VoiceIntent.SEND_PAYMENT_LINK
    assert analysis.response_language == language
    assert expected_script in analysis.agent_response
    assert analysis.localized_responses[language.value] == analysis.agent_response


@pytest.mark.asyncio
async def test_low_transcription_confidence_never_executes_action():
    agent = VoiceRecoveryAgent(provider_name="fake")

    analysis = await agent.analyze_utterance(
        "send the payment link",
        conversation_history=[],
        language_hint=LanguageDetected.ENGLISH,
        transcription_confidence=0.31,
    )

    assert analysis.detected_intent == VoiceIntent.UNCLEAR
    assert analysis.recommended_action == "clarify"
    assert analysis.requires_confirmation is False
