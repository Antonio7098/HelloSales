from __future__ import annotations

import pytest

from hello_sales_backend.application.agents.contracts import AgentDefinition, ToolSelectionPolicy
from hello_sales_backend.application.agents.registry import AgentRegistry
from hello_sales_backend.platform.agents.config import AgentRuntimeConfig
from hello_sales_backend.platform.agents.memory import InMemoryAgentStore
from hello_sales_backend.platform.agents.models import (
    AgentRun,
    AgentRunStatus,
    AgentToolCallStatus,
    AgentTurn,
    AgentTurnStatus,
)
from hello_sales_backend.platform.agents.runtime import GenericAgentRuntime
from hello_sales_backend.platform.agents.tools import (
    AgentToolCatalog,
    AgentToolDefinition,
    AgentToolExecutionContext,
    AgentToolRequest,
)
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import (
    AlertPolicy,
    InMemoryOperationalStore,
    ObservabilityRuntime,
)
from hello_sales_backend.platform.providers.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
)
from hello_sales_backend.platform.workflows.runtime import build_workflow_runtime
from hello_sales_backend.shared.errors import AppError, app_error


class FakeChatModel(ChatModelPort):
    provider_name = "fake-runtime"

    def __init__(self, *, configured: bool = True, output_text: str = "provider-output") -> None:
        self._configured = configured
        self._output_text = output_text

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion:
        return ChatCompletion(
            provider=self.provider_name,
            model="fake-model",
            output_text=f"{self._output_text}:{messages[-1].content}",
        )

    def is_configured(self) -> bool:
        return self._configured


class FixedSelectionPolicy:
    def __init__(self, requests: list[AgentToolRequest]) -> None:
        self._requests = requests

    def select(self, user_input: str, catalog: AgentToolCatalog) -> list[AgentToolRequest]:
        return list(self._requests)


def _build_runtime(
    *,
    store: InMemoryAgentStore,
    tools: AgentToolCatalog,
    llm_provider: ChatModelPort | None = None,
    selection_policy: ToolSelectionPolicy | None = None,
) -> GenericAgentRuntime:
    observability = ObservabilityRuntime(
        store=InMemoryOperationalStore(),
        alert_policy=AlertPolicy(),
    )
    workflow_runtime = build_workflow_runtime(Settings(environment="test", database_url="sqlite+aiosqlite:///runtime.db"))
    return GenericAgentRuntime(
        config=AgentRuntimeConfig(),
        workflow_runtime=workflow_runtime,
        llm_provider=llm_provider or FakeChatModel(),
        store=store,
        agents=AgentRegistry(
            [
                AgentDefinition(
                    agent_id="generic",
                    display_name="Test Generic Agent",
                    tools=tools,
                    selection_policy=selection_policy or FixedSelectionPolicy([]),
                    build_messages=lambda user_input, _tool_context: [ChatMessage(role="user", content=user_input)],
                    build_fallback_response=lambda user_input, tool_context: f"fallback:{user_input}:{tool_context}",
                )
            ],
            default_agent_id="generic",
        ),
        observability=observability,
    )


def _build_runtime_with_observability(
    *,
    store: InMemoryAgentStore,
    tools: AgentToolCatalog,
    llm_provider: ChatModelPort | None = None,
    selection_policy: ToolSelectionPolicy | None = None,
) -> tuple[GenericAgentRuntime, ObservabilityRuntime]:
    observability = ObservabilityRuntime(
        store=InMemoryOperationalStore(),
        alert_policy=AlertPolicy(),
    )
    workflow_runtime = build_workflow_runtime(Settings(environment="test", database_url="sqlite+aiosqlite:///runtime.db"))
    runtime = GenericAgentRuntime(
        config=AgentRuntimeConfig(),
        workflow_runtime=workflow_runtime,
        llm_provider=llm_provider or FakeChatModel(),
        store=store,
        agents=AgentRegistry(
            [
                AgentDefinition(
                    agent_id="generic",
                    display_name="Test Generic Agent",
                    tools=tools,
                    selection_policy=selection_policy or FixedSelectionPolicy([]),
                    build_messages=lambda user_input, _tool_context: [ChatMessage(role="user", content=user_input)],
                    build_fallback_response=lambda user_input, tool_context: f"fallback:{user_input}:{tool_context}",
                )
            ],
            default_agent_id="generic",
        ),
        observability=observability,
    )
    return runtime, observability


async def _seed_run(store: InMemoryAgentStore, *, input_text: str) -> tuple[AgentRun, AgentTurn]:
    run = AgentRun(
        run_id="run-1",
        profile_name="generic",
        status=AgentRunStatus.PENDING,
        request_id="req-1",
        trace_id="tr-1",
        actor_id=None,
    )
    turn = AgentTurn(
        turn_id="turn-1",
        run_id=run.run_id,
        sequence_no=1,
        input_text=input_text,
        status=AgentTurnStatus.PENDING,
    )
    run.latest_turn_id = turn.turn_id
    await store.create_run(run)
    await store.create_turn(turn)
    return run, turn


