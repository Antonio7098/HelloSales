from __future__ import annotations

import pytest

from hello_sales_backend.application.agents.contracts import (
    AgentDefinition,
    AgentPromptDefinition,
)
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
    EmptyToolArguments,
)
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.llm import (
    JSONGenerationResult,
    LLMCallContext,
    LLMMessage,
    LLMProviderPort,
    PromptMetadata,
    ProviderToolCall,
    ProviderToolDefinition,
    TextGenerationResult,
    ToolCallCompletionResult,
)
from hello_sales_backend.platform.observability.metrics import (
    MetricsRuntimeSnapshot,
    PrometheusMetricsRuntime,
)
from hello_sales_backend.platform.observability.runtime import (
    AlertPolicy,
    InMemoryOperationalStore,
    ObservabilityRuntime,
)
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage
from hello_sales_backend.platform.workflows.runtime import build_workflow_runtime
from hello_sales_backend.shared.errors import AppError, app_error


class ScriptedToolProvider(LLMProviderPort):
    provider_name = "fake-runtime"

    def __init__(
        self,
        *,
        completions: list[ToolCallCompletionResult | AppError],
        configured: bool = True,
        output_text: str = "provider-output",
    ) -> None:
        self._configured = configured
        self._output_text = output_text
        self._completions = list(completions)
        self.tool_requests: list[dict[str, object]] = []

    async def generate(self, messages: list[LLMMessage]) -> TextGenerationResult:
        return await self.generate_text(messages)

    async def generate_text(
        self,
        messages: list[LLMMessage],
        *,
        context: LLMCallContext | None = None,
    ) -> TextGenerationResult:
        del context
        return TextGenerationResult(
            provider=self.provider_name,
            model="fake-model",
            output_text=f"{self._output_text}:{messages[-1].content}",
        )

    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint=None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult:
        del messages, schema_hint, context
        return JSONGenerationResult(
            provider=self.provider_name,
            model="fake-model",
            raw_text="{}",
            output_json={},
        )

    async def complete_with_tools(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[ProviderToolDefinition],
        context: LLMCallContext | None = None,
        tool_choice: str | None = None,
        on_text_delta=None,
    ) -> ToolCallCompletionResult:
        del context, tool_choice
        self.tool_requests.append(
            {
                "messages": messages,
                "tool_names": [tool.name for tool in tools],
            }
        )
        if not self._completions:
            raise AssertionError("provider completion script exhausted")
        completion = self._completions.pop(0)
        if isinstance(completion, AppError):
            raise completion
        if on_text_delta is not None and completion.content:
            await on_text_delta(completion.content)
        return completion

    def is_configured(self) -> bool:
        return self._configured


class FailingToolCallStore(InMemoryAgentStore):
    def __init__(self, *, fail_on: str) -> None:
        super().__init__()
        self._fail_on = fail_on

    async def create_tool_call(self, tool_call) -> None:
        if self._fail_on == "create":
            raise RuntimeError("create failed")
        await super().create_tool_call(tool_call)

    async def update_tool_call(self, tool_call) -> None:
        if self._fail_on == "update":
            raise RuntimeError("update failed")
        await super().update_tool_call(tool_call)


