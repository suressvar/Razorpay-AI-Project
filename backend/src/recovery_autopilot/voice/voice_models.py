"""
Voice Recovery Domain Models & State Machine Definitions.
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
    DISPUTE = "dispute"
    REQUEST_HUMAN = "request_human"
    STOP_CONTACT = "stop_contact"
    CONFIRM_YES = "confirm_yes"
    CONFIRM_NO = "confirm_no"
    UNCLEAR = "unclear"
    UNKNOWN = "unknown"


class LanguageDetected(str, Enum):
    HINGLISH = "hinglish"
    HINDI = "hindi"
    ENGLISH = "english"
    UNKNOWN = "unknown"


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
    agent_response_hinglish: str
    agent_response_english: str
    requires_confirmation: bool = False
    requires_human_escalation: bool = False


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
    channel: str = "voice_hinglish"
    notes: Optional[str] = None
