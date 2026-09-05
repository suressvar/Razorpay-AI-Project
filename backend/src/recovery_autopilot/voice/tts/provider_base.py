"""
Abstract Base Interface and Type Definitions for Multilingual Text-to-Speech (TTS) Providers.
Supports Indian English, Hindi, Kannada, Tamil, Telugu, Marathi, and Bengali.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from recovery_autopilot.voice.voice_models import LanguageDetected


class TTSModelTier(str, Enum):
    """Quality and latency tiers for Text-to-Speech synthesis."""
    HIGH_QUALITY = "high_quality"       # Rich formant synthesis with natural prosody
    LIGHTWEIGHT = "lightweight"         # Low-latency local acoustic synthesis
    BROWSER_FALLBACK = "browser"        # Strict locale-matching browser speech
    TEXT_ONLY = "text_only"             # Silent text fallback when voice unavailable


class VoiceGender(str, Enum):
    FEMALE = "female"
    MALE = "male"
    NEUTRAL = "neutral"


@dataclass
class VoiceProfile:
    """Descriptor for a specific voice actor or synthesized acoustic profile."""
    voice_id: str
    name: str
    language: LanguageDetected
    locale: str
    gender: VoiceGender = VoiceGender.FEMALE
    sample_rate: int = 24000
    naturalness_score: Optional[float] = None
    quality_rating: str = "Not measured"
    description: str = ""
    is_native: bool = True
    is_mock: bool = False


@dataclass
class TTSAudioResult:
    """Output bundle resulting from TTS synthesis."""
    audio_base64: str
    audio_format: str = "audio/wav"     # "audio/wav", "audio/mp3", or "audio/pcm"
    sample_rate: int = 24000
    duration_sec: float = 0.0
    text_spoken: str = ""
    ssml_used: Optional[str] = None
    language: LanguageDetected = LanguageDetected.ENGLISH
    voice_id: str = ""
    tier: TTSModelTier = TTSModelTier.HIGH_QUALITY
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSRequest:
    """Synthesis request parameters."""
    text: str
    language: LanguageDetected = LanguageDetected.ENGLISH
    voice_id: Optional[str] = None
    rate: float = 1.0                   # Speaking rate (0.75 - 1.25)
    pitch: float = 1.0                  # Pitch factor (0.8 - 1.2)
    tier: TTSModelTier = TTSModelTier.HIGH_QUALITY
    use_ssml: bool = False
    context_hint: Optional[str] = None


class BaseTTSProvider(ABC):
    """Abstract Base Class for local and remote TTS engines."""

    @abstractmethod
    def get_supported_languages(self) -> List[LanguageDetected]:
        """Returns the list of languages supported by this provider."""
        pass

    @abstractmethod
    def get_available_voices(self, language: Optional[LanguageDetected] = None) -> List[VoiceProfile]:
        """Returns available voice profiles, optionally filtered by language."""
        pass

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSAudioResult:
        """Synthesizes text into audio bytes and returns metadata."""
        pass

    @abstractmethod
    def estimate_duration(self, text: str, rate: float = 1.0) -> float:
        """Estimates the spoken duration of text in seconds."""
        pass
