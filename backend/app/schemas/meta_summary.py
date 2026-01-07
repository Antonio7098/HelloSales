from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MetaPreference(BaseModel):
    label: str
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    last_seen_at: datetime | None = None


class MetaPattern(BaseModel):
    label: str
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    severity: float | None = Field(default=None, ge=0.0, le=1.0)


class MetaExerciseArchetype(BaseModel):
    key: str
    label: str
    attempts_total: int = Field(default=0, ge=0)
    attempts_30d: int = Field(default=0, ge=0)
    last_practiced_at: datetime | None = None
    affinity: float | None = Field(default=None, ge=0.0, le=1.0)


class MetaMilestone(BaseModel):
    label: str
    occurred_at: datetime | None = None


class MetaSummaryMemory(BaseModel):
    schema_version: int = 1

    preferences: list[MetaPreference] = Field(default_factory=list)
    recurring_strengths: list[MetaPattern] = Field(default_factory=list)
    recurring_issues: list[MetaPattern] = Field(default_factory=list)
    exercise_archetypes: list[MetaExerciseArchetype] = Field(default_factory=list)
    milestones: list[MetaMilestone] = Field(default_factory=list)

    processed_session_summary_ids: list[UUID] = Field(default_factory=list)


class MetaSummaryLLMOutput(BaseModel):
    memory: MetaSummaryMemory
    summary_text: str = Field(default="")