def _build_runtime(
    *,
    store: InMemoryAgentStore,
    tools: AgentToolCatalog,
    llm_provider: LLMProviderPort | None = None,
) -> GenericAgentRuntime:
    observability = ObservabilityRuntime(
        store=InMemoryOperationalStore(),
        alert_policy=AlertPolicy(),
    )
    workflow_runtime = build_workflow_runtime(
        Settings(environment="test", database_url="sqlite+aiosqlite:///runtime.db")
    )
    return GenericAgentRuntime(
        config=AgentRuntimeConfig(),
        workflow_runtime=workflow_runtime,
        llm_provider=llm_provider or ScriptedToolProvider(completions=[]),
        store=store,
        agents=AgentRegistry(
            [
                AgentDefinition(
                    agent_id="generic",
                    display_name="Test Generic Agent",
                    tools=tools,
                    prompt=AgentPromptDefinition(
                        metadata=PromptMetadata(
                            prompt_id="agent.generic.test",
                            version="v1",
                            owner_kind="agent",
                            owner_id="generic",
                            purpose="response",
                        ),
                        build_messages=lambda user_input: [
                            ChatMessage(role="user", content=user_input)
                        ],
                        build_fallback_response=lambda user_input: f"fallback:{user_input}",
                    ),
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
    llm_provider: LLMProviderPort | None = None,
    observability: ObservabilityRuntime | None = None,
) -> tuple[GenericAgentRuntime, ObservabilityRuntime]:
    observability = observability or ObservabilityRuntime(
        store=InMemoryOperationalStore(),
        alert_policy=AlertPolicy(),
    )
    workflow_runtime = build_workflow_runtime(
        Settings(environment="test", database_url="sqlite+aiosqlite:///runtime.db")
    )
    runtime = GenericAgentRuntime(
        config=AgentRuntimeConfig(),
        workflow_runtime=workflow_runtime,
        llm_provider=llm_provider or ScriptedToolProvider(completions=[]),
        store=store,
        agents=AgentRegistry(
            [
                AgentDefinition(
                    agent_id="generic",
                    display_name="Test Generic Agent",
                    tools=tools,
                    prompt=AgentPromptDefinition(
                        metadata=PromptMetadata(
                            prompt_id="agent.generic.test",
                            version="v1",
                            owner_kind="agent",
                            owner_id="generic",
                            purpose="response",
                        ),
                        build_messages=lambda user_input: [
                            ChatMessage(role="user", content=user_input)
                        ],
                        build_fallback_response=lambda user_input: f"fallback:{user_input}",
                    ),
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
async def test_generic_agent_runtime_completes_turn_with_native_tool_calling() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-1",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
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
    assert tool_calls[0].tool_call_id == "call-1"
    assert tool_calls[0].status == AgentToolCallStatus.COMPLETED
    assert any(event.event_type == "agent.tool.completed" for event in events)
    assert any(event.event_type == "agent.response.delta" for event in events)
    assert provider.tool_requests[0]["tool_names"] == ["get_runtime_status"]
    tool_messages = [
        item for item in provider.tool_requests[1]["messages"] if item.get("role") == "tool"
    ]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call-1"


@pytest.mark.asyncio
async def test_generic_agent_runtime_reclassifies_unknown_provider_tool_as_provider_error() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-missing",
                        tool_name="missing_tool",
                        arguments={"query": "status"},
                    )
                ],
            )
            ,
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
    )

    with pytest.raises(AppError) as exc_info:
        await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    assert exc_info.value.code == "provider.invalid_tool_name"
    assert exc_info.value.category == "provider"
    assert exc_info.value.status_code == 502

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    assert run is not None and run.error_code == "provider.invalid_tool_name"
    assert turn is not None and turn.error_code == "provider.invalid_tool_name"


@pytest.mark.asyncio
async def test_generic_agent_runtime_reclassifies_provider_tool_argument_schema_failure() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-bad-args",
                        tool_name="get_runtime_status",
                        arguments={"unexpected": "value"},
                    )
                ],
            )
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
    )

    with pytest.raises(AppError) as exc_info:
        await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    assert exc_info.value.code == "provider.invalid_tool_arguments"
    assert exc_info.value.category == "provider"
    assert exc_info.value.status_code == 502

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    assert run is not None and run.error_code == "provider.invalid_tool_arguments"
    assert turn is not None and turn.error_code == "provider.invalid_tool_arguments"


@pytest.mark.asyncio
async def test_generic_agent_runtime_preserves_data_error_when_tool_call_create_fails() -> None:
    store = FailingToolCallStore(fail_on="create")
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-create-fail",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
    )

    with pytest.raises(AppError) as exc_info:
        await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    assert exc_info.value.code == "data.agent_tool_call.create_failed"
    assert exc_info.value.category == "data"

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    assert run is not None and run.error_code == "data.agent_tool_call.create_failed"
    assert turn is not None and turn.error_code == "data.agent_tool_call.create_failed"


@pytest.mark.asyncio
async def test_generic_agent_runtime_pauses_for_approval() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="run diagnostic job")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-approval",
                        tool_name="run_diagnostic_job",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="run_diagnostic_job",
                    description="diagnostic",
                    arguments_model=EmptyToolArguments,
                    execute=lambda _arguments, _context: {"task_id": "task-1"},
                    requires_approval=True,
                )
            ]
        ),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    tool_calls = await store.list_tool_calls("run-1", "turn-1")

    assert run is not None and run.status == AgentRunStatus.AWAITING_APPROVAL
    assert turn is not None and turn.status == AgentTurnStatus.AWAITING_APPROVAL
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_call_id == "call-approval"
    assert tool_calls[0].status == AgentToolCallStatus.PENDING_APPROVAL
    assert tool_calls[0].approval_id is not None


