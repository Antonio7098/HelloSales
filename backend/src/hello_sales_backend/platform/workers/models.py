"""Worker runtime data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from hello_sales_backend.platform.llm import EffectivePromptRef


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class WorkerRunStatus(StrEnum):
    """Persisted worker-run lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerExecutionMode(StrEnum):
    """Execution owner for a worker run."""

    DIRECT = "direct"
    STAGEFLOW = "stageflow"


@dataclass(slots=True)
class WorkerRun:
    """Persisted worker run state."""

    run_id: str
    worker_name: str
    status: WorkerRunStatus
    input_payload: dict[str, object]
    request_id: str | None
    trace_id: str | None
    actor_id: str | None
    prompt: EffectivePromptRef | None = None
    execution_mode: WorkerExecutionMode = WorkerExecutionMode.DIRECT
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task_id: str | None = None
    attempt_count: int = 0
    max_attempts: int = 1
    timeout_seconds: float | None = None
    output_payload: dict[str, object] | None = None
    provider_name: str | None = None
    model_name: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    error_details: dict[str, object] | None = None


@dataclass(slots=True)
class WorkerRunEvent:
    """Ordered worker event persisted for diagnostics."""

    event_id: str
    run_id: str
    sequence_no: int
    event_type: str
    severity: str
    payload: dict[str, object]
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    code: str | None = None


@dataclass(slots=True)
class WorkerDiagnosticsSummary:
    """Operator-facing summary of worker runtime state."""

    active_count: int
    total_count: int
    recent_runs: list[WorkerRun]
