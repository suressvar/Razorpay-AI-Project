"""
Tests for Prompt 5: Multilingual Speech Recognition.
Verifies genuine transcription, silence/tone rejection without fabricating transcripts,
and honest confidence/uncertainty estimation.
"""
import io
import math
import struct
import wave
import pytest

from recovery_autopilot.voice.stt.real_whisper_provider import RealWhisperSTTProvider
from recovery_autopilot.voice.voice_models import STTModelProfile


def generate_synthetic_sine_tone(duration_sec: float = 1.0, freq_hz: float = 440.0) -> bytes:
    """Generates a pure mathematical sine tone as 16-bit 16kHz mono WAV."""
    sample_rate = 16000
    num_samples = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            val = int(10000.0 * math.sin(2.0 * math.pi * freq_hz * i / sample_rate))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


def generate_synthetic_silence(duration_sec: float = 1.0) -> bytes:
    """Generates pure silence as 16-bit 16kHz mono WAV."""
    sample_rate = 16000
    num_samples = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_silence_and_tones_do_not_become_payment_requests():
    """Mathematical tones and pure silence must never be fabricated into payment requests."""
    provider = RealWhisperSTTProvider(default_profile=STTModelProfile.FAST)

    # 1. Test pure silence
    silence_wav = generate_synthetic_silence(duration_sec=1.5)
    res_silence = await provider.transcribe(silence_wav, language_hint="en")
    assert res_silence.transcript == ""
    assert res_silence.is_mock is False
    assert "WhatsApp payment link" not in res_silence.transcript

    # 2. Test sine wave tone
    tone_wav = generate_synthetic_sine_tone(duration_sec=1.0, freq_hz=880.0)
    res_tone = await provider.transcribe(tone_wav, language_hint="en")
    # Tone must either be filtered out or result in empty/non-payment text, never a fake payment proposal
    assert "WhatsApp payment link" not in res_tone.transcript


@pytest.mark.asyncio
async def test_model_warmup_and_profile_info():
    """Model warmup succeeds and honest model information is returned."""
    provider = RealWhisperSTTProvider(default_profile=STTModelProfile.FAST)
    info = provider.get_model_info()

    assert info["provider"] == "RealWhisperSTTProvider"
    assert info["is_mock"] is False
    assert info["engine_type"] == "neural_faster_whisper"
    assert "faster-whisper-tiny" in info["model_name"]
    assert "hi-IN" in info["supported_languages"]
    assert "en-IN" in info["supported_languages"]


@pytest.mark.asyncio
async def test_real_speech_recognition_produces_content_dependent_output():
    """Real speech audio produces genuine, content-dependent transcription."""
    import edge_tts

    # Generate real synthesized speech for testing
    comm = edge_tts.Communicate("I would like to pay next week.", "en-IN-NeerjaExpressiveNeural")
    chunks = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    audio_bytes = b"".join(chunks)
    assert len(audio_bytes) > 1000

    provider = RealWhisperSTTProvider(default_profile=STTModelProfile.FAST)
    result = await provider.transcribe(audio_bytes, language_hint="en")

    assert result.is_mock is False
    assert len(result.transcript) > 0
    # Must contain relevant spoken words
    transcript_lower = result.transcript.lower()
    assert any(w in transcript_lower for w in ["pay", "next", "week", "like"])
    assert "whatsapp payment link" not in transcript_lower
