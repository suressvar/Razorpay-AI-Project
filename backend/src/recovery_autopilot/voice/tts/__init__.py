"""
Multilingual Text-to-Speech (TTS) Engine Package for Razorpay Recovery Autopilot.
"""
from recovery_autopilot.voice.tts.provider_base import (
    BaseTTSProvider,
    TTSAudioResult,
    TTSModelTier,
    TTSRequest,
    VoiceGender,
    VoiceProfile,
)
from recovery_autopilot.voice.tts.local_tts_provider import (
    LocalMultilingualTTSProvider,
    VOICE_REGISTRY,
)
from recovery_autopilot.voice.tts.neural_tts_provider import (
    NEURAL_VOICE_REGISTRY,
    NeuralMultilingualTTSProvider,
)
from recovery_autopilot.voice.tts.tts_normalization import (
    LocaleSpeechRenderer,
    number_to_indian_english_words,
    number_to_hindi_words,
)


def get_tts_provider(prefer_neural: bool = True) -> BaseTTSProvider:
    """Returns neural TTS provider if available, otherwise local acoustic provider."""
    if prefer_neural:
        try:
            return NeuralMultilingualTTSProvider()
        except Exception:
            pass
    return LocalMultilingualTTSProvider()

from recovery_autopilot.voice.tts.lexicon import (
    FINTECH_TERMINOLOGY,
    INDIAN_BANKS,
    CUSTOMER_NAMES_PHONETIC,
    generate_ssml,
)
from recovery_autopilot.voice.tts.pronunciation_benchmark import (
    PronunciationBenchmarkRunner,
    PronunciationTestCase,
    BENCHMARK_DATASET,
)

__all__ = [
    "BaseTTSProvider",
    "TTSAudioResult",
    "TTSModelTier",
    "TTSRequest",
    "VoiceGender",
    "VoiceProfile",
    "LocalMultilingualTTSProvider",
    "VOICE_REGISTRY",
    "NeuralMultilingualTTSProvider",
    "NEURAL_VOICE_REGISTRY",
    "get_tts_provider",
    "LocaleSpeechRenderer",

    "number_to_indian_english_words",
    "number_to_hindi_words",
    "FINTECH_TERMINOLOGY",
    "INDIAN_BANKS",
    "CUSTOMER_NAMES_PHONETIC",
    "generate_ssml",
    "PronunciationBenchmarkRunner",
    "PronunciationTestCase",
    "BENCHMARK_DATASET",
]
