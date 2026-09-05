"""Server-side Authentication and Operator Identity Service.

Replaces client-supplied role headers with cryptographically verified server-side identity.
Derives viewer, reviewer, and administrator permissions exclusively from verified tokens/sessions.
"""

import hashlib
import hmac
import logging
import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel

from recovery_autopilot.domain.enums import ActorType

logger = logging.getLogger("recovery_autopilot.security.auth")


class OperatorRole(str):
    VIEWER = "viewer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class AuthenticatedUser(BaseModel):
    user_id: str
    username: str
    name: str
    role: str
    token: str
    created_at: float
    expires_at: float


# Secure in-memory token registry initialized with pre-seeded operator tokens for demo/testing
TOKEN_REGISTRY: Dict[str, AuthenticatedUser] = {
    "auth_token_admin_recovery_v1": AuthenticatedUser(
        user_id="usr_admin_01",
        username="admin",
        name="Arjun Sharma (Admin)",
        role="admin",
        token="auth_token_admin_recovery_v1",
        created_at=time.time(),
        expires_at=time.time() + 86400 * 30,
    ),
    "auth_token_reviewer_recovery_v1": AuthenticatedUser(
        user_id="usr_reviewer_02",
        username="reviewer",
        name="Priya Patel (Reviewer)",
        role="reviewer",
        token="auth_token_reviewer_recovery_v1",
        created_at=time.time(),
        expires_at=time.time() + 86400 * 30,
    ),
    "auth_token_viewer_recovery_v1": AuthenticatedUser(
        user_id="usr_viewer_03",
        username="viewer",
        name="Rohit Verma (Viewer)",
        role="viewer",
        token="auth_token_viewer_recovery_v1",
        created_at=time.time(),
        expires_at=time.time() + 86400 * 30,
    ),
}

# Predefined credentials for login
OPERATOR_ACCOUNTS = {
    "admin": {
        "password_hash": hashlib.sha256("admin_recovery_demo_2026".encode()).hexdigest(),
        "user_id": "usr_admin_01",
        "name": "Arjun Sharma (Admin)",
        "role": "admin",
    },
    "reviewer": {
        "password_hash": hashlib.sha256("reviewer_recovery_demo_2026".encode()).hexdigest(),
        "user_id": "usr_reviewer_02",
        "name": "Priya Patel (Reviewer)",
        "role": "reviewer",
    },
    "viewer": {
        "password_hash": hashlib.sha256("viewer_recovery_demo_2026".encode()).hexdigest(),
        "user_id": "usr_viewer_03",
        "name": "Rohit Verma (Viewer)",
        "role": "viewer",
    },
}


def authenticate_credentials(username: str, password: str) -> AuthenticatedUser:
    """Validate username and password and generate new authenticated session token."""
    account = OPERATOR_ACCOUNTS.get(username.lower().strip())
    if not account:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expected_hash = account["password_hash"]
    given_hash = hashlib.sha256(password.encode()).hexdigest()
    if not hmac.compare_digest(expected_hash, given_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    new_token = f"tok_{secrets.token_hex(24)}"
    user = AuthenticatedUser(
        user_id=account["user_id"],
        username=username,
        name=account["name"],
        role=account["role"],
        token=new_token,
        created_at=time.time(),
        expires_at=time.time() + 86400 * 7,
    )
    TOKEN_REGISTRY[new_token] = user
    logger.info("Operator %s (%s) logged in successfully", username, account["role"])
    return user


def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
) -> AuthenticatedUser:
    """Extract and verify server-side authenticated identity.

    Strict security enforcement:
    - Never uses client role headers (e.g. X-Operator-Role) as authority.
    - Missing token -> 401 Unauthorized.
    - Invalid or expired token -> 401 Unauthorized.
    """
    token = None
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
        else:
            token = parts[0].strip()
    elif x_auth_token:
        token = x_auth_token.strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required: No valid Bearer token provided in Authorization header.",
        )

    user = TOKEN_REGISTRY.get(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token. Please log in again.",
        )

    if time.time() > user.expires_at:
        TOKEN_REGISTRY.pop(token, None)
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired. Please re-authenticate.",
        )

    return user


def require_role(allowed_roles: List[str]):
    """Factory dependency enforcing that authenticated server-side role has permission."""

    def _role_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            logger.warning(
                "Access denied for user %s (role: %s, required: %s)",
                user.username,
                user.role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: server-authenticated role '{user.role}' lacks required permissions ({allowed_roles}).",
            )
        return user

    return _role_checker


def require_viewer(user: AuthenticatedUser = Depends(require_role(["viewer", "reviewer", "admin"]))) -> str:
    """Viewer permission: permits read-only inspection."""
    return user.user_id


def require_reviewer(user: AuthenticatedUser = Depends(require_role(["reviewer", "admin"]))) -> str:
    """Reviewer permission: permits case approval, rejection, and manual workflow execution."""
    return user.user_id


def require_admin(user: AuthenticatedUser = Depends(require_role(["admin"]))) -> str:
    """Admin permission: permits setting modification, kill-switch toggle, and demo data resets."""
    return user.user_id
