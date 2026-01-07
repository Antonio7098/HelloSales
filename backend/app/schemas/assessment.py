"""Pydantic schemas for assessment engine (triage + skill evaluation).

These schemas are used for:
- Dev/test HTTP endpoints (e.g. /api/v1/test/triage, /api/v1/test/assess)
- Internal service contracts between WebSocket handlers and services
- Serializing assessment results to send to the mobile client
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    """Simple chat role for triage/assessment context."""

    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Minimal message used as context for triage/assessment."""

    role: ChatRole
    content: str


# ──────────────────────────────────────────────────────────────────────────────
# TRIAGE
# ──────────────────────────────────────────────────────────────────────────────


class TriageDecision(str, Enum):
    """Triage decision returned by the TriageService."""

    ASSESS = "assess"
    SKIP = "skip"


class TriageRequest(BaseModel):
    """Request payload for triage.

    Used by:
    - Dev/test HTTP endpoint `/api/v1/test/triage`
    - Internal calls from Chat/Voice services to TriageService
    """

    session_id: UUID
    user_response: str
    context: list[ChatMessage] = Field(
        default_factory=list,
        description="Recent conversation context (e.g. last 2-3 turns)",
    )


class TriageResponse(BaseModel):
    """Triage result with optional observability metadata."""

    decision: TriageDecision
    reason: str
    latency_ms: int | None = None
    tokens_used: int | None = None
    cost_cents: int | None = None
    provider: str | None = None
    model: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# ASSESSMENT RESULTS
# ──────────────────────────────────────────────────────────────────────────────


class FeedbackExampleQuote(BaseModel):
    """Example quote from the user's response, with annotation."""

    quote: str
    annotation: str
    type: str = Field(..., description="'strength' | 'improvement'")


class SkillFeedback(BaseModel):
    """Structured feedback for a single skill assessment."""

    primary_takeaway: str
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    example_quotes: list[FeedbackExampleQuote] = Field(default_factory=list)
    next_level_criteria: str | None = None


class SkillAssessmentResponse(BaseModel):
    """Per-skill assessment result returned to clients/services."""

    skill_id: UUID
    level: int = Field(..., ge=0, le=10)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    summary: str | None = None
    feedback: SkillFeedback

    # Observability
    latency_ms: int | None = None
    tokens_used: int | None = None
    cost_cents: int | None = None
    provider: str | None = None
    model: str | None = None

    class Config:
        from_attributes = True


class AssessmentMetrics(BaseModel):
    """Aggregated metrics for an assessment group."""

    triage_latency_ms: int | None = None
    assessment_latency_ms: int | None = None
    total_cost_cents: int | None = None


class AssessmentResponse(BaseModel):
    """Top-level assessment result.

    Used for:
    - Dev/test HTTP endpoint `/api/v1/test/assess`
    - Internal responses from AssessmentService
    - Basis for WebSocket `assessment.complete` payload
    """

    assessment_id: UUID | None = None
    session_id: UUID | None = None
    interaction_id: UUID | None = None
    triage_decision: str | None = None
    triage_override_label: str | None = None
    # Original user utterance that was assessed (text or transcript)
    user_response: str | None = None
    skills: list[SkillAssessmentResponse]
    metrics: AssessmentMetrics | None = None


# ──────────────────────────────────────────────────────────────────────────────
# ASSESSMENT REQUESTS (DEV/TEST)
# ──────────────────────────────────────────────────────────────────────────────


class AssessmentRequest(BaseModel):
    """Request payload for testing AssessmentService in isolation.

    Mirrors the curl examples in SPR-004.
    """

    user_response: str
    skill_ids: list[UUID]
    current_levels: dict[UUID, int] | None = None
    context: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# LEVEL CHANGE EVENTS
# ──────────────────────────────────────────────────────────────────────────────


class LevelChangeEvent(BaseModel):
    """Event emitted when a user's skill level changes."""

    user_id: UUID
    skill_id: UUID
    from_level: int
    to_level: int
    reason: str | None = None
    source_assessment_id: UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True
