"""Task metadata models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Protocol


class TaskStatus(str, Enum):
    """Background task lifecycle state."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    PARTIAL_FAILURE = "partial_failure"


@dataclass(slots=True, frozen=True)
class TaskMetadata:
    """Metadata attached to background execution."""

    task_id: str
    purpose: str
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None


@dataclass(slots=True)
class TaskSnapshot:
    """Current or terminal state of a background task."""

    metadata: TaskMetadata
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_details: dict[str, object] | None = None


class TaskEventSink(Protocol):
    """Optional persistence or event sink for task state changes."""

    async def upsert(self, snapshot: TaskSnapshot) -> None: ...


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)
