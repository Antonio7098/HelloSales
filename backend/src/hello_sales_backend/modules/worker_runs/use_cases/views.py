"""Worker-runs views returned to adapters."""

from pydantic import BaseModel


class PromptRefView(BaseModel):
    """Serialized prompt identity used by one worker execution."""

    prompt_id: str
    version: str
    owner_kind: str
    owner_id: str
    purpose: str
    checksum: str | None = None


class WorkerRunSummaryView(BaseModel):
    """Summary view returned after worker mutations."""

    run_id: str
    worker_name: str
    status: str
    prompt: PromptRefView | None = None
    execution_mode: str
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    task_id: str | None = None
    attempt_count: int
    max_attempts: int
    timeout_seconds: float | None = None
    provider_name: str | None = None
    model_name: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None


class WorkerRunDetailView(WorkerRunSummaryView):
    """Detailed worker-run view."""

    input_payload: dict[str, object]
    output_payload: dict[str, object] | None = None
    error_details: dict[str, object] | None = None


class WorkerEventView(BaseModel):
    """Ordered event view for one worker run."""

    event_id: str
    sequence_no: int
    event_type: str
    severity: str
    code: str | None = None
    payload: dict[str, object]
    created_at: str
