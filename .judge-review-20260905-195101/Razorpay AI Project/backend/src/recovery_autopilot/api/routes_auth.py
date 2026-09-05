"""Authentication endpoints for operator login, token generation, and identity verification."""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from recovery_autopilot.security.auth import (
    AuthenticatedUser,
    TOKEN_REGISTRY,
    authenticate_credentials,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    operator_id: str
    name: str
    expires_in: int = 604800  # 7 days


@router.post("/login", response_model=LoginResponse)
async def login_operator(req: LoginRequest):
    """Authenticate operator credentials and issue a verified server-side session token."""
    user = authenticate_credentials(username=req.username, password=req.password)
    return LoginResponse(
        access_token=user.token,
        role=user.role,
        operator_id=user.user_id,
        name=user.name,
    )


@router.get("/me", response_model=Dict[str, str])
async def get_current_operator(user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve authenticated operator identity and permissions."""
    return {
        "operator_id": user.user_id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
    }


@router.post("/logout")
async def logout_operator(user: AuthenticatedUser = Depends(get_current_user)):
    """Revoke active session token."""
    TOKEN_REGISTRY.pop(user.token, None)
    return {"status": "logged_out", "message": "Session token successfully revoked"}
