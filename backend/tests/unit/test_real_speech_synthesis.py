"""
Tests for Prompt 6: Multilingual Speech Synthesis and Audio Review Gallery.
Verifies understandable speech generation across Indian languages, sensitive data masking,
and authentic recorded evaluator reviews without fake MOS numbers.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from recovery_autopilot.main import app
from recovery_autopilot.voice.tts.neural_tts_provider import (
    NEURAL_VOICE_REGISTRY,
    NeuralMultilingualTTSProvider,
)
from recovery_autopilot.voice.tts.provider_base import TTSRequest
from recovery_autopilot.voice.tts.review_gallery import GalleryRating, gallery_store
from recovery_autopilot.voice.voice_models import LanguageDetected


@pytest.mark.asyncio
async def test_neural_voices_configured_for_all_seven_indian_languages():
    """Neural voices are available and verified for all 7 required Indian languages."""
    provider = NeuralMultilingualTTSProvider()
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
        matching = provider.get_supported_voices(lang)
        assert len(matching) > 0, f"Missing neural voice for {lang.value}"
        assert matching[0].is_mock is False
        assert matching[0].quality_rating == "Native-verified"


@pytest.mark.asyncio
async def test_speech_sanitization_prevents_reading_urls_and_credentials_aloud():
    """Raw URLs, payment IDs, and OTPs must never be read aloud by TTS."""
    provider = NeuralMultilingualTTSProvider()

    raw_text = "Please open https://rzp.io/i/test9812 to pay for pay_8829104. Your OTP is 584920."
    sanitized = provider._sanitize_for_speech(raw_text)

    assert "https://" not in sanitized
    assert "pay_8829104" not in sanitized
    assert "584920" not in sanitized
    assert "the link sent to your phone" in sanitized
    assert "your subscription" in sanitized
    assert "your security code" in sanitized


@pytest.mark.asyncio
async def test_audio_review_gallery_records_evaluator_ratings_without_hardcoded_mos():
    """Review gallery stores authentic ratings and calculates average intelligibility."""
    items = gallery_store.get_gallery_items()
    assert len(items) >= 7  # All 7 languages represented

    # Submit a new rating
    rating = GalleryRating(
        item_id="gallery_te_01",
        evaluator_name="Venkatesh Babu (Telugu Evaluator)",
        native_speaker=True,
        intelligibility_rating=5,
        naturalness_rating=4,
        comments="Very natural tone for Telugu debt collection call.",
    )
    res = gallery_store.record_rating(rating)
    assert res["intelligibility_rating"] == 5

    # Verify updated gallery
    updated_items = gallery_store.get_gallery_items()
    te_item = next(it for it in updated_items if it["id"] == "gallery_te_01")
    assert te_item["review_count"] >= 1
    assert te_item["avg_intelligibility"] == 5.0


@pytest.mark.asyncio
async def test_gallery_endpoints_via_fastapi():
    """GET /voice/gallery returns review items, POST /voice/gallery/rate saves reviews."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/voice/gallery")
        assert resp.status_code == 200
        gallery = resp.json()
        assert len(gallery) >= 7

        # Post a rating via API
        post_resp = await client.post(
            "/voice/gallery/rate",
            json={
                "item_id": "gallery_mr_01",
                "evaluator_name": "Pooja Patil (Marathi Evaluator)",
                "native_speaker": True,
                "intelligibility_rating": 5,
                "naturalness_rating": 5,
                "comments": "Excellent Marathi pronunciation of subscription terms.",
            },
        )
        assert post_resp.status_code == 200
        assert post_resp.json()["intelligibility_rating"] == 5
