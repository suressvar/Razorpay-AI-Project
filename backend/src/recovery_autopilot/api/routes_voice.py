"""
FastAPI Routes for Consent-Based Hinglish Voice Recovery Experience.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.config import get_settings
from recovery_autopilot.persistence.database import get_db
from recovery_autopilot.persistence.repository import SqlAlchemyRepository
from recovery_autopilot.voice.evaluator import VoiceRecoveryEvaluator
from recovery_autopilot.voice.voice_models import VoiceScenarioPreset
from recovery_autopilot.voice.voice_session import VOICE_SCENARIOS, VoiceSessionManager

router = APIRouter(prefix="/voice", tags=["Voice Recovery Agent"])


class StartVoiceSessionRequest(BaseModel):
    case_id: str = Field(..., description="Target PaymentCase ID")


class ConsentRequest(BaseModel):
    consent_granted: bool = Field(..., description="True if customer agrees to voice conversation")


class UtteranceRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Speech text or transcribed customer utterance")


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


@router.post("/sessions/start", response_model=Dict[str, Any])
async def start_voice_session(
    req: StartVoiceSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initializes a new interactive Hinglish voice recovery session for a given case."""
    settings = get_settings()
    if not settings.VOICE_ENABLED:
        raise HTTPException(status_code=403, detail="Voice Recovery Agent is disabled in settings (VOICE_ENABLED=false)")

    repo = SqlAlchemyRepository(db)
    case = await repo.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {req.case_id} not found")

    manager = VoiceSessionManager(repo)
    session = await manager.start_session(case)
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
    """Processes spoken customer utterance, executes guardrails, and produces Hinglish agent response."""
    repo = SqlAlchemyRepository(db)
    manager = VoiceSessionManager(repo)
    try:
        session, analysis = await manager.process_customer_utterance(session_id, req.text)
        return {
            "session": session.to_dict(),
            "latest_analysis": analysis.model_dump(mode="json"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(exc)}")


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

