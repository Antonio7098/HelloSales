from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SkillLevelPoint(BaseModel):
    """Single point in a skill's level history."""

    timestamp: datetime
    from_level: int | None = None
    to_level: int
    reason: str | None = None
    source_assessment_id: UUID | None = None


class SkillProgressResponse(BaseModel):
    """Aggregated progress for a single skill."""

    skill_id: UUID
    slug: str
    title: str
    current_level: int
    is_tracked: bool
    history: list[SkillLevelPoint] = Field(default_factory=list)
    assessment_count: int = 0


class SessionHistoryItem(BaseModel):
    """High-level summary of a session for the dashboard."""

    id: UUID
    started_at: datetime
    ended_at: datetime | None = None
    state: str
    interaction_count: int
    assessment_count: int
    last_assessment_at: datetime | None = None
