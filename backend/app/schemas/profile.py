from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GoalInfo(BaseModel):
    title: str
    description: str | None = None


class SpeakingContextInfo(BaseModel):
    title: str
    description: str | None = None


class UserProfileResponse(BaseModel):
    name: str | None = None
    bio: str | None = None
    goal: GoalInfo | None = None
    contexts: SpeakingContextInfo | None = None
    notes: str | None = None
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    name: str | None = Field(default=None)
    bio: str | None = Field(default=None)
    goal: GoalInfo | None = Field(default=None)
    contexts: SpeakingContextInfo | None = Field(default=None)
    notes: str | None = Field(default=None)
