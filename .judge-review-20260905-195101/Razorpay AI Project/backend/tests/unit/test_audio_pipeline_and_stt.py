"""
Unit tests for STT Provider Architecture, PCM Audio Decoding, and Hardware Profiles.
"""
import io
import struct
import wave
import pytest

from recovery_autopilot.voice.stt.local_provider import LocalMultilingualSTTProvider
from recovery_autopilot.voice.voice_models import STTModelProfile


def _generate_synthetic_pcm_wav(num_samples: int = 16000, amplitude: int = 10000) -> bytes:
    """Generates synthetic 16-bit mono 16kHz WAV audio bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        # 440Hz sine wave approximations
        frames = bytearray()
        for i in range(num_samples):
            val = int(amplitude * (1 if (i // 20) % 2 == 0 else -1))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_stt_provider_warmup_and_profiles():
    provider = LocalMultilingualSTTProvider()

    info = provider.get_model_info()
    assert info["provider"] == "LocalMultilingualSTTProvider"
    assert info["is_warmed_up"] is False

    # Warmup balanced
    warmed = await provider.warmup(STTModelProfile.BALANCED)
    assert warmed is True
    assert provider.is_warmed_up is True

    # Warmup fast
    warmed_fast = await provider.warmup(STTModelProfile.FAST)
    assert warmed_fast is True
    assert provider.get_model_info()["active_profile"] == "fast"


@pytest.mark.asyncio
async def test_pcm_audio_validation_and_transcription():
    provider = LocalMultilingualSTTProvider()
    await provider.warmup()

    # Valid audio
    wav_bytes = _generate_synthetic_pcm_wav(num_samples=16000, amplitude=12000)
    res = await provider.transcribe(wav_bytes, language_hint="hi-IN", profile=STTModelProfile.BALANCED)

    assert res.transcript != ""
    assert res.confidence > 0.8
    assert res.audio_duration_sec == 1.0
    assert len(res.word_timestamps) > 0

    # Silent / Too short audio
    empty_bytes = b"\x00" * 20
    empty_res = await provider.transcribe(empty_bytes, language_hint="en-IN")
    assert empty_res.confidence == 0.0
    assert empty_res.transcript == ""


@pytest.mark.asyncio
async def test_clipping_detection_in_audio_frames():
    provider = LocalMultilingualSTTProvider()

    # Clipped audio (amplitude > 32700)
    clipped_wav = _generate_synthetic_pcm_wav(num_samples=8000, amplitude=32750)
    audio_info = provider._parse_and_validate_audio(clipped_wav)

    assert audio_info["clipped"] is True
    assert audio_info["peak"] >= 32700
