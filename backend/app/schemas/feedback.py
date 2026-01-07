"""Pydantic schemas for feedback events (flags + reports).

Used by WebSocket handlers and (optional) HTTP endpoints defined in SPR-006.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackRole(str, Enum):
    """Role associated with the feedback target message."""

    USER = "user"
    ASSISTANT = "assistant"


class FeedbackCategory(str, Enum):
    """High-level category for feedback events."""

    BAD_ASSISTANT = "bad_assistant"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    LIKE = "like"
    PREFERENCE = "preference"
    TRIAGE_INCORRECT = "triage_incorrect"


class TimeBucket(str, Enum):
    """Coarse time bucketing for when the issue occurred."""

    JUST_NOW = "just_now"
    EARLIER_TODAY = "earlier_today"
    EARLIER_THIS_WEEK = "earlier_this_week"


class FeedbackMessageFlagCreate(BaseModel):
    """Payload for per-message flag submissions from chat/voice transcripts."""

    session_id: UUID | None = Field(
        default=None,
        description="Optional session_id when feedback is not tied to a specific session context",
    )
    interaction_id: UUID
    role: FeedbackRole = Field(..., description="Role of the flagged message")
    category: FeedbackCategory
    name: str = Field(..., max_length=150)
    short_reason: str | None = Field(default=None, max_length=255)
    time_bucket: TimeBucket | None = Field(default=None)


class FeedbackReportCreate(BaseModel):
    """Payload for high-level reports from the Reporting tab."""

    category: FeedbackCategory
    name: str = Field(..., max_length=150)
    description: str | None = Field(default=None)
    scope: str | None = Field(
        default=None,
        description="Optional scope hint: 'chat' | 'voice' | 'app'",
    )
    time_bucket: TimeBucket
    session_id: UUID | None = Field(
        default=None,
        description="Optional session_id when report is tied to a session",
    )
    interaction_id: UUID | None = Field(
        default=None,
        description="Optional interaction_id when report is tied to a message",
    )


class FeedbackEventRead(BaseModel):
    """Serialized feedback event for listing/observability."""

    id: UUID
    user_id: UUID
    session_id: UUID | None
    interaction_id: UUID | None
    role: FeedbackRole | None
    category: FeedbackCategory
    name: str
    short_reason: str | None
    time_bucket: TimeBucket | None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackListResponse(BaseModel):
    """Paginated list response for feedback events."""

    items: list[FeedbackEventRead]
    total: int
