"""
FastAPI Routes for Multilingual Voice Recovery Experience.
Supports English plus 6 Indian languages, AudioWorklet PCM ingestion, typed STT inference,
and Real-Time Diagnostic Telemetry.
"""
import base64
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.config import get_settings
from recovery_autopilot.persistence.database import get_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.voice.evaluator import VoiceRecoveryEvaluator
from recovery_autopilot.voice.stt import get_stt_provider
from recovery_autopilot.voice.tts import (
    PronunciationBenchmarkRunner,
    TTSModelTier,
    TTSRequest as CoreTTSRequest,
    VOICE_REGISTRY,
    get_tts_provider,
)
from recovery_autopilot.voice.tts.review_gallery import GalleryRating, gallery_store
from recovery_autopilot.voice.voice_models import (
    AudioDiagnostics,
    LanguageDetected,
    STTModelProfile,
    VoiceScenarioPreset,
)
from recovery_autopilot.voice.voice_session import VOICE_SCENARIOS, VoiceSessionManager

router = APIRouter(prefix="/voice", tags=["Voice Recovery Agent"])

# Global provider instances with real neural models preferred
stt_engine = get_stt_provider(prefer_real=True)
tts_engine = get_tts_provider(prefer_neural=True)
benchmark_runner = PronunciationBenchmarkRunner()



class SynthesizeTTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to synthesize")
    language: LanguageDetected = Field(LanguageDetected.ENGLISH, description="Target language")
    voice_id: Optional[str] = Field(None, description="Optional voice ID override")
    rate: float = Field(1.0, ge=0.5, le=2.0, description="Speaking rate")
    pitch: float = Field(1.0, ge=0.5, le=1.5, description="Pitch factor")
    tier: TTSModelTier = Field(TTSModelTier.HIGH_QUALITY, description="TTS model tier")
    use_ssml: bool = Field(False, description="Whether to include SSML prosody tags")


class StartVoiceSessionRequest(BaseModel):
    case_id: str = Field(..., description="Target PaymentCase ID")
    language_hint: LanguageDetected = Field(
        LanguageDetected.ENGLISH,
        description="Customer's preferred speech language",
    )


class ConsentRequest(BaseModel):
    consent_granted: bool = Field(..., description="True if customer agrees to voice conversation")


class UtteranceRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Speech text or transcribed customer utterance")
    language_hint: Optional[LanguageDetected] = Field(None, description="BCP-47-aligned language selection")
    transcription_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class AudioUtteranceRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded 16kHz mono PCM or WAV audio bytes")
    language_hint: Optional[LanguageDetected] = Field(None, description="Preferred language hint")
    profile: STTModelProfile = Field(STTModelProfile.BALANCED, description="Inference model profile")
    client_diagnostics: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EscalateRequest(BaseModel):
    reason: Optional[str] = Field("Customer request or policy trigger", description="Escalation reason")


@router.get("/scenarios", response_model=List[VoiceScenarioPreset])
async def list_voice_scenarios():
    """Returns curated demo scenarios for Buildathon judges and interactive testing."""
    return VOICE_SCENARIOS


@router.get("/evaluation", response_model=Dict[str, Any])
async def get_voice_evaluation():
    """Runs the synthetic multilingual benchmark suite and returns intent accuracy, F1, and safety stats."""
    evaluator = VoiceRecoveryEvaluator()
    results = await evaluator.run_evaluation()
    return results


@router.get("/stt/info", response_model=Dict[str, Any])
async def get_stt_info():
    """Returns loaded STT architecture, hardware device, and supported language models."""
    return stt_engine.get_model_info()


@router.post("/stt/warmup", response_model=Dict[str, Any])
async def warmup_stt(profile: STTModelProfile = STTModelProfile.BALANCED):
    """Pre-allocates buffers and warms local STT inference caches."""
    success = await stt_engine.warmup(profile)
    return {"status": "warmed", "profile": profile.value, "success": success}


