"""
Unit tests for Multilingual TTS Pipeline, Normalization, Lexicon, and Pronunciation Benchmark.
"""
import base64
import pytest
from recovery_autopilot.voice.voice_models import LanguageDetected
from recovery_autopilot.voice.tts import (
    LocalMultilingualTTSProvider,
    LocaleSpeechRenderer,
    PronunciationBenchmarkRunner,
    TTSModelTier,
    TTSRequest,
    VOICE_REGISTRY,
    generate_ssml,
    number_to_hindi_words,
    number_to_indian_english_words,
)


@pytest.fixture
def normalizer():
    return LocaleSpeechRenderer()


@pytest.fixture
def tts_engine():
    return LocalMultilingualTTSProvider()


def test_indian_number_conversion_english():
    assert number_to_indian_english_words(0) == "zero"
    assert number_to_indian_english_words(750) == "seven hundred fifty"
    assert number_to_indian_english_words(125000) == "one lakh twenty-five thousand"
    assert number_to_indian_english_words(1000000) == "ten lakh"
    assert number_to_indian_english_words(25000000) == "two crore fifty lakh"


def test_hindi_number_conversion():
    assert number_to_hindi_words(750) == "सात सौ पचास"
    assert number_to_hindi_words(125000) == "एक लाख पच्चीस हज़ार"
    assert number_to_hindi_words(1000000) == "दस लाख"


def test_currency_normalization(normalizer):
    # English
    en_res = normalizer.normalize_currency("Please pay ₹1,25,000 immediately.", LanguageDetected.ENGLISH)
    assert "one lakh twenty-five thousand rupees" in en_res

    # Hindi
    hi_res = normalizer.normalize_currency("आपका ₹1,25,000 का भुगतान बाकी है।", LanguageDetected.HINDI)
    assert "एक लाख पच्चीस हज़ार रुपये" in hi_res

    # Tamil
    ta_res = normalizer.normalize_currency("மொத்த தொகை ₹1,25,000 ஆகும்.", LanguageDetected.TAMIL)
    assert "ஒரு லட்சத்து இருபத்தைந்தாயிரம் ரூபாய்" in ta_res


def test_url_and_id_masking(normalizer):
    url_res = normalizer.normalize_urls("Check https://rzp.io/i/recovery99 for details", LanguageDetected.ENGLISH)
    assert "https://rzp.io" not in url_res
    assert "I have displayed the secure payment link" in url_res

    id_res = normalizer.normalize_payment_ids("Your payment pay_9948271 failed.")
    assert "pay_9948271" not in id_res
    assert "ending in 8 2 7 1" in id_res


def test_zero_credential_leakage(normalizer):
    secret_text = "Your OTP is 481920 and CVV is 921 with card 4111 2222 3333 4444."
    cleaned = normalizer.sanitize_credentials(secret_text)
    assert "481920" not in cleaned
    assert "921" not in cleaned
    assert "4111 2222 3333 4444" not in cleaned


def test_date_and_time_normalization(normalizer):
    date_res = normalizer.normalize_dates("Due on 05/09/2026.", LanguageDetected.ENGLISH)
    assert "September 5th, 2026" in date_res

    time_res = normalizer.normalize_times("Meeting at 7:30 PM.", LanguageDetected.ENGLISH)
    assert "7:30 PM" in time_res


def test_lexicon_phonetics(normalizer):
    text = "Use Razorpay UPI on HDFC Bank."
    en_phonetic = normalizer.apply_lexicon_phonetics(text, LanguageDetected.ENGLISH)
    assert "Razor-pay" in en_phonetic
    assert "U P I" in en_phonetic
    assert "H D F C Bank" in en_phonetic


def test_ssml_generation():
    ssml = generate_ssml("Hello customer.", LanguageDetected.ENGLISH, rate=0.95)
    assert "<speak>" in ssml
    assert 'rate="95%"' in ssml
    assert "xml:lang=\"en-IN\"" in ssml


@pytest.mark.asyncio
async def test_tts_acoustic_synthesis(tts_engine):
    req = TTSRequest(
        text="Your Razorpay payment of ₹750 is due.",
        language=LanguageDetected.ENGLISH,
        tier=TTSModelTier.HIGH_QUALITY,
    )
    result = await tts_engine.synthesize(req)
    assert result.audio_format == "audio/wav"
    assert result.duration_sec > 0.5
    assert len(result.audio_base64) > 100
    # Verify valid base64
    raw_wav = base64.b64decode(result.audio_base64)
    assert raw_wav.startswith(b"RIFF")
    assert b"WAVE" in raw_wav[:16]


@pytest.mark.asyncio
async def test_tts_regional_voices(tts_engine):
    languages = [
        LanguageDetected.ENGLISH,
        LanguageDetected.HINDI,
        LanguageDetected.KANNADA,
        LanguageDetected.TAMIL,
        LanguageDetected.TELUGU,
        LanguageDetected.MARATHI,
        LanguageDetected.BENGALI,
    ]
    for lang in languages:
        voices = tts_engine.get_available_voices(lang)
        assert len(voices) > 0
        req = TTSRequest(text="Payment received.", language=lang)
        res = await tts_engine.synthesize(req)
        assert res.language == lang
        assert len(res.audio_base64) > 0


@pytest.mark.asyncio
async def test_pronunciation_benchmark():
    runner = PronunciationBenchmarkRunner()
    benchmark_results = await runner.run_benchmark()
    assert benchmark_results["total_test_cases"] > 10
    assert benchmark_results["normalization_pass_rate"] == 100.0
    assert benchmark_results["audio_synthesis_pass_rate"] == 100.0
    assert len(benchmark_results["sample_gallery"]) > 10
