"""Jobs views."""

from pydantic import BaseModel


class JobTaskView(BaseModel):
    """Single task snapshot exposed through the jobs module."""

    task_id: str
    purpose: str
    status: str
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class JobTaskListView(BaseModel):
    """List of recent tasks."""

    items: list[JobTaskView]


class StartDiagnosticJobView(BaseModel):
    """Response when a diagnostic job is queued."""

    task_id: str
    purpose: str
    status: str
