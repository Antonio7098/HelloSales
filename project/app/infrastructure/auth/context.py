"""Authentication context for request handling."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.auth.workos import WorkOSAuth, get_workos_auth

security = HTTPBearer()

# Demo token storage (from auth.py)
_demo_tokens: dict[str, dict] = {}


def _register_demo_token(token: str, user_data: dict) -> None:
    """Register a demo token."""
    global _demo_tokens
    _demo_tokens[token] = user_data


def _verify_demo_token(token: str) -> dict | None:
    """Verify a demo token and return user data."""
    global _demo_tokens
    return _demo_tokens.get(token)


def _invalidate_demo_token(token: str) -> None:
    """Invalidate a demo token."""
    global _demo_tokens
    _demo_tokens.pop(token, None)


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

    Supports both WorkOS JWT tokens and demo tokens.
    """
    token = credentials.credentials

    # Try demo token first (for demo mode)
    demo_data = _verify_demo_token(token)
    if demo_data:
        user_id = UUID(demo_data.get("user_id", "00000000-0000-0000-0000-000000000000"))
        email = demo_data.get("email", "")

        return AuthContext(
            user_id=user_id,
            email=email,
            org_id=None,
            org_external_id=None,
            role=demo_data.get("role", "user"),
            permissions=[],
            raw_token=token,
            claims={"sub": str(user_id), "email": email, "demo": True},
        )

    # Otherwise, verify as WorkOS JWT token
    try:
        claims = await workos.verify_token(token)

        # Extract user ID (sub claim is the WorkOS user ID)
        user_id_str = claims.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )

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
            raw_token=token,
            claims=claims,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        ) from e


async def get_optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    workos: WorkOSAuth = Depends(get_workos_auth),
) -> AuthContext | None:
    """FastAPI dependency to optionally get authenticated user context.

    Returns None if no Authorization header is provided.
    """
    if credentials is None:
        return None

    token = credentials.credentials

    # Try demo token first
    demo_data = _verify_demo_token(token)
    if demo_data:
        user_id = UUID(demo_data.get("user_id", "00000000-0000-0000-0000-000000000000"))
        return AuthContext(
            user_id=user_id,
            email=demo_data.get("email", ""),
            org_id=None,
            org_external_id=None,
            role=demo_data.get("role", "user"),
            permissions=[],
            raw_token=token,
            claims={"sub": str(user_id), "email": demo_data.get("email", ""), "demo": True},
        )

    # Otherwise, try to verify as WorkOS JWT token
    try:
        claims = await workos.verify_token(token)

        user_id_str = claims.get("sub")
        org_id = None
        org_external_id = claims.get("org_id")
        role = claims.get("role")
        permissions = claims.get("permissions", [])

        return AuthContext(
            user_id=UUID(user_id_str) if user_id_str and _is_uuid(user_id_str) else UUID(int=0),
            email=claims.get("email", ""),
            org_id=org_id,
            org_external_id=org_external_id,
            role=role,
            permissions=permissions,
            raw_token=token,
            claims=claims,
        )

    except Exception:
        return None


def _is_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False
