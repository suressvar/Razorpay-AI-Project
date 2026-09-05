"""
Neural Multilingual Text-to-Speech Provider powered by Edge-TTS.
Provides genuine, highly intelligible speech for:
English (en-IN), Hindi (hi-IN), Kannada (kn-IN), Tamil (ta-IN),
Telugu (te-IN), Marathi (mr-IN), and Bengali (bn-IN).
"""
from __future__ import annotations

import base64
import logging
import re
import time
from typing import Dict, List, Optional

from recovery_autopilot.voice.tts.lexicon import generate_ssml
from recovery_autopilot.voice.tts.provider_base import (
    BaseTTSProvider,
    TTSAudioResult,
    TTSModelTier,
    TTSRequest,
    VoiceGender,
    VoiceProfile,
)
from recovery_autopilot.voice.tts.tts_normalization import LocaleSpeechRenderer
from recovery_autopilot.voice.voice_models import LanguageDetected

logger = logging.getLogger("recovery_autopilot.voice.tts.neural_tts_provider")

NEURAL_VOICE_REGISTRY: List[VoiceProfile] = [
    VoiceProfile(
        voice_id="hi-IN-MadhurNeural",
        name="Madhur (हिन्दी - Neural)",
        language=LanguageDetected.HINDI,
        locale="hi-IN",
        gender=VoiceGender.MALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="High-intelligibility neural voice for Hindi subscription recovery.",
        is_native=True,
        is_mock=False,
    ),
    VoiceProfile(
        voice_id="hi-IN-SwaraNeural",
        name="Swara (हिन्दी - Neural)",
        language=LanguageDetected.HINDI,
        locale="hi-IN",
        gender=VoiceGender.FEMALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="Natural feminine neural voice for Hindi subscription recovery.",
        is_native=True,
        is_mock=False,
    ),
    VoiceProfile(
        voice_id="en-IN-NeerjaExpressiveNeural",
        name="Neerja (Indian English - Neural)",
        language=LanguageDetected.ENGLISH,
        locale="en-IN",
        gender=VoiceGender.FEMALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="Expressive Indian English neural voice with natural cadence.",
        is_native=True,
        is_mock=False,
    ),
    VoiceProfile(
        voice_id="kn-IN-GaganNeural",
        name="Gagan (ಕನ್ನಡ - Neural)",
        language=LanguageDetected.KANNADA,
        locale="kn-IN",
        gender=VoiceGender.MALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="Native Kannada neural voice for Bangalore/Karnataka merchant recovery.",
        is_native=True,
        is_mock=False,
    ),
    VoiceProfile(
        voice_id="ta-IN-PallaviNeural",
        name="Pallavi (தமிழ் - Neural)",
        language=LanguageDetected.TAMIL,
        locale="ta-IN",
        gender=VoiceGender.FEMALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="Native Tamil neural voice for Chennai/Tamil Nadu customer recovery.",
        is_native=True,
        is_mock=False,
    ),
    VoiceProfile(
        voice_id="te-IN-MohanNeural",
        name="Mohan (తెలుగు - Neural)",
        language=LanguageDetected.TELUGU,
        locale="te-IN",
        gender=VoiceGender.MALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="Native Telugu neural voice for Hyderabad/AP/Telangana recovery.",
        is_native=True,
        is_mock=False,
    ),
    VoiceProfile(
        voice_id="mr-IN-AarohiNeural",
        name="Aarohi (मराठी - Neural)",
        language=LanguageDetected.MARATHI,
        locale="mr-IN",
        gender=VoiceGender.FEMALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="Native Marathi neural voice for Mumbai/Pune customer recovery.",
        is_native=True,
        is_mock=False,
    ),
    VoiceProfile(
        voice_id="bn-IN-BashkarNeural",
        name="Bashkar (বাংলা - Neural)",
        language=LanguageDetected.BENGALI,
        locale="bn-IN",
        gender=VoiceGender.MALE,
        sample_rate=24000,
        quality_rating="Native-verified",
        description="Native Bengali neural voice for Kolkata/West Bengal customer recovery.",
        is_native=True,
        is_mock=False,
    ),
]

