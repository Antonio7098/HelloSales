"""Session views returned to adapters."""

from pydantic import BaseModel


class SessionItemView(BaseModel):
    """Operational view of one session item."""

    item_id: str
    sequence_no: int
    item_type: str
    actor_id: str | None = None
    run_id: str | None = None
    turn_id: str | None = None
    tool_call_id: str | None = None
    payload: dict[str, object]
    created_at: str


class SessionSummaryView(BaseModel):
    """Summary view returned after session mutations."""

    session_id: str
    status: str
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
    last_summarized_item_sequence: int
    created_at: str
    updated_at: str
    completed_at: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None


class SessionSummaryStateView(BaseModel):
    """Materialized session summary state."""

    summary_id: str
    status: str
    coverage_start_sequence: int
    coverage_end_sequence: int
    summary_text: str
    task_id: str | None = None
    provider_name: str | None = None
    model_name: str | None = None
    prompt_id: str
    prompt_version: str
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class SessionDetailView(SessionSummaryView):
    """Detailed session view with append-only items."""

    summary: SessionSummaryStateView | None = None
    items: list[SessionItemView]