@pytest.mark.asyncio
async def test_generic_agent_runtime_completes_turn_with_tool_and_provider_response() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    runtime = _build_runtime(
        store=store,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
        selection_policy=FixedSelectionPolicy([AgentToolRequest(name="get_runtime_status", arguments={})]),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    tool_calls = await store.list_tool_calls("run-1", "turn-1")
    events = await store.list_events("run-1", limit=20)

    assert run is not None and run.status == AgentRunStatus.COMPLETED
    assert turn is not None and turn.status == AgentTurnStatus.COMPLETED
    assert turn.response_text == "provider-output:show runtime status"
    assert len(tool_calls) == 1
    assert tool_calls[0].status == AgentToolCallStatus.COMPLETED
    assert any(event.event_type == "agent.tool.completed" for event in events)


@pytest.mark.asyncio
async def test_generic_agent_runtime_pauses_for_approval() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="run diagnostic job")
    runtime = _build_runtime(
        store=store,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="run_diagnostic_job",
                    description="diagnostic",
                    execute=lambda _arguments, _context: {"task_id": "task-1"},
                    requires_approval=True,
                )
            ]
        ),
        selection_policy=FixedSelectionPolicy([AgentToolRequest(name="run_diagnostic_job", arguments={})]),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    tool_calls = await store.list_tool_calls("run-1", "turn-1")

    assert run is not None and run.status == AgentRunStatus.AWAITING_APPROVAL
    assert turn is not None and turn.status == AgentTurnStatus.AWAITING_APPROVAL
    assert len(tool_calls) == 1
    assert tool_calls[0].status == AgentToolCallStatus.PENDING_APPROVAL
    assert tool_calls[0].approval_id is not None


@pytest.mark.asyncio
async def test_generic_agent_runtime_records_tool_failures() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")

    async def failing_tool(_arguments: dict[str, object], _context: AgentToolExecutionContext) -> dict[str, object]:
        raise app_error(
            "Tool failed",
            code="agent.tool.test_failure",
            category="internal",
            status_code=500,
            operation="agent.tool.execute",
            component="agent",
        )

    runtime = _build_runtime(
        store=store,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    execute=failing_tool,
                )
            ]
        ),
        llm_provider=FakeChatModel(),
        selection_policy=FixedSelectionPolicy([AgentToolRequest(name="get_runtime_status", arguments={})]),
    )

    with pytest.raises(AppError):
        await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    tool_calls = await store.list_tool_calls("run-1", "turn-1")
    events = await store.list_events("run-1", limit=20)

    assert run is not None and run.status == AgentRunStatus.FAILED
    assert turn is not None and turn.status == AgentTurnStatus.FAILED
    assert tool_calls[0].status == AgentToolCallStatus.FAILED
    assert tool_calls[0].error_code == "agent.tool.test_failure"
    assert any(event.event_type == "agent.tool.failed" for event in events)
    assert any(event.event_type == "agent.turn.failed" for event in events)


@pytest.mark.asyncio
async def test_generic_agent_runtime_failure_emits_operational_event_with_correlation() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")

    async def failing_tool(_arguments: dict[str, object], _context: AgentToolExecutionContext) -> dict[str, object]:
        raise app_error(
            "Tool failed",
            code="agent.tool.test_failure",
            category="internal",
            status_code=500,
            operation="agent.tool.execute",
            component="agent",
        )

    runtime, observability = _build_runtime_with_observability(
        store=store,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    execute=failing_tool,
                )
            ]
        ),
        llm_provider=FakeChatModel(),
        selection_policy=FixedSelectionPolicy([AgentToolRequest(name="get_runtime_status", arguments={})]),
    )

    with pytest.raises(AppError):
        await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    op_events = observability.recent_events()
    assert op_events
    failure_event = op_events[0]
    assert failure_event.event_type == "agent.turn.failed"
    assert failure_event.code
    assert failure_event.correlation_id == "req-1"
    assert failure_event.trace_id == "tr-1"


@pytest.mark.asyncio
async def test_generic_agent_runtime_persists_correlation_on_agent_events() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    runtime = _build_runtime(
        store=store,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
        selection_policy=FixedSelectionPolicy([AgentToolRequest(name="get_runtime_status", arguments={})]),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    events = await store.list_events("run-1", limit=20)
    assert events
    assert all(event.request_id == "req-1" for event in events)
    assert all(event.trace_id == "tr-1" for event in events)