LANGUAGE_TO_DEFAULT_VOICE = {
    LanguageDetected.HINDI: "hi-IN-MadhurNeural",
    LanguageDetected.ENGLISH: "en-IN-NeerjaExpressiveNeural",
    LanguageDetected.KANNADA: "kn-IN-GaganNeural",
    LanguageDetected.TAMIL: "ta-IN-PallaviNeural",
    LanguageDetected.TELUGU: "te-IN-MohanNeural",
    LanguageDetected.MARATHI: "mr-IN-AarohiNeural",
    LanguageDetected.BENGALI: "bn-IN-BashkarNeural",
}


class NeuralMultilingualTTSProvider(BaseTTSProvider):
    """Production Text-to-Speech engine utilizing Microsoft Edge Neural Voices.

    Generates intelligible, human-like speech across all 7 supported Indian languages.
    """

    is_mock = False

    def __init__(self):
        self.voices = NEURAL_VOICE_REGISTRY

    def get_supported_languages(self) -> List[LanguageDetected]:
        return list(LANGUAGE_TO_DEFAULT_VOICE.keys())

    def get_available_voices(self, language: Optional[LanguageDetected] = None) -> List[VoiceProfile]:
        if language is None:
            return self.voices
        return [v for v in self.voices if v.language == language]

    def get_supported_voices(self, language: Optional[LanguageDetected] = None) -> List[VoiceProfile]:
        return self.get_available_voices(language)

    def estimate_duration(self, text: str, rate: float = 1.0) -> float:
        # Standard average speaking rate ~140 words per minute (2.3 words/sec)
        words = len(text.split())
        base_dur = max(0.5, words / 2.3)
        return round(base_dur / max(0.1, rate), 2)


    def _sanitize_for_speech(self, text: str) -> str:
        """Sanitizes text so raw URLs, IDs, and tokens are never read aloud."""
        # 1. Replace payment URLs with friendly text
        cleaned = re.sub(r"https?://\S+", "the link sent to your phone", text)
        # 2. Replace raw transaction/payment IDs (e.g. pay_981248712) with 'your payment'
        cleaned = re.sub(r"\b(pay|sub|inv|order)_[a-zA-Z0-9]+\b", "your subscription", cleaned)
        # 3. Strip any OTP-like 6-digit numbers
        cleaned = re.sub(r"\b\d{6}\b", "your security code", cleaned)
        return cleaned

    async def synthesize(self, request: TTSRequest) -> TTSAudioResult:
        """Synthesizes text into high-quality spoken audio using Edge-TTS."""
        t0 = time.perf_counter()
        target_lang = request.language or LanguageDetected.ENGLISH
        voice_id = request.voice_id or LANGUAGE_TO_DEFAULT_VOICE.get(
            target_lang, "en-IN-NeerjaExpressiveNeural"
        )

        # 1. Phonetic & Locale normalization (rupees, lakh, dates)
        display_text = request.text
        sanitized = self._sanitize_for_speech(display_text)
        speech_text = LocaleSpeechRenderer.render(sanitized, target_lang)

        try:
            import edge_tts

            comm = edge_tts.Communicate(speech_text, voice_id)
            audio_chunks = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            audio_bytes = b"".join(audio_chunks)
            if not audio_bytes:
                raise RuntimeError("Edge-TTS returned empty audio stream.")

            b64_audio = base64.b64encode(audio_bytes).decode("ascii")
            latency = (time.perf_counter() - t0) * 1000.0

            # Approximate duration based on MP3 byte size (~48kbps or ~6KB/sec)
            duration_sec = round(len(audio_bytes) / 6000.0, 2)

            return TTSAudioResult(
                audio_base64=b64_audio,
                audio_format="audio/mp3",
                sample_rate=24000,
                duration_sec=duration_sec,
                text_spoken=speech_text,
                language=target_lang,
                voice_id=voice_id,
                tier=TTSModelTier.HIGH_QUALITY,
                metadata={
                    "display_text": display_text,
                    "engine": "edge_tts_neural",
                    "latency_ms": round(latency, 1),
                    "is_mock": False,
                },
            )

        except Exception as exc:
            logger.warning("Neural TTS failed or offline (%s), falling back to local provider.", exc)
            from recovery_autopilot.voice.tts.local_tts_provider import LocalMultilingualTTSProvider

            fallback = LocalMultilingualTTSProvider()
            res = await fallback.synthesize(request)
            res.metadata["fallback_from_neural"] = True
            res.metadata["fallback_reason"] = str(exc)
            return res
