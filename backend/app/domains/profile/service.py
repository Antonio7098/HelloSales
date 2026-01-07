"""Profile service for user profile management."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserProfile
from app.schemas.profile import (
    SpeakingContextInfo,
    UserProfileResponse,
    UserProfileUpdate,
)


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: UUID) -> UserProfile | None:
        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return result.scalar_one_or_none()

    async def upsert_profile(self, user_id: UUID, data: UserProfileUpdate) -> UserProfile:
        profile = await self.get_profile(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)

        payload: dict[str, Any] = data.model_dump(exclude_unset=True)

        if "name" in payload:
            profile.name = payload["name"]

        if "bio" in payload:
            profile.bio = payload["bio"]

        if "goal" in payload:
            # payload["goal"] is already a plain dict (or None) from model_dump
            profile.goal = payload["goal"]

        if "contexts" in payload:
            # contexts is a structured object (title + description) or None
            profile.contexts = payload["contexts"]

        if "notes" in payload:
            profile.notes = payload["notes"]

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_profile_response(self, user_id: UUID) -> UserProfileResponse:
        """Return a serialisable profile model for API/WS responses.

        If the user does not yet have a stored profile, this returns a
        non-persisted "empty" profile with sensible timestamps instead of
        constructing a transient ORM object without ``created_at`` / ``updated_at``.
        """

        profile = await self.get_profile(user_id)

        # Get user's onboarding status
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        onboarding_completed = user.onboarding_completed if user else False

        if profile is None:
            now = datetime.utcnow()
            return UserProfileResponse(
                name=None,
                bio=None,
                goal=None,
                contexts=None,
                notes=None,
                onboarding_completed=onboarding_completed,
                created_at=now,
                updated_at=now,
            )

        # Handle legacy list-based contexts as well as the new structured object
        raw_contexts = profile.contexts
        speaking_context: SpeakingContextInfo | None = None

        if isinstance(raw_contexts, dict):
            title = str(raw_contexts.get("title") or "").strip()
            desc_raw = raw_contexts.get("description")
            description = (
                str(desc_raw).strip() if isinstance(desc_raw, str) and desc_raw.strip() else None
            )
            if title or description:
                speaking_context = SpeakingContextInfo(
                    title=title or "Speaking context", description=description
                )
        elif isinstance(raw_contexts, list):
            # Old shape: list of tags like ["interviews", "presentations"]
            tags = [str(c).strip() for c in raw_contexts if str(c).strip()]
            if tags:
                speaking_context = SpeakingContextInfo(title=", ".join(tags), description=None)

        return UserProfileResponse(
            name=profile.name,
            bio=profile.bio,
            goal=profile.goal,
            contexts=speaking_context,
            notes=profile.notes,
            onboarding_completed=onboarding_completed,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
