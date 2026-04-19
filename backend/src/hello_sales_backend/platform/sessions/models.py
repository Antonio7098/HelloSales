"""Neutral session substrate models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from hello_sales_backend.platform.llm import EffectivePromptRef


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class SessionStatus(StrEnum):
    """Persisted session lifecycle state."""

    ACTIVE = "active"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionSummaryStatus(StrEnum):
    """Persisted session summary lifecycle state."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionItemType(StrEnum):
    """Neutral item types recorded in a session chronology."""

    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SYSTEM_NOTE = "system_note"


@dataclass(slots=True)
class Session:
    """Durable neutral conversation root."""

    session_id: str
    status: SessionStatus
    profile_name: str
    actor_id: str | None = None
    user_id: str | None = None
    org_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    latest_item_id: str | None = None
    latest_run_id: str | None = None
    summary_task_id: str | None = None
    summary_status: str | None = None
    last_summarized_item_sequence: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class SessionItem:
    """One append-only chronological session item."""

    item_id: str
    session_id: str
    sequence_no: int
    item_type: SessionItemType
    payload: dict[str, object]
    actor_id: str | None = None
    run_id: str | None = None
    turn_id: str | None = None
    tool_call_id: str | None = None
    prompt: EffectivePromptRef | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class SessionSummary:
    """Persisted summary coverage for a session."""

    summary_id: str
    session_id: str
    coverage_start_sequence: int
    coverage_end_sequence: int
    summary_text: str
    prompt: EffectivePromptRef
    status: SessionSummaryStatus
    task_id: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
