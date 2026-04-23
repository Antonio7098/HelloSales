"""System domain entities."""

from pydantic import BaseModel


class RuntimeStatus(BaseModel):
    """Internal runtime status entity."""

    app_name: str
    environment: str
    workflow_engine: str
    workflow_installed: bool
    current_time_utc: str


class ProviderRuntimeStatus(BaseModel):
    """Internal provider diagnostics entity."""

    name: str
    available: bool
    kind: str = "provider"
    required: bool = False
    degraded: bool = False


class TaskRuntimeStatus(BaseModel):
    """Internal task diagnostics entity."""

    task_id: str
    purpose: str
    status: str
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_details: dict[str, object] | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class WorkerRuntimeStatus(BaseModel):
    """Internal worker-run diagnostics entity."""

    run_id: str
    worker_name: str
    status: str
    prompt_id: str | None = None
    prompt_version: str | None = None
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
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
