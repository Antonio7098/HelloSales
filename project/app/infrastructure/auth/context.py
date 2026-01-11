"""Authentication context for request handling."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.auth.workos import WorkOSAuth, get_workos_auth

security = HTTPBearer()


@dataclass
class AuthContext:
    """Authenticated user context available in request handlers."""

    user_id: UUID
    email: str
    org_id: UUID | None
    org_external_id: str | None
    role: str | None
    permissions: list[str]
    raw_token: str
    claims: dict[str, Any]

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.user_id is not None

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def require_org(self) -> UUID:
        """Get org_id or raise if not present."""
        if self.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization context required",
            )
        return self.org_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    workos: WorkOSAuth = Depends(get_workos_auth),
) -> AuthContext:
    """FastAPI dependency to get authenticated user context.

    Extracts and validates JWT from Authorization header.
    """
    try:
        claims = await workos.verify_token(credentials.credentials)

        # Extract user ID (sub claim is the WorkOS user ID)
        user_id_str = claims.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )

        # WorkOS uses string IDs, we need to handle conversion
        # For now, we'll use the auth_subject to look up our UUID later
        # The user_id here is a placeholder - actual UUID comes from our database

        # Extract organization if present
        org_id = None
        org_external_id = claims.get("org_id")

        # Extract role and permissions
        role = claims.get("role")
        permissions = claims.get("permissions", [])

        return AuthContext(
            user_id=UUID(user_id_str) if _is_uuid(user_id_str) else UUID(int=0),
            email=claims.get("email", ""),
            org_id=org_id,
            org_external_id=org_external_id,
            role=role,
            permissions=permissions,
            raw_token=credentials.credentials,
            claims=claims,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        ) from e


def _is_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False