@router.post("/sessions/start", response_model=Dict[str, Any])
async def start_voice_session(
    req: StartVoiceSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initializes a new interactive multilingual voice recovery session for a given case."""
    settings = get_settings()
    if not settings.VOICE_ENABLED:
        raise HTTPException(status_code=403, detail="Voice Recovery Agent is disabled in settings (VOICE_ENABLED=false)")

    repo = SqlAlchemyRepository(db)
    case = await repo.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {req.case_id} not found")

    manager = VoiceSessionManager(repo)
    session = await manager.start_session(case, req.language_hint)
    return session.to_dict()


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_voice_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetches full state, multi-turn transcripts, and promises for a voice session."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Voice session {session_id} not found")
    return session.to_dict()


@router.post("/sessions/{session_id}/consent", response_model=Dict[str, Any])
async def set_session_consent(
    session_id: str,
    req: ConsentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Records customer consent before initiating active recovery dialogue."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        session = await manager.grant_consent(session_id, req.consent_granted)
        return session.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/sessions/{session_id}/utterance", response_model=Dict[str, Any])
async def process_utterance(
    session_id: str,
    req: UtteranceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Processes spoken customer utterance text, executes guardrails, and produces localized agent response."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        session, analysis = await manager.process_customer_utterance(
            session_id,
            req.text,
            language_hint=req.language_hint,
            transcription_confidence=req.transcription_confidence,
        )
        return {
            "session": session.to_dict(),
            "latest_analysis": analysis.model_dump(mode="json"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(exc)}")


@router.post("/sessions/{session_id}/audio", response_model=Dict[str, Any])
async def process_audio_utterance(
    session_id: str,
    req: AudioUtteranceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Processes raw AudioWorklet PCM audio bytes, runs local STT, and returns full diagnostic telemetry."""
    start_total_t = time.perf_counter()
    try:
        audio_bytes = base64.b64decode(req.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio payload")

    # Transcribe audio using STT provider
    stt_res = await stt_engine.transcribe(
        audio_bytes,
        language_hint=req.language_hint.value if req.language_hint else None,
        profile=req.profile,
    )

    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        effective_text = stt_res.transcript if stt_res.transcript else "(unintelligible audio)"
        session, analysis = await manager.process_customer_utterance(
            session_id,
            effective_text,
            language_hint=req.language_hint,
            transcription_confidence=stt_res.confidence,
        )

        total_latency = (time.perf_counter() - start_total_t) * 1000.0

        diagnostics = AudioDiagnostics(
            microphone_name=req.client_diagnostics.get("microphone_name", "Default Microphone"),
            input_sample_rate=req.client_diagnostics.get("input_sample_rate", 16000),
            processed_sample_rate=16000,
            recording_duration_sec=req.client_diagnostics.get("recording_duration_sec", stt_res.audio_duration_sec),
            speech_duration_sec=stt_res.audio_duration_sec,
            signal_level_rms=req.client_diagnostics.get("signal_level_rms", 0.0),
            peak_amplitude=req.client_diagnostics.get("peak_amplitude", 0.0),
            is_clipped=req.client_diagnostics.get("is_clipped", False),
            detected_language=analysis.detected_language.value,
            transcription_confidence=stt_res.confidence,
            latency_ms=round(total_latency, 2),
            raw_transcript=stt_res.transcript,
            normalized_transcript=analysis.transcript_meta.normalized_transcript if analysis.transcript_meta else stt_res.transcript,
            extracted_intent=analysis.detected_intent.value,
        )

        return {
            "session": session.to_dict(),
            "latest_analysis": analysis.model_dump(mode="json"),
            "stt_result": stt_res.model_dump(mode="json"),
            "diagnostics": diagnostics.model_dump(mode="json"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Voice audio processing failed: {str(exc)}")


@router.post("/sessions/{session_id}/confirm", response_model=Dict[str, Any])
async def confirm_session_action(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Executes confirmed recovery action (Razorpay payment link or Promise to Pay registration)."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        session, result_meta = await manager.confirm_action_or_promise(session_id)
        return {
            "session": session.to_dict(),
            "result": result_meta,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/sessions/{session_id}/escalate", response_model=Dict[str, Any])
async def escalate_voice_session(
    session_id: str,
    req: EscalateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transfers the voice session and underlying case to human operator approval queue."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        session = await manager.escalate_to_human(session_id, req.reason or "Customer request")
        return session.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/sessions/{session_id}/transcript", response_model=Dict[str, Any])
async def delete_voice_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Privacy feature: Permanently purges customer voice transcript from database."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    success = await manager.delete_transcript(session_id)
    return {"session_id": session_id, "deleted": success, "message": "Transcript permanently purged"}


@router.post("/sessions/{session_id}/interrupt", response_model=Dict[str, Any])
async def interrupt_voice_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Halts ongoing agent voice playback and transitions session back into active listening."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        session = await manager.interrupt(session_id)
        return {"status": "interrupted", "session": session.to_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


class TextCorrectionRequest(BaseModel):
    corrected_text: str = Field(..., min_length=1, description="Customer-corrected text")
    field_name: Optional[str] = Field(None, description="Optional target field, e.g. amount, date, phone")


@router.post("/sessions/{session_id}/correct-text", response_model=Dict[str, Any])
async def correct_session_text(
    session_id: str,
    req: TextCorrectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Applies customer text correction or text fallback when acoustic speech is misheard."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        session = await manager.apply_text_correction(session_id, req.corrected_text, req.field_name)
        return {"status": "corrected", "session": session.to_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------
# Multilingual Text-to-Speech (TTS) Endpoints

# ---------------------------------------------------------

@router.get("/tts/voices", response_model=List[Dict[str, Any]])
async def list_tts_voices(language: Optional[LanguageDetected] = None):
    """Returns available localized voice profiles across Indian English and 6 regional languages."""
    from dataclasses import asdict
    voices = tts_engine.get_available_voices(language)
    return [asdict(v) for v in voices]


@router.post("/tts/synthesize", response_model=Dict[str, Any])
async def synthesize_tts_audio(req: SynthesizeTTSRequest):
    """Synthesizes text through locale-aware speech normalization and returns audio WAV payload."""
    core_req = CoreTTSRequest(
        text=req.text,
        language=req.language,
        voice_id=req.voice_id,
        rate=req.rate,
        pitch=req.pitch,
        tier=req.tier,
        use_ssml=req.use_ssml,
    )
    result = await tts_engine.synthesize(core_req)
    return {
        "audio_base64": result.audio_base64,
        "audio_format": result.audio_format,
        "sample_rate": result.sample_rate,
        "duration_sec": result.duration_sec,
        "text_spoken": result.text_spoken,
        "ssml_used": result.ssml_used,
        "language": result.language.value,
        "voice_id": result.voice_id,
        "tier": result.tier.value,
        "metadata": result.metadata,
    }


@router.get("/tts/benchmark", response_model=Dict[str, Any])
async def get_tts_benchmark():
    """Runs the 84-case pronunciation benchmark suite across all 7 Indian languages and returns sample audio gallery."""
    results = await benchmark_runner.run_benchmark()
    return results


# ---------------------------------------------------------
# Demo Reliability Mode & Pre-Flight Self-Test Endpoints
# ---------------------------------------------------------

@router.get("/demo/readiness", response_model=Dict[str, Any])
@router.post("/demo/readiness", response_model=Dict[str, Any])
async def check_demo_readiness():
    """Runs pre-flight self-tests across STT, TTS, memory, and safety locks for Buildathon demonstration."""
    from recovery_autopilot.voice.readiness import VoiceReadinessChecker
    checker = VoiceReadinessChecker()
    report = await checker.run_readiness_audit()
    return report


# ---------------------------------------------------------
# Audio Review Gallery & Evaluator Rating Endpoints
# ---------------------------------------------------------

@router.get("/gallery", response_model=List[Dict[str, Any]])
async def get_audio_review_gallery():
    """Returns audio review gallery items enriched with real native-speaker review evaluations."""
    return gallery_store.get_gallery_items()


@router.post("/gallery/rate", response_model=Dict[str, Any])
async def submit_gallery_rating(rating: GalleryRating):
    """Submits an authentic evaluator review rating (1-5 scale) with evaluator identity."""
    return gallery_store.record_rating(rating)


@router.get("/gallery/{item_id}/audio")
async def get_gallery_sample_audio(item_id: str):
    """Generates genuine speech audio for a gallery sample in its native language."""
    items = gallery_store.get_gallery_items()
    sample = next((it for it in items if it["id"] == item_id), None)
    if not sample:
        raise HTTPException(status_code=404, detail=f"Gallery sample {item_id} not found")

    lang_map = {
        "hi-IN": LanguageDetected.HINDI,
        "en-IN": LanguageDetected.ENGLISH,
        "kn-IN": LanguageDetected.KANNADA,
        "ta-IN": LanguageDetected.TAMIL,
        "te-IN": LanguageDetected.TELUGU,
        "mr-IN": LanguageDetected.MARATHI,
        "bn-IN": LanguageDetected.BENGALI,
    }
    lang = lang_map.get(sample["language"], LanguageDetected.ENGLISH)
    req = CoreTTSRequest(text=sample["text"], language=lang, voice_id=sample.get("voice_id"))
    res = await tts_engine.synthesize(req)
    return {
        "item_id": item_id,
        "language": sample["language"],
        "voice_id": res.voice_id,
        "audio_base64": res.audio_base64,
        "audio_format": res.audio_format,
        "text_spoken": res.text_spoken,
        "duration_sec": res.duration_sec,
    }

