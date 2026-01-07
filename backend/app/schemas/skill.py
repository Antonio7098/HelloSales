"""Pydantic schemas for skills system."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SkillLevelCriteria(BaseModel):
    """A single level's criteria and examples."""

    level: int = Field(..., ge=1, le=10)
    criteria: str
    examples: list[str] = Field(default_factory=list)


class UserSkillProgress(BaseModel):
    """User's progress on a skill (embedded in responses)."""

    current_level: int = Field(..., ge=0, le=10)
    is_tracked: bool
    track_order: int | None = None
    recent_avg_score: float | None = None


class SkillResponse(BaseModel):
    """Skill in catalog listing (without full rubric)."""

    id: UUID
    slug: str
    title: str
    description: str | None = None
    category: str | None = None
    is_tracked: bool = False
    current_level: int | None = None  # None if user never tracked this skill
    recent_avg_score: float | None = None

    class Config:
        from_attributes = True


class SkillDetailResponse(BaseModel):
    """Full skill detail including all level rubrics."""

    id: UUID
    slug: str
    title: str
    description: str | None = None
    category: str | None = None
    levels: list[SkillLevelCriteria]
    user_progress: UserSkillProgress | None = None

    class Config:
        from_attributes = True


class TrackedSkillResponse(BaseModel):
    """A skill the user is currently tracking."""

    id: UUID
    slug: str
    title: str
    current_level: int = Field(..., ge=0, le=10)
    track_order: int = Field(..., ge=1, le=2)
    started_at: datetime | None = None
    last_tracked_at: datetime | None = None
    recent_avg_score: float | None = None

    class Config:
        from_attributes = True


class SkillContextForLLM(BaseModel):
    """Skill context to inject into LLM prompts (used by ChatService/VoiceService)."""

    skill_id: UUID
    slug: str
    title: str
    current_level: int
    current_level_examples: list[str] = Field(default_factory=list)
    next_level: int | None = None  # None if already at level 10
    next_level_criteria: str | None = None
    next_level_examples: list[str] = Field(default_factory=list)
