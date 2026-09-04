"""
Typed Speech-to-Text (STT) Provider Abstract Interface and Data Contracts.
Supports local engines, remote fallback, word-level timestamps, and model profiles.
"""
from __future__ import annotations

import abc
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field

from recovery_autopilot.voice.voice_models import STTModelProfile


class STTWordTimestamp(BaseModel):
    word: str
    start_sec: float
    end_sec: float
    confidence: float = 1.0


class STTAlternative(BaseModel):
    transcript: str
    confidence: float


class STTResult(BaseModel):
    transcript: str
    detected_language: str = "en-IN"
    confidence: float = 1.0
    word_timestamps: List[STTWordTimestamp] = Field(default_factory=list)
    alternatives: List[STTAlternative] = Field(default_factory=list)
    latency_ms: float = 0.0
    model_profile: STTModelProfile = STTModelProfile.BALANCED
    model_name: str = "local-multilingual-v2"
    audio_duration_sec: float = 0.0


class STTProvider(abc.ABC):
    """
    Abstract interface for multilingual Speech-to-Text inference providers.
    """

    @abc.abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        language_hint: Optional[str] = None,
        profile: STTModelProfile = STTModelProfile.BALANCED,
    ) -> STTResult:
        """
        Transcribes raw PCM / WAV mono audio bytes into text with confidence metrics.
        """
        pass

    @abc.abstractmethod
    async def warmup(self, profile: STTModelProfile = STTModelProfile.BALANCED) -> bool:
        """
        Warms up the STT model weights in memory before active demo or production calls.
        """
        pass

    @abc.abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Returns model architecture, loaded status, memory footprint, and hardware device.
        """
        pass