@pytest.mark.asyncio
async def test_generic_agent_runtime_records_tool_failures() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")

    async def failing_tool(
        _arguments: dict[str, object], _context: AgentToolExecutionContext
    ) -> dict[str, object]:
        raise app_error(
            "Tool failed",
            code="agent.tool.test_failure",
            category="internal",
            status_code=500,
            operation="agent.tool.execute",
            component="agent",
        )

    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-fail",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=failing_tool,
                )
            ]
        ),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    tool_calls = await store.list_tool_calls("run-1", "turn-1")
    events = await store.list_events("run-1", limit=20)

    assert run is not None and run.status == AgentRunStatus.COMPLETED
    assert turn is not None and turn.status == AgentTurnStatus.COMPLETED
    assert turn.response_text == "provider-output:show runtime status"
    assert tool_calls[0].status == AgentToolCallStatus.FAILED
    assert tool_calls[0].error_code == "agent.tool.test_failure"
    assert any(event.event_type == "agent.tool.failed" for event in events)
    assert not any(event.event_type == "agent.turn.failed" for event in events)
    tool_messages = [
        item for item in provider.tool_requests[1]["messages"] if item.get("role") == "tool"
    ]
    assert len(tool_messages) == 1
    assert "agent.tool.test_failure" in str(tool_messages[0]["content"])


@pytest.mark.asyncio
async def test_generic_agent_runtime_failure_emits_operational_event_with_correlation() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")

    async def failing_tool(
        _arguments: dict[str, object], _context: AgentToolExecutionContext
    ) -> dict[str, object]:
        raise RuntimeError("boom")

    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-fail",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            )
        ]
    )
    runtime, observability = _build_runtime_with_observability(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=failing_tool,
                )
            ]
        ),
    )

    with pytest.raises(AppError):
        await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    op_events = observability.recent_events()
    failure_event = next(event for event in op_events if event.event_type == "agent.turn.failed")
    assert failure_event.event_type == "agent.turn.failed"
    assert failure_event.code
    assert failure_event.correlation_id == "req-1"
    assert failure_event.trace_id == "tr-1"


