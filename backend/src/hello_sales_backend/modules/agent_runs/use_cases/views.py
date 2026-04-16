"""Agent-runs views returned to adapters."""

from pydantic import BaseModel


class AgentToolCallView(BaseModel):
    """Operational view of one agent tool call."""

    tool_call_id: str
    tool_name: str
    status: str
    requires_approval: bool
    approval_id: str | None = None
    arguments: dict[str, object]
    result_payload: dict[str, object] | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None


class AgentTurnView(BaseModel):
    """Operational view of one agent turn."""

    turn_id: str
    sequence_no: int
    status: str
    input_text: str
    response_text: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    tools: list[AgentToolCallView]


class AgentRunSummaryView(BaseModel):
    """Summary view returned after run mutations."""

    run_id: str
    profile_name: str
    status: str
    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    latest_turn_id: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error_code: str | None = None
    error_category: str | None = None
    error_message: str | None = None


class AgentRunDetailView(AgentRunSummaryView):
    """Detailed run view with all turns."""

    turns: list[AgentTurnView]


class AgentEventView(BaseModel):
    """Ordered event view for one run."""

    event_id: str
    sequence_no: int
    event_type: str
    severity: str
    code: str | None = None
    turn_id: str | None = None
    payload: dict[str, object]
    created_at: str


class AgentApprovalView(BaseModel):
    """Approval action result."""

    approval_id: str
    approved: bool
    run_id: str
    turn_id: str
    tool_call_id: str
    status: str
