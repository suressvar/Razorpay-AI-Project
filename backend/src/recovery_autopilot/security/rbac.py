"""Role-Based Access Control (RBAC) and Security Middleware for Operators.

Authority is strictly derived from authenticated server-side tokens and identity.
Request headers like X-Operator-Role cannot grant access or elevate privileges.
"""

from recovery_autopilot.security.auth import (
    AuthenticatedUser,
    OperatorRole,
    TOKEN_REGISTRY,
    authenticate_credentials,
    get_current_user,
    require_admin,
    require_reviewer,
    require_role,
    require_viewer,
)

def verify_operator_role(min_role: OperatorRole = OperatorRole.VIEWER):
    return require_role(min_role)

__all__ = [
    "OperatorRole",
    "AuthenticatedUser",
    "TOKEN_REGISTRY",
    "authenticate_credentials",
    "get_current_user",
    "require_role",
    "require_viewer",
    "require_reviewer",
    "require_admin",
    "verify_operator_role",
]

