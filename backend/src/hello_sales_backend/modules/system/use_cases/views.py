"""System views."""

from pydantic import BaseModel


class SystemStatusView(BaseModel):
    """System status returned to adapters."""

    app_name: str
    environment: str
    workflow_engine: str
    workflow_installed: bool
    current_time_utc: str


class ProviderDiagnosticsView(BaseModel):
    """Provider diagnostics returned to adapters."""

    name: str
    available: bool


class TaskSnapshotView(BaseModel):
    """Background task diagnostics."""

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


class TaskDiagnosticsView(BaseModel):
    """Background task summary."""

    active_count: int
    failure_count: int
    total_count: int
    recent: list[TaskSnapshotView]


class AgentRunSnapshotView(BaseModel):
    """Generic-agent run summary for diagnostics."""

    run_id: str
    profile_name: str
    status: str
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    latest_turn_id: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None


class AgentDiagnosticsView(BaseModel):
    """Agent runtime diagnostics summary."""

    active_count: int
    awaiting_approval_count: int
    total_count: int
    recent: list[AgentRunSnapshotView]


class AgentProfileView(BaseModel):
    """Registered agent profile metadata."""

    agent_id: str
    display_name: str


class OperationalEventView(BaseModel):
    """Operational event diagnostics."""

    event_type: str
    severity: str
    component: str | None = None
    operation: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    code: str | None = None
    payload: dict[str, object]


class AlertView(BaseModel):
    """Active operational alert."""

    code: str
    severity: str
    message: str
    created_at: str
    event_type: str | None = None
    component: str | None = None
    operation: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    details: dict[str, object]


class SystemDiagnosticsView(BaseModel):
    """Detailed operational diagnostics."""

    app_name: str
    environment: str
    database_scheme: str
    workflow_engine: str
    workflow_installed: bool
    current_time_utc: str
    providers: list[ProviderDiagnosticsView]
    agent_profiles: list[AgentProfileView]
    tasks: TaskDiagnosticsView
    agents: AgentDiagnosticsView
    events: list[OperationalEventView]
    alerts: list[AlertView]
