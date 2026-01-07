"""HTTP endpoints for user profile (personalisation)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.http.dependencies import get_current_user
from app.database import get_session
from app.domains.profile.service import ProfileService
from app.models import User
from app.schemas.profile import UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=UserProfileResponse)
async def get_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserProfileResponse:
    service = ProfileService(session)
    return await service.get_profile_response(user.id)


@router.patch("", response_model=UserProfileResponse)
async def update_profile(
    payload: UserProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserProfileResponse:
    service = ProfileService(session)
    profile = await service.upsert_profile(user.id, payload)
    return UserProfileResponse.model_validate(profile)
