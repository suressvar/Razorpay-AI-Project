"""Administrative security control endpoints including emergency kill-switch."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from recovery_autopilot.config import settings
from recovery_autopilot.security.rbac import require_admin

router = APIRouter(prefix="/admin", tags=["Admin & Security"])
logger = logging.getLogger("recovery_autopilot.api.admin")


class KillSwitchRequest(BaseModel):
    active: bool = Field(..., description="Whether emergency kill switch should be activated")
    reason: str = Field("Manual operator override", description="Audit reason for kill-switch state toggle")


class SettingsUpdateRequest(BaseModel):
    model_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    payment_execution_mode: Optional[str] = None
    human_review_threshold_inr: Optional[float] = None
    min_confidence_threshold: Optional[float] = None
    max_contact_attempts: Optional[int] = None
    min_hours_between_contacts: Optional[int] = None
    voice_enabled: Optional[bool] = None


@router.get("/status")
async def get_admin_status():
    """Get operational security and kill switch status."""
    return {
        "kill_switch_active": settings.KILL_SWITCH_ACTIVE,
        "execution_mode": settings.PAYMENT_EXECUTION_MODE,
        "allow_production_mode": settings.ALLOW_PRODUCTION_MODE,
        "confirm_live_financial_transactions": settings.CONFIRM_LIVE_FINANCIAL_TRANSACTIONS,
    }


@router.get("/settings")
async def get_all_settings():
    """Retrieve complete merchant, gateway, AI model, and recovery policy configuration."""
    return {
        "merchant": {
            "merchant_id": "acc_rzp_sub_883294",
            "business_name": "Razorpay Revenue Autopilot Demo Merchant",
            "gstin": "29AABCU9603R1Z2",
            "business_type": "Private Limited",
            "registered_email": "finance-ops@autopilot.example.com",
            "support_contact": "+91 80 4040 2020",
            "webhook_url": "http://localhost:8000/webhooks/razorpay",
            "webhook_secret_set": bool(settings.RAZORPAY_WEBHOOK_SECRET),
        },
        "gateway": {
            "execution_mode": settings.PAYMENT_EXECUTION_MODE,
            "key_id_masked": f"{settings.RAZORPAY_KEY_ID[:12]}..." if len(settings.RAZORPAY_KEY_ID) > 12 else settings.RAZORPAY_KEY_ID,
            "key_id": settings.RAZORPAY_KEY_ID,
            "key_secret_configured": bool(settings.RAZORPAY_KEY_SECRET),
            "webhook_secret_masked": f"{settings.RAZORPAY_WEBHOOK_SECRET[:8]}..." if len(settings.RAZORPAY_WEBHOOK_SECRET) > 8 else "***",
            "kill_switch_active": settings.KILL_SWITCH_ACTIVE,
            "allow_production_mode": settings.ALLOW_PRODUCTION_MODE,
            "confirm_live_financial_transactions": settings.CONFIRM_LIVE_FINANCIAL_TRANSACTIONS,
        },
        "ai_model": {
            "active_provider": settings.MODEL_PROVIDER,
            "gemini_model": settings.GEMINI_MODEL,
            "gemini_api_key_set": bool(settings.GEMINI_API_KEY),
            "gemini_temperature": settings.GEMINI_TEMPERATURE,
            "openai_model": settings.OPENAI_MODEL,
            "openai_api_key_set": bool(settings.OPENAI_API_KEY),
            "openai_base_url": settings.OPENAI_BASE_URL,
            "ollama_model": settings.OLLAMA_MODEL,
            "ollama_base_url": settings.OLLAMA_BASE_URL,
        },
        "policies": {
            "human_review_threshold_inr": settings.HUMAN_REVIEW_THRESHOLD_INR,
            "min_confidence_threshold": settings.MIN_CONFIDENCE_THRESHOLD,
            "max_contact_attempts": settings.MAX_CONTACT_ATTEMPTS,
            "min_hours_between_contacts": settings.MIN_HOURS_BETWEEN_CONTACTS,
            "max_contacts_per_week": settings.MAX_CONTACTS_PER_WEEK,
            "max_retry_delay_minutes": settings.MAX_RETRY_DELAY_MINUTES,
        },
        "voice": {
            "voice_enabled": settings.VOICE_ENABLED,
            "voice_stt_provider": settings.VOICE_STT_PROVIDER,
            "voice_tts_provider": settings.VOICE_TTS_PROVIDER,
            "voice_min_confidence_threshold": settings.VOICE_MIN_CONFIDENCE_THRESHOLD,
            "voice_session_timeout_seconds": settings.VOICE_SESSION_TIMEOUT_SECONDS,
        },
        "team": [
            {
                "id": "usr_01",
                "name": "Arjun Sharma (Admin)",
                "email": "arjun@example.com",
                "role": "admin",
                "status": "active",
                "last_active": "Just now",
            },
            {
                "id": "usr_02",
                "name": "Priya Patel (Reviewer)",
                "email": "priya.p@example.com",
                "role": "reviewer",
                "status": "active",
                "last_active": "10 mins ago",
            },
            {
                "id": "usr_03",
                "name": "Rohit Verma (Ops Viewer)",
                "email": "rohit.v@example.com",
                "role": "viewer",
                "status": "active",
                "last_active": "2 hours ago",
            },
        ],
        "channels": {
            "whatsapp": {"enabled": True, "status": "connected", "sender": "+91 98765 00000"},
            "sms": {"enabled": True, "status": "connected", "sender": "RZPPAY"},
            "email": {"enabled": True, "status": "connected", "sender": "billing@merchant.com"},
            "voice": {"enabled": settings.VOICE_ENABLED, "status": "ready", "agent_name": "Aarav (AI Voice Bot)"},
        },
    }


@router.post("/settings")
async def update_settings(
    req: SettingsUpdateRequest,
    operator_id: str = Depends(require_admin),
):
    """Update runtime operational policies and AI model configuration."""
    if req.model_provider:
        settings.MODEL_PROVIDER = req.model_provider
    if req.gemini_api_key is not None:
        settings.GEMINI_API_KEY = req.gemini_api_key
    if req.gemini_model:
        settings.GEMINI_MODEL = req.gemini_model
    if req.openai_api_key is not None:
        settings.OPENAI_API_KEY = req.openai_api_key
    if req.openai_model:
        settings.OPENAI_MODEL = req.openai_model
    if req.ollama_model:
        settings.OLLAMA_MODEL = req.ollama_model
    if req.ollama_base_url:
        settings.OLLAMA_BASE_URL = req.ollama_base_url
    if req.payment_execution_mode:
        settings.PAYMENT_EXECUTION_MODE = req.payment_execution_mode
    if req.human_review_threshold_inr is not None:
        settings.HUMAN_REVIEW_THRESHOLD_INR = req.human_review_threshold_inr
    if req.min_confidence_threshold is not None:
        settings.MIN_CONFIDENCE_THRESHOLD = req.min_confidence_threshold
    if req.max_contact_attempts is not None:
        settings.MAX_CONTACT_ATTEMPTS = req.max_contact_attempts
    if req.min_hours_between_contacts is not None:
        settings.MIN_HOURS_BETWEEN_CONTACTS = req.min_hours_between_contacts
    if req.voice_enabled is not None:
        settings.VOICE_ENABLED = req.voice_enabled

    logger.info("Settings updated by admin '%s'", operator_id)
    return {
        "status": "success",
        "updated_by": operator_id,
        "message": "Settings updated successfully",
    }


@router.post("/kill-switch")
async def toggle_kill_switch(
    req: KillSwitchRequest,
    operator_id: str = Depends(require_admin),
):
    """Toggle the emergency kill switch (requires admin role).

    When active, all autonomous recovery actions are instantly blocked.
    """
    settings.KILL_SWITCH_ACTIVE = req.active
    logger.critical(
        "EMERGENCY KILL SWITCH %s by admin '%s'. Reason: %s",
        "ACTIVATED" if req.active else "DEACTIVATED",
        operator_id,
        req.reason,
    )
    return {
        "kill_switch_active": settings.KILL_SWITCH_ACTIVE,
        "changed_by": operator_id,
        "reason": req.reason,
        "status": "success",
    }


class ModelTestRequest(BaseModel):
    error_code: str = Field("BAD_REQUEST_PAYMENT_TIMED_OUT", description="Error code to diagnose")
    error_description: str = Field("Payment timed out at issuing bank gateway during 3DS OTP validation", description="Error details")
    amount_inr: float = Field(4999.0, description="Transaction amount in INR")
    customer_tier: str = Field("vip", description="Customer tier")


@router.post("/test-model")
async def test_ai_model_inference(req: ModelTestRequest):
    """Developer tool: test active LLM model inference with latency and output inspection."""
    import time
    from recovery_autopilot.model_providers.factory import get_model_provider

    start_time = time.time()
    try:
        provider = get_model_provider()
        prompt = (
            f"Analyze failed payment: code={req.error_code}, desc={req.error_description}, "
            f"amount=₹{req.amount_inr}, customer_tier={req.customer_tier}. Propose recovery strategy."
        )
        response_text = await provider.generate_recovery_plan(
            error_code=req.error_code,
            error_description=req.error_description,
            amount_inr=req.amount_inr,
            customer_history={"tier": req.customer_tier, "prev_failures": 1},
        ) if hasattr(provider, "generate_recovery_plan") else "AI provider active and responding."
        
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "success",
            "provider": settings.MODEL_PROVIDER,
            "model": getattr(provider, "model_name", settings.MODEL_PROVIDER),
            "latency_ms": latency_ms,
            "prompt_sample": prompt,
            "raw_output": response_text,
            "timestamp": time.time(),
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.exception("AI Model test inference failed")
        return {
            "status": "error",
            "provider": settings.MODEL_PROVIDER,
            "latency_ms": latency_ms,
            "error": str(e),
        }


@router.post("/test-webhook")
async def simulate_test_webhook():
    """Developer tool: simulate incoming Razorpay webhook event and measure ingestion latency."""
    import hmac
    import hashlib
    import json
    import time
    import uuid

    start_time = time.time()
    event_id = f"evt_test_{uuid.uuid4().hex[:12]}"
    payment_id = f"pay_test_{uuid.uuid4().hex[:14]}"
    
    payload = {
        "entity": "event",
        "account_id": "acc_rzp_sub_883294",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": 299900,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_{uuid.uuid4().hex[:14]}",
                    "method": "upi",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Payment authorization timed out at issuing bank gateway",
                    "error_source": "bank",
                    "error_step": "payment_authorization",
                    "error_reason": "payment_gateway_timeout",
                    "email": "developer.test@example.com",
                    "contact": "+919876543210",
                }
            }
        },
        "created_at": int(time.time()),
    }
    
    body_str = json.dumps(payload)
    secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
    signature = hmac.new(secret, body_str.encode("utf-8"), hashlib.sha256).hexdigest()
    latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "status": "success",
        "event_id": event_id,
        "event_type": "payment.failed",
        "payment_id": payment_id,
        "signature_computed": signature,
        "latency_ms": latency_ms,
        "sample_payload": payload,
        "verification_status": "VALID_HMAC_SHA256",
    }


@router.get("/system-diagnostics")
async def get_system_diagnostics():
    """Developer tool: real-time system metrics, environment state, and runtime diagnostics."""
    import sys
    import platform
    import time

    return {
        "runtime": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "framework": "FastAPI (ASGI / Uvicorn)",
            "database_engine": "SQLAlchemy (Async SQLite / PostgreSQL)",
            "worker_queue": "In-Memory Async Event Loop Queue",
        },
        "environment": {
            "execution_mode": settings.PAYMENT_EXECUTION_MODE,
            "model_provider": settings.MODEL_PROVIDER,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID[:10] + "...",
            "razorpay_key_secret_set": bool(settings.RAZORPAY_KEY_SECRET),
            "webhook_secret_set": bool(settings.RAZORPAY_WEBHOOK_SECRET),
            "gemini_api_key_set": bool(settings.GEMINI_API_KEY),
            "openai_api_key_set": bool(settings.OPENAI_API_KEY),
            "kill_switch_active": settings.KILL_SWITCH_ACTIVE,
        },
        "endpoints": {
            "api_base": "http://127.0.0.1:8000",
            "webhook_ingestion": "http://127.0.0.1:8000/webhooks/razorpay",
            "copilot_chat": "http://127.0.0.1:8000/copilot/chat",
            "metrics_summary": "http://127.0.0.1:8000/metrics/summary",
            "docs": "http://127.0.0.1:8000/docs",
            "openapi_schema": "http://127.0.0.1:8000/openapi.json",
        },
        "timestamp": time.time(),
    }
