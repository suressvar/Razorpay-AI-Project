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

__all__ = [
    "STTProvider",
    "STTResult",
    "STTWordTimestamp",
    "STTAlternative",
    "LocalMultilingualSTTProvider",
]
