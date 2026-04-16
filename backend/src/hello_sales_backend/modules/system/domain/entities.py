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
