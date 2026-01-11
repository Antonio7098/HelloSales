"""Authentication endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.infrastructure.auth import AuthContext, get_current_user

router = APIRouter()


class UserInfoResponse(BaseModel):
    """Current user information response."""

    user_id: UUID
    email: str
    org_id: UUID | None
    org_external_id: str | None
    role: str | None
    permissions: list[str]

    class Config:
        from_attributes = True


class TokenClaimsResponse(BaseModel):
    """Token claims response for debugging."""

    claims: dict[str, Any]


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    auth: AuthContext = Depends(get_current_user),
) -> UserInfoResponse:
    """Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    return UserInfoResponse(
        user_id=auth.user_id,
        email=auth.email,
        org_id=auth.org_id,
        org_external_id=auth.org_external_id,
        role=auth.role,
        permissions=auth.permissions,
    )


@router.get("/claims", response_model=TokenClaimsResponse)
async def get_token_claims(
    auth: AuthContext = Depends(get_current_user),
) -> TokenClaimsResponse:
    """Get raw token claims for debugging.

    Requires valid JWT token in Authorization header.
    """
    return TokenClaimsResponse(claims=auth.claims)
