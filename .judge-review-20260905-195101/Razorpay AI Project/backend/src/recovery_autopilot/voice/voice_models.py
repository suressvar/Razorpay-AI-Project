"""
Voice Recovery Domain Models & State Machine Definitions.
Supports 7 Indian Languages, 6 Code-Switched Dialects, Typed STT Interfaces,
and Structured Intent Contracts.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VoiceSessionState(str, Enum):
    INITIALIZED = "INITIALIZED"
    AWAITING_CONSENT = "AWAITING_CONSENT"
    GREETING = "GREETING"
    EXPLAINING_FAILURE = "EXPLAINING_FAILURE"
    AWAITING_INTENT = "AWAITING_INTENT"
    CLARIFICATION = "CLARIFICATION"
    PROPOSING_OPTION = "PROPOSING_OPTION"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    EXECUTING_ACTION = "EXECUTING_ACTION"
    RECORDING_PROMISE = "RECORDING_PROMISE"
    CLOSURE = "CLOSURE"
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"
    TERMINATED = "TERMINATED"


class VoiceIntent(str, Enum):
    PAY_NOW = "pay_now"
    SEND_PAYMENT_LINK = "send_payment_link"
    RETRY_LATER = "retry_later"
    PROMISE_TO_PAY = "promise_to_pay"
    ALREADY_PAID = "already_paid"
    PAYMENT_DISPUTE = "payment_dispute"
    DISPUTE = "dispute"  # backward compatibility alias
    WRONG_CUSTOMER = "wrong_customer"
    REQUEST_HUMAN = "request_human"
    STOP_CONTACT = "stop_contact"
    REPEAT_REQUEST = "repeat_request"
    LANGUAGE_CHANGE = "language_change"
    CONFIRM_YES = "confirm_yes"
    CONFIRM_NO = "confirm_no"
    UNCLEAR = "unclear"
    UNKNOWN = "unknown"


class LanguageDetected(str, Enum):
    # Auto-detection default
    AUTO = "auto"

    # 7 Primary Supported Indian Languages
    ENGLISH = "english"
    HINDI = "hindi"
    KANNADA = "kannada"
    TAMIL = "tamil"
    TELUGU = "telugu"
    MARATHI = "marathi"
    BENGALI = "bengali"

    # 6 Code-Switched Dialects
    HINGLISH = "hinglish"
    KANGLISH = "kanglish"
    TANGLISH = "tanglish"
    TENGLISH = "tenglish"
    MARATHI_ENGLISH = "marathi_english"
    BENGALI_ENGLISH = "bengali_english"

    UNKNOWN = "unknown"


class STTModelProfile(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"


class TranscriptMetadata(BaseModel):
    original_transcript: str
    normalized_transcript: str
    detected_language: str
    language_confidence: float = 1.0
    alternative_languages: List[str] = Field(default_factory=list)
    code_switched: bool = False
    transcription_confidence: float = 1.0
    needs_clarification: bool = False


class IntentEntities(BaseModel):
    promised_date: Optional[str] = None
    promised_time: Optional[str] = None
    amount: Optional[float] = None
    requested_language: Optional[str] = None


class StructuredIntentResult(BaseModel):
    intent: str = "unknown"
    confidence: float = 0.0
    entities: IntentEntities = Field(default_factory=IntentEntities)
    requires_confirmation: bool = False
    requires_human: bool = False
    clarification_question: Optional[str] = None
    safety_reason: Optional[str] = None


class AudioDiagnostics(BaseModel):
    microphone_name: Optional[str] = None
    input_sample_rate: int = 16000
    processed_sample_rate: int = 16000
    recording_duration_sec: float = 0.0
    speech_duration_sec: float = 0.0
    signal_level_rms: float = 0.0
    peak_amplitude: float = 0.0
    is_clipped: bool = False
    detected_language: str = "en-IN"
    transcription_confidence: float = 1.0
    latency_ms: float = 0.0
    raw_transcript: str = ""
    normalized_transcript: str = ""
    extracted_intent: str = "unknown"


class VoiceTurnRole(str, Enum):
    SYSTEM = "system"
    AGENT = "agent"
    CUSTOMER = "customer"


class VoiceTurn(BaseModel):
    turn_id: str
    role: VoiceTurnRole
    text: str
    translated_text: Optional[str] = None
    language: LanguageDetected = LanguageDetected.HINGLISH
    detected_intent: Optional[VoiceIntent] = None
    confidence_score: float = 1.0
    action_suggested: Optional[str] = None
    audio_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceAgentAnalysis(BaseModel):
    detected_intent: VoiceIntent
    confidence: float = Field(ge=0.0, le=1.0)
    detected_language: LanguageDetected
    customer_sentiment: str = "neutral"  # neutral, frustrated, cooperative, anxious
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)  # e.g. {"promise_date": "tomorrow", "time": "5pm"}
    reasoning: str
    is_safe: bool = True
    safety_flags: List[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    response_language: LanguageDetected = LanguageDetected.ENGLISH
    agent_response: str = ""
    agent_response_hinglish: str = ""
    agent_response_english: str = ""
    localized_responses: Dict[str, str] = Field(default_factory=dict)
    requires_confirmation: bool = False
    requires_human_escalation: bool = False

    # Enhanced structured contracts
    structured_intent: Optional[StructuredIntentResult] = None
    transcript_meta: Optional[TranscriptMetadata] = None

    def response_for(self, language: LanguageDetected | str) -> str:
        """Return the best ready-to-speak response for a requested language."""
        language_value = language.value if isinstance(language, LanguageDetected) else language
        return (
            self.localized_responses.get(language_value)
            or (self.agent_response_hinglish if language_value in [LanguageDetected.HINGLISH.value, LanguageDetected.HINDI.value] else "")
            or (self.agent_response_english if language_value == LanguageDetected.ENGLISH.value else "")
            or self.agent_response
            or self.agent_response_english
            or self.agent_response_hinglish
        )


class VoiceScenarioPreset(BaseModel):
    scenario_id: str
    title: str
    description: str
    customer_persona: str
    sample_utterances: List[str]
    expected_intent: VoiceIntent
    expected_outcome: str


class PromiseToPayDraft(BaseModel):
    case_id: str
    customer_id: str
    promised_amount: float
    promised_date: str  # YYYY-MM-DD or descriptive like "tomorrow"
    channel: str = "voice_multilingual"
    notes: Optional[str] = None
