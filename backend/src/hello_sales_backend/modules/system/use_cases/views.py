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
    kind: str = "provider"
    required: bool = False
    degraded: bool = False


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
    prompt_id: str | None = None
    prompt_version: str | None = None
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


class WorkerRunSnapshotView(BaseModel):
    """Worker-run summary for diagnostics."""

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


class WorkerDiagnosticsView(BaseModel):
    """Worker runtime diagnostics summary."""

    active_count: int
    total_count: int
    recent: list[WorkerRunSnapshotView]


class SessionSnapshotView(BaseModel):
    """Session summary for diagnostics."""

    session_id: str
    status: str
    profile_name: str
    latest_run_id: str | None = None
    latest_item_id: str | None = None
    summary_task_id: str | None = None
    summary_status: str | None = None
    last_summarized_item_sequence: int
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    user_id: str | None = None
    org_id: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class SessionDiagnosticsView(BaseModel):
    """Session runtime diagnostics summary."""

    total_count: int
    active_count: int
    awaiting_approval_count: int
    recent: list[SessionSnapshotView]


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


class MetricsDiagnosticsView(BaseModel):
    """Metrics runtime summary."""

    enabled: bool
    exporter: str
    endpoint_enabled: bool
    endpoint_path: str
    http_enabled: bool
    health_enabled: bool
    background_tasks_enabled: bool
    agents_enabled: bool
    workers_enabled: bool


class TracingDiagnosticsView(BaseModel):
    """Tracing runtime summary."""

    enabled: bool
    exporter: str
    service_name: str
    service_version: str
    environment: str
    http_enabled: bool
    background_tasks_enabled: bool
    agents_enabled: bool
    workers_enabled: bool
    otlp_endpoint: str = ""


class ObservabilityDiagnosticsView(BaseModel):
    """Observability runtime summary."""

    metrics: MetricsDiagnosticsView
    tracing: TracingDiagnosticsView


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
    sessions: SessionDiagnosticsView
    workers: WorkerDiagnosticsView
    observability: ObservabilityDiagnosticsView
    events: list[OperationalEventView]
    alerts: list[AlertView]
