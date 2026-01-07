from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.auth.workos import verify_workos_jwt
from app.config import get_settings


@dataclass(frozen=True)
class IdentityClaims:
    """Enterprise identity claims from WorkOS AuthKit."""
    subject: str
    provider: Literal["workos"] = "workos"
    email: str | None = None
    org_id: str | None = None  # Required for enterprise access
    raw_claims: dict[str, Any] | None = None


class IdentityTokenError(Exception):
    pass


async def verify_identity_token(token: str) -> IdentityClaims:
    """
    Verify a WorkOS AuthKit access token and return identity claims.

    Enterprise backend only accepts WorkOS tokens.
    """
    settings = get_settings()

    # Development-only shortcut: accept the literal "dev_token" for local development.
    if token == "dev_token" and getattr(settings, "is_development", False):
        return IdentityClaims(
            provider="workos",
            subject="dev_user_123",
            email="dev@example.com",
            org_id="dev_org_123",
            raw_claims={"sub": "dev_user_123", "email": "dev@example.com", "org_id": "dev_org_123"},
        )

    # Verify WorkOS JWT
    claims = await verify_workos_jwt(token)
    subject = str(claims.get("sub") or "")
    if not subject:
        raise IdentityTokenError("Token missing subject")

    org_id = claims.get("org_id")
    if not org_id:
        raise IdentityTokenError("Enterprise token missing org_id claim")

    return IdentityClaims(
        provider="workos",
        subject=subject,
        email=claims.get("email"),
        org_id=org_id,
        raw_claims=claims,
    )
