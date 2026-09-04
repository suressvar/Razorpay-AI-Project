"""Role-Based Access Control (RBAC) and Security Middleware for Operators."""

import enum
import logging
from typing import List, Optional

from fastapi import Header, HTTPException

logger = logging.getLogger("recovery_autopilot.security.rbac")


class OperatorRole(str, enum.Enum):
    VIEWER = "viewer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


def verify_operator_role(
    allowed_roles: List[OperatorRole],
    operator_role: Optional[str] = Header("reviewer", alias="X-Operator-Role"),
    operator_id: Optional[str] = Header("ops_default", alias="X-Operator-Id"),
) -> str:
    """Verify that the caller has one of the allowed operator roles."""
    if not operator_role:
        role_enum = OperatorRole.VIEWER
    else:
        try:
            role_enum = OperatorRole(operator_role.lower())
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail=f"Invalid operator role '{operator_role}'. Allowed roles: {[r.value for r in OperatorRole]}",
            )

    if role_enum not in allowed_roles:
        logger.warning(
            "Access denied for operator %s with role %s (required: %s)",
            operator_id,
            role_enum.value,
            [r.value for r in allowed_roles],
        )
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: role '{role_enum.value}' lacks required permissions ({[r.value for r in allowed_roles]}).",
        )

    return operator_id or "ops_default"


def require_reviewer(
    operator_role: Optional[str] = Header("reviewer", alias="X-Operator-Role"),
    operator_id: Optional[str] = Header("ops_default", alias="X-Operator-Id"),
) -> str:
    return verify_operator_role([OperatorRole.REVIEWER, OperatorRole.ADMIN], operator_role, operator_id)


def require_admin(
    operator_role: Optional[str] = Header("admin", alias="X-Operator-Role"),
    operator_id: Optional[str] = Header("ops_admin", alias="X-Operator-Id"),
) -> str:
    return verify_operator_role([OperatorRole.ADMIN], operator_role, operator_id)
