"""FastAPI routes for AI Copilot assistant interactions and payment link execution."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from recovery_autopilot.persistence.database import get_db
from recovery_autopilot.services.copilot_service import copilot_service

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])


class CopilotChatRequest(BaseModel):
    """Request payload for Copilot query with optional screenshot."""

    query: str = Field(..., description="Agent or customer query text")
    image_base64: Optional[str] = Field(None, description="Base64 encoded screenshot attachment")
    image_name: Optional[str] = Field(None, description="Original filename of screenshot")
    agent_name: Optional[str] = Field("Support Agent", description="Name of logged-in support agent")


class CopilotCreatePaymentLinkRequest(BaseModel):
    """Request payload for creating a Razorpay payment link via Copilot."""

    case_id: str = Field(..., description="Target PaymentCase ID")
    amount_inr: float = Field(..., gt=0, description="Amount in INR")
    customer_email: str = Field(..., description="Recipient customer email")
    customer_phone: str = Field(..., description="Recipient customer contact number")
    expiry_date: Optional[str] = Field(None, description="Optional link expiry date string")
    note: Optional[str] = Field(None, description="Optional note visible to customer")
    agent_name: Optional[str] = Field("Support Agent", description="Name of logged-in support agent")


@router.get("", response_model=Dict[str, Any])
async def copilot_info():
    """Information endpoint for AI Copilot."""
    return {
        "service": "AI Copilot Diagnostic Assistant",
        "description": "Cross-references Razorpay payment records to diagnose failures and send payment links.",
        "frontend_ui_url": "http://localhost:5173/copilot",
        "endpoints": {
            "chat": "POST /copilot/chat",
            "create_payment_link": "POST /copilot/create-payment-link",
        },
    }


@router.post("/chat", response_model=Dict[str, Any])
async def copilot_chat(

    req: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process support inquiry or customer complaint and return diagnosis and resolution recommendations."""
    try:
        res = await copilot_service.process_chat(
            session=db,
            query=req.query,
            image_base64=req.image_base64,
            image_name=req.image_name,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Copilot diagnosis failed: {str(exc)}")


@router.post("/create-payment-link", response_model=Dict[str, Any])
async def create_copilot_payment_link(
    req: CopilotCreatePaymentLinkRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute creation of a Razorpay Payment Link for a diagnosed case with audit logging."""
    try:
        result = await copilot_service.create_payment_link(
            session=db,
            case_id=req.case_id,
            amount_inr=req.amount_inr,
            customer_email=req.customer_email,
            customer_phone=req.customer_phone,
            expiry_date=req.expiry_date,
            note=req.note,
            operator_name=getattr(req, "agent_name", None) or "Support Agent",
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create payment link: {str(exc)}")
