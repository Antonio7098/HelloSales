"""Generic agent runtime data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class AgentRunStatus(str, Enum):
    """Persisted agent-run lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTurnStatus(str, Enum):
    """Persisted turn lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentToolCallStatus(str, Enum):
    """Persisted tool-call lifecycle states."""

    QUEUED = "queued"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class AgentRun:
    """Persisted generic-agent run."""

    run_id: str
    profile_name: str
    status: AgentRunStatus
    request_id: str | None
    trace_id: str | None
    actor_id: str | None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latest_turn_id: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    error_details: dict[str, object] | None = None


@dataclass(slots=True)
class AgentTurn:
    """Persisted input/output turn for one run."""

    turn_id: str
    run_id: str
    sequence_no: int
    input_text: str
    status: AgentTurnStatus
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    response_text: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    error_details: dict[str, object] | None = None


@dataclass(slots=True)
class AgentToolCall:
    """Persisted tool invocation for one turn."""

    tool_call_id: str
    run_id: str
    turn_id: str
    sequence_no: int
    tool_name: str
    status: AgentToolCallStatus
    arguments: dict[str, object]
    requires_approval: bool
    approval_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_payload: dict[str, object] | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    error_details: dict[str, object] | None = None


@dataclass(slots=True)
class AgentArtifact:
    """Persisted structured output produced by an agent run."""

    artifact_id: str
    run_id: str
    turn_id: str | None
    artifact_type: str
    payload: dict[str, object]
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class AgentStreamEvent:
    """Ordered agent event persisted for replay and diagnostics."""

    event_id: str
    run_id: str
    turn_id: str | None
    sequence_no: int
    event_type: str
    severity: str
    payload: dict[str, object]
    created_at: datetime = field(default_factory=utc_now)
    code: str | None = None


@dataclass(slots=True)
class AgentDiagnosticsSummary:
    """Operator-facing summary of generic-agent runtime state."""

    active_count: int
    awaiting_approval_count: int
    total_count: int
    recent_runs: list[AgentRun]
