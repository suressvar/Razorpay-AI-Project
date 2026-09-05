"""
Speech-to-Text (STT) subpackage.
"""
from recovery_autopilot.voice.stt.local_provider import LocalMultilingualSTTProvider
from recovery_autopilot.voice.stt.provider_base import (
    STTAlternative,
    STTProvider,
    STTResult,
    STTWordTimestamp,
)
from recovery_autopilot.voice.stt.real_whisper_provider import RealWhisperSTTProvider


def get_stt_provider(prefer_real: bool = True) -> STTProvider:
    """Returns the genuine Whisper STT provider if available, or falls back to mock."""
    if prefer_real:
        try:
            return RealWhisperSTTProvider()
        except Exception:
            pass
    return LocalMultilingualSTTProvider()


__all__ = [
    "STTProvider",
    "STTResult",
    "STTWordTimestamp",
    "STTAlternative",
    "LocalMultilingualSTTProvider",
    "RealWhisperSTTProvider",
    "get_stt_provider",
]