@pytest.mark.asyncio
async def test_generic_agent_runtime_fails_when_tool_failure_retry_budget_is_exhausted() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")

    async def failing_tool(
        _arguments: dict[str, object], _context: AgentToolExecutionContext
    ) -> dict[str, object]:
        raise app_error(
            "Tool failed",
            code="agent.tool.test_failure",
            category="validation",
            status_code=400,
            operation="agent.tool.execute",
            component="agent",
        )

    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-fail-1",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-fail-2",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-fail-3",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=failing_tool,
                )
            ]
        ),
    )

    provider._completions.append(
        ToolCallCompletionResult(
            provider="fake-runtime",
            model="fake-model",
            content="I could not complete the request because the tool retry budget was exhausted.",
        )
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    events = await store.list_events("run-1", limit=40)

    assert run is not None and run.status == AgentRunStatus.COMPLETED
    assert turn is not None and turn.status == AgentTurnStatus.COMPLETED
    assert "retry budget was exhausted" in (turn.response_text or "")
    assert any(event.event_type == "agent.tool.retry_limit_exceeded" for event in events)
    tool_messages = [
        item for item in provider.tool_requests[-1]["messages"] if item.get("role") == "tool"
    ]
    assert any("agent.tool.max_retries_exceeded" in str(item["content"]) for item in tool_messages)


@pytest.mark.asyncio
async def test_generic_agent_runtime_retries_empty_completion_then_completes() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="",
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog([]),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    turn = await store.get_turn("turn-1")
    events = await store.list_events("run-1", limit=20)

    assert turn is not None and turn.status == AgentTurnStatus.COMPLETED
    assert turn.response_text == "provider-output:show runtime status"
    assert provider.tool_requests[1]["messages"][-1]["role"] == "system"
    assert any(event.event_type == "agent.attempt.empty_completion" for event in events)
    assert any(event.event_type == "agent.attempt.retry_scheduled" for event in events)


@pytest.mark.asyncio
async def test_generic_agent_runtime_retries_retryable_provider_error_then_completes() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            app_error(
                "upstream unavailable",
                code="provider.upstream_unavailable",
                category="provider",
                status_code=503,
                retryable=True,
                operation="agent.llm.complete_with_tools",
                component="agent",
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog([]),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    turn = await store.get_turn("turn-1")
    events = await store.list_events("run-1", limit=20)

    assert turn is not None and turn.status == AgentTurnStatus.COMPLETED
    assert turn.response_text == "provider-output:show runtime status"
    assert len(provider.tool_requests) == 2
    assert any(event.event_type == "agent.attempt.provider_failed" for event in events)
    assert any(event.event_type == "agent.attempt.retry_scheduled" for event in events)


@pytest.mark.asyncio
async def test_generic_agent_runtime_fails_after_exhausting_empty_completion_retries() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(provider="fake-runtime", model="fake-model", content=""),
            ToolCallCompletionResult(provider="fake-runtime", model="fake-model", content=""),
            ToolCallCompletionResult(provider="fake-runtime", model="fake-model", content=""),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog([]),
    )

    with pytest.raises(AppError) as exc_info:
        await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    run = await store.get_run("run-1")
    turn = await store.get_turn("turn-1")
    events = await store.list_events("run-1", limit=20)

    assert exc_info.value.code == "agent.provider.empty_completion"
    assert run is not None and run.status == AgentRunStatus.FAILED
    assert turn is not None and turn.status == AgentTurnStatus.FAILED
    assert any(event.event_type == "agent.attempt.empty_completion" for event in events)
    assert any(event.event_type == "agent.turn.failed" for event in events)


@pytest.mark.asyncio
async def test_generic_agent_runtime_persists_correlation_on_agent_events() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-1",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime = _build_runtime(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    events = await store.list_events("run-1", limit=20)
    assert events
    assert all(event.request_id == "req-1" for event in events)
    assert all(event.trace_id == "tr-1" for event in events)


@pytest.mark.asyncio
async def test_generic_agent_runtime_emits_agent_metrics_for_execution_and_tools() -> None:
    store = InMemoryAgentStore()
    await _seed_run(store, input_text="show runtime status")
    observability = ObservabilityRuntime(
        store=InMemoryOperationalStore(),
        alert_policy=AlertPolicy(),
        metrics=PrometheusMetricsRuntime(
            MetricsRuntimeSnapshot(
                enabled=True,
                exporter="prometheus",
                endpoint_enabled=True,
                endpoint_path="/metrics",
                http_enabled=False,
                health_enabled=False,
                background_tasks_enabled=False,
                agents_enabled=True,
                workers_enabled=False,
            )
        ),
    )
    provider = ScriptedToolProvider(
        completions=[
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                tool_calls=[
                    ProviderToolCall(
                        call_id="call-1",
                        tool_name="get_runtime_status",
                        arguments={},
                    )
                ],
            ),
            ToolCallCompletionResult(
                provider="fake-runtime",
                model="fake-model",
                content="provider-output:show runtime status",
            ),
        ]
    )
    runtime, _ = _build_runtime_with_observability(
        store=store,
        llm_provider=provider,
        tools=AgentToolCatalog(
            [
                AgentToolDefinition(
                    name="get_runtime_status",
                    description="status",
                    arguments_model=EmptyToolArguments,
                    execute=lambda _arguments, _context: {"status": "ok"},
                )
            ]
        ),
        observability=observability,
    )

    await runtime.process_turn(run_id="run-1", turn_id="turn-1")

    metrics_payload, _ = observability.render_metrics()
    metrics_text = metrics_payload.decode("utf-8")

    assert 'hello_sales_agent_turn_executions_started_total{profile="generic"} 1.0' in metrics_text
    assert (
        'hello_sales_agent_turn_executions_completed_total{profile="generic",status="completed"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_agent_tool_calls_started_total{profile="generic",tool="get_runtime_status"} 1.0'
        in metrics_text
    )
    assert (
        'hello_sales_agent_tool_calls_completed_total{profile="generic",status="completed",tool="get_runtime_status"} 1.0'
        in metrics_text
    )
