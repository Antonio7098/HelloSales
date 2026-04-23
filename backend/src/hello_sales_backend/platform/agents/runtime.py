"""Native-tool-calling agent runtime."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol, cast

from stageflow.pipeline.dag import UnifiedStageExecutionError

from hello_sales_backend.application.agents.registry import AgentRegistry
from hello_sales_backend.platform.agents.config import AgentRuntimeConfig
from hello_sales_backend.platform.agents.models import (
    AgentRun,
    AgentRunStatus,
    AgentStreamEvent,
    AgentToolCall,
    AgentToolCallStatus,
    AgentTurn,
    AgentTurnStatus,
    utc_now,
)
from hello_sales_backend.platform.agents.persistence import AgentStorePort
from hello_sales_backend.platform.agents.tools import AgentToolExecutionContext
from hello_sales_backend.platform.llm import (
    EffectivePromptRef,
    ProviderToolCall,
    ToolCallCompletionResult,
    decide_llm_retry,
    empty_completion_issue,
    provider_error_issue,
)
from hello_sales_backend.platform.llm.contracts import LLMCallContext, LLMProviderPort


def _safe_int(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage
from hello_sales_backend.platform.sessions.attachment import SessionAttachmentStore
from hello_sales_backend.platform.sessions.models import SessionItem, SessionItemType
from hello_sales_backend.platform.sessions.persistence import SessionStorePort
from hello_sales_backend.platform.workflows.pipeline import WorkflowStageKind, WorkflowStageSpec
from hello_sales_backend.platform.workflows.runtime import WorkflowRuntime
from hello_sales_backend.shared.errors import AppError, app_error, internal_error
from hello_sales_backend.shared.ids import new_id


class AgentExecutionRuntime(Protocol):
    """Execution surface used by the application service."""

    async def process_turn(self, *, run_id: str, turn_id: str) -> None: ...


@dataclass(slots=True)
class GenericAgentRuntime:
    """Own the execution lifecycle for application agent runs."""

    config: AgentRuntimeConfig
    workflow_runtime: WorkflowRuntime
    llm_provider: LLMProviderPort
    store: AgentStorePort
    agents: AgentRegistry
    observability: ObservabilityRuntime
    sessions: SessionAttachmentStore | None = None
    session_store: SessionStorePort | None = None
    _logger: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = get_logger("hello_sales_backend.agent_runtime")

    async def process_turn(self, *, run_id: str, turn_id: str) -> None:
        run = await self.store.get_run(run_id)
        turn = await self.store.get_turn(turn_id)
        if run is None or turn is None:
            raise app_error(
                "Agent run or turn was not found",
                code="agent.run.not_found",
                category="validation",
                status_code=404,
                details={"run_id": run_id, "turn_id": turn_id},
                operation="agent.process_turn",
                component="agent",
            )
        definition = self.agents.require(run.profile_name)
        if run.prompt is None:
            run.prompt = definition.effective_prompt_ref()
        if turn.prompt is None:
            turn.prompt = run.prompt
        started_at = perf_counter()
        await self._mark_running(run=run, turn=turn)
        if self.sessions is not None:
            await self.sessions.mark_running(run=run)
        self.observability.on_agent_turn_execution_started(profile_name=run.profile_name)
        try:
            with self.observability.start_agent_turn_span(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                profile_name=run.profile_name,
                prompt=turn.prompt,
                request_id=run.request_id,
                trace_id=run.trace_id,
            ) as span:
                try:
                    result = await self._run_pipeline(run=run, turn=turn, definition=definition)
                except asyncio.CancelledError:
                    await self._mark_cancelled(run=run, turn=turn)
                    self.observability.finish_agent_turn_span(
                        span,
                        run_id=run.run_id,
                        turn_id=turn.turn_id,
                        profile_name=run.profile_name,
                        status=run.status.value,
                        error_type="CancelledError",
                    )
                    raise
                except Exception as exc:
                    structured = (
                        exc
                        if isinstance(exc, AppError)
                        else internal_error(
                            "Generic-agent turn failed unexpectedly",
                            code="agent.turn.failed_unexpected",
                            details={"run_id": run.run_id, "turn_id": turn.turn_id},
                            operation="agent.process_turn",
                            component="agent",
                            exc=exc,
                        )
                    )
                    await self._mark_failed(run=run, turn=turn, exc=structured)
                    self.observability.finish_agent_turn_span(
                        span,
                        run_id=run.run_id,
                        turn_id=turn.turn_id,
                        profile_name=run.profile_name,
                        status=run.status.value,
                        error_type=structured.__class__.__name__,
                    )
                    raise structured from exc
                if result.get("awaiting_approval") is True:
                    await self._mark_awaiting_approval(run=run, turn=turn)
                    self.observability.finish_agent_turn_span(
                        span,
                        run_id=run.run_id,
                        turn_id=turn.turn_id,
                        profile_name=run.profile_name,
                        status=run.status.value,
                        error_type=None,
                    )
                    return
                response_text = str(result.get("response_text", "")).strip()
                await self._mark_completed(run=run, turn=turn, response_text=response_text)
                self.observability.finish_agent_turn_span(
                    span,
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    profile_name=run.profile_name,
                    status=run.status.value,
                    error_type=None,
                )
        finally:
            self.observability.on_agent_turn_execution_finished(
                profile_name=run.profile_name,
                status=run.status.value,
                duration_seconds=perf_counter() - started_at,
            )

    async def _run_pipeline(self, *, run: AgentRun, turn: AgentTurn, definition: Any) -> dict[str, object]:
        if not self.workflow_runtime.installed:
            raise app_error(
                "Workflow runtime is not available for generic-agent execution",
                code="agent.workflow.unavailable",
                category="workflow",
                status_code=503,
                details={"engine": self.workflow_runtime.engine_name},
                operation="agent.pipeline.run",
                component="agent",
            )
        if self.workflow_runtime.pipeline_factory is None:
            raise app_error(
                "Workflow pipeline factory is not available for generic-agent execution",
                code="agent.workflow.pipeline_factory_missing",
                category="workflow",
                status_code=503,
                details={"engine": self.workflow_runtime.engine_name},
                operation="agent.pipeline.run",
                component="agent",
            )

        async def run_agent_loop(_ctx: Any) -> dict[str, object]:
            return await self._run_agent_loop(run=run, turn=turn, definition=definition)

        pipeline = self.workflow_runtime.pipeline_factory.create_pipeline(
            name="generic_agent_turn",
            stages=[
                WorkflowStageSpec(
                    name="run_agent_loop",
                    handler=run_agent_loop,
                    kind=WorkflowStageKind.WORK,
                )
            ],
        )
        self._logger.info(
            "agent.turn.pipeline.started",
            run_id=run.run_id,
            turn_id=turn.turn_id,
            profile_name=run.profile_name,
            **self._prompt_fields(turn.prompt),
        )
        try:
            results = await pipeline.run()
        except UnifiedStageExecutionError as exc:
            if isinstance(exc.original, AppError):
                raise exc.original from exc
            raise
        output = results["run_agent_loop"].data
        self._logger.info(
            "agent.turn.pipeline.completed",
            run_id=run.run_id,
            turn_id=turn.turn_id,
            profile_name=run.profile_name,
            **self._prompt_fields(turn.prompt),
        )
        return dict(output)

    async def _run_agent_loop(self, *, run: AgentRun, turn: AgentTurn, definition: Any) -> dict[str, object]:
        if not self.llm_provider.is_configured():
            return {
                "awaiting_approval": False,
                "response_text": definition.build_fallback_response(turn.input_text),
                "provider": "fallback",
                "model": "deterministic-noop",
            }

        prompt_messages = definition.build_messages(turn.input_text)
        session_context = await self._build_session_context_messages(run=run, turn=turn)
        if prompt_messages and prompt_messages[0].role == "system":
            contextual_messages = [prompt_messages[0], *session_context, *prompt_messages[1:]]
        else:
            contextual_messages = [*session_context, *prompt_messages]
        messages = [item.model_dump(mode="json") for item in contextual_messages]
        existing_tool_calls = await self.store.list_tool_calls(run.run_id, turn.turn_id)
        messages.extend(self._replay_tool_messages(existing_tool_calls))

        resumed = await self._continue_existing_tool_calls(
            run=run,
            turn=turn,
            definition=definition,
            messages=messages,
            tool_calls=existing_tool_calls,
        )
        if resumed.get("awaiting_approval") is True:
            return resumed

        failed_tool_attempts = 0
        tool_retry_budget_exhausted = False
        for tool_iteration in range(1, self.config.max_tool_iterations + 1):
            completion = await self._complete_with_retry(
                run=run,
                turn=turn,
                definition=definition,
                messages=messages,
                tool_iteration=tool_iteration,
                allow_tools=not tool_retry_budget_exhausted,
            )
            if not completion.tool_calls:
                final_response = (completion.content or "").strip()
                return {
                    "awaiting_approval": False,
                    "response_text": final_response,
                    "provider": completion.provider,
                    "model": completion.model,
                }

            persisted_tool_calls = await self._queue_provider_tool_calls(
                run=run,
                turn=turn,
                definition=definition,
                tool_calls=completion.tool_calls,
            )
            messages.append(
                self._assistant_tool_call_message(
                    tool_calls=completion.tool_calls,
                    content=completion.content,
                )
            )

            execution_result = await self._continue_existing_tool_calls(
                run=run,
                turn=turn,
                definition=definition,
                messages=messages,
                tool_calls=persisted_tool_calls,
                failed_tool_attempts=failed_tool_attempts,
            )
            if execution_result.get("awaiting_approval") is True:
                return execution_result
            failed_tool_attempts = _safe_int(execution_result.get("failed_tool_attempts"), failed_tool_attempts)
            budget_exhausted_now = bool(
                execution_result.get("tool_retry_budget_exhausted", tool_retry_budget_exhausted)
            )
            if budget_exhausted_now and not tool_retry_budget_exhausted:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "The maximum governed-tool retry budget for this turn has been reached. "
                            "Do not call any more tools. Use the tool failure details already in the "
                            "conversation to explain the limitation and answer as helpfully as possible "
                            "without additional tool use."
                        ),
                    }
                )
            tool_retry_budget_exhausted = budget_exhausted_now

        raise app_error(
            "Agent exceeded the maximum native tool-calling iterations",
            code="agent.tool.max_iterations_exceeded",
            category="workflow",
            status_code=502,
            details={
                "run_id": run.run_id,
                "turn_id": turn.turn_id,
                "max_tool_iterations": self.config.max_tool_iterations,
            },
            operation="agent.loop",
            component="agent",
        )

    async def _complete_with_retry(
        self,
        *,
        run: AgentRun,
        turn: AgentTurn,
        definition: Any,
        messages: list[dict[str, object]],
        tool_iteration: int,
        allow_tools: bool,
    ) -> ToolCallCompletionResult:
        max_attempts = self.config.max_llm_completion_retries + 1
        for llm_attempt in range(1, max_attempts + 1):
            streamed_text = False

            async def on_text_delta(delta: str) -> None:
                nonlocal streamed_text
                if delta:
                    streamed_text = True
                await self._append_response_delta(run=run, turn=turn, delta=delta)

            try:
                completion = await self.llm_provider.complete_with_tools(
                    messages,
                    tools=definition.tools.provider_definitions() if allow_tools else [],
                    context=LLMCallContext(
                        request_id=run.request_id,
                        trace_id=run.trace_id,
                        actor_id=run.actor_id,
                        operation="agent.llm.complete_with_tools",
                        prompt=turn.prompt,
                    ),
                    on_text_delta=on_text_delta,
                )
            except AppError as exc:
                decision = decide_llm_retry(
                    issue=provider_error_issue(
                        exc,
                        retryable=exc.retryable and not streamed_text,
                        details={
                            "run_id": run.run_id,
                            "turn_id": turn.turn_id,
                            "tool_iteration": tool_iteration,
                            "streamed_text": streamed_text,
                        },
                    ),
                    attempt=llm_attempt,
                    max_attempts=max_attempts,
                )
                await self._append_event(
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    event_type="agent.attempt.provider_failed",
                    severity="warning",
                    code=decision.issue.code,
                    payload={
                        "turn_id": turn.turn_id,
                        "tool_iteration": tool_iteration,
                        "llm_attempt": llm_attempt,
                        "max_attempts": max_attempts,
                        "streamed_text": streamed_text,
                        "error": exc.to_dict(),
                    },
                )
                if decision.should_retry:
                    await self._append_event(
                        run_id=run.run_id,
                        turn_id=turn.turn_id,
                        event_type="agent.attempt.retry_scheduled",
                        severity="warning",
                        code="agent.attempt.retry_scheduled",
                        payload={
                            "turn_id": turn.turn_id,
                            "tool_iteration": tool_iteration,
                            "llm_attempt": llm_attempt,
                            "next_attempt": decision.next_attempt,
                            "max_attempts": max_attempts,
                            "issue_kind": decision.issue.kind.value,
                            "issue_code": decision.issue.code,
                        },
                    )
                    continue
                raise

            if completion.tool_calls or (completion.content or "").strip():
                return completion

            decision = decide_llm_retry(
                issue=empty_completion_issue(
                    code="agent.provider.empty_completion",
                    message="Agent provider returned neither tool calls nor a final response",
                    details={
                        "run_id": run.run_id,
                        "turn_id": turn.turn_id,
                        "tool_iteration": tool_iteration,
                        "provider": completion.provider,
                        "model": completion.model,
                        "max_llm_completion_retries": self.config.max_llm_completion_retries,
                    },
                    retry_prompt_message=(
                        "The previous completion was empty: no tool calls and no final answer. "
                        "Retry now. For in-scope data requests, either call the governed SQL tool "
                        "or provide a direct final answer grounded in the approved schema."
                    ),
                ),
                attempt=llm_attempt,
                max_attempts=max_attempts,
            )
            await self._append_event(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                event_type="agent.attempt.empty_completion",
                severity="warning",
                code=decision.issue.code,
                payload={
                    "turn_id": turn.turn_id,
                    "tool_iteration": tool_iteration,
                    "llm_attempt": llm_attempt,
                    "max_attempts": max_attempts,
                    "provider": completion.provider,
                    "model": completion.model,
                },
            )
            if decision.should_retry:
                await self._append_event(
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    event_type="agent.attempt.retry_scheduled",
                    severity="warning",
                    code="agent.attempt.retry_scheduled",
                    payload={
                        "turn_id": turn.turn_id,
                        "tool_iteration": tool_iteration,
                        "llm_attempt": llm_attempt,
                        "next_attempt": decision.next_attempt,
                        "max_attempts": max_attempts,
                        "issue_kind": decision.issue.kind.value,
                        "issue_code": decision.issue.code,
                    },
                )
                if decision.issue.retry_prompt_message is not None:
                    messages.append(
                        {
                            "role": "system",
                            "content": decision.issue.retry_prompt_message,
                        }
                    )
                continue
            raise app_error(
                decision.issue.message,
                code=decision.issue.code,
                category="provider",
                status_code=502,
                details=decision.issue.details,
                operation="agent.llm.complete_with_tools",
                component="agent",
            )
        raise internal_error(
            "Agent completion retry loop exhausted without returning or failing",
            code="agent.llm.retry_loop_exhausted",
            details={
                "run_id": run.run_id,
                "turn_id": turn.turn_id,
                "tool_iteration": tool_iteration,
                "max_attempts": max_attempts,
            },
            operation="agent.llm.complete_with_tools",
            component="agent",
        )

    async def _build_session_context_messages(self, *, run: AgentRun, turn: AgentTurn) -> list[ChatMessage]:
        if run.session_id is None or self.session_store is None:
            return []

        summary = await self.session_store.get_latest_summary(run.session_id)
        items = await self.session_store.list_items(run.session_id)
        prior_items = self._prior_message_items(items=items, current_input=turn.input_text)

        messages: list[ChatMessage] = []
        if summary is not None and summary.status.value == "completed" and summary.summary_text.strip():
            messages.append(
                ChatMessage(
                    role="system",
                    content=(
                        "Conversation summary for older turns. Treat this as historical context, "
                        "not as fresh evidence unless confirmed by tool results in this turn.\n"
                        f"{summary.summary_text.strip()}"
                    ),
                )
            )
            prior_items = [
                item for item in prior_items if item.sequence_no > summary.coverage_end_sequence
            ]

        recent_items = prior_items[-16:]
        for item in recent_items:
            if item.item_type == SessionItemType.USER_MESSAGE:
                text = item.payload.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(ChatMessage(role="user", content=text))
            elif item.item_type == SessionItemType.ASSISTANT_MESSAGE:
                text = item.payload.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(ChatMessage(role="assistant", content=text))
        return messages

    @staticmethod
    def _prior_message_items(*, items: list[SessionItem], current_input: str) -> list[SessionItem]:
        message_items = [
            item
            for item in items
            if item.item_type in {SessionItemType.USER_MESSAGE, SessionItemType.ASSISTANT_MESSAGE}
        ]
        if not message_items:
            return []

        latest = message_items[-1]
        latest_text = latest.payload.get("text")
        if (
            latest.item_type == SessionItemType.USER_MESSAGE
            and isinstance(latest_text, str)
            and latest_text == current_input
        ):
            return message_items[:-1]
        return message_items

    async def _append_response_delta(self, *, run: AgentRun, turn: AgentTurn, delta: str) -> None:
        if not delta:
            return
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.response.delta",
            severity="info",
            code="agent.response.delta",
            payload={
                "turn_id": turn.turn_id,
                "delta": delta,
            },
        )

    async def _queue_provider_tool_calls(
        self,
        *,
        run: AgentRun,
        turn: AgentTurn,
        definition: Any,
        tool_calls: list[ProviderToolCall],
    ) -> list[AgentToolCall]:
        persisted: list[AgentToolCall] = []
        for provider_tool_call in tool_calls:
            try:
                tool_definition = definition.tools.require(provider_tool_call.tool_name)
            except AppError as exc:
                if exc.code != "agent.tool.not_found":
                    raise
                raise app_error(
                    "Provider requested an unregistered agent tool",
                    code="provider.invalid_tool_name",
                    category="provider",
                    status_code=502,
                    details={
                        "run_id": run.run_id,
                        "turn_id": turn.turn_id,
                        "tool_call_id": provider_tool_call.call_id,
                        "tool_name": provider_tool_call.tool_name,
                        "arguments": provider_tool_call.arguments,
                    },
                    operation="agent.tool.queue_provider_call",
                    component="agent",
                    exc=exc,
                ) from exc
            tool_call = AgentToolCall(
                tool_call_id=provider_tool_call.call_id,
                run_id=run.run_id,
                turn_id=turn.turn_id,
                sequence_no=await self.store.next_tool_sequence(run.run_id, turn.turn_id),
                tool_name=provider_tool_call.tool_name,
                status=(
                    AgentToolCallStatus.PENDING_APPROVAL
                    if tool_definition.requires_approval
                    else AgentToolCallStatus.QUEUED
                ),
                arguments=provider_tool_call.arguments,
                requires_approval=tool_definition.requires_approval,
                approval_id=new_id() if tool_definition.requires_approval else None,
            )
            await self._create_tool_call(tool_call)
            if self.sessions is not None:
                await self.sessions.append_tool_call(run=run, turn=turn, tool_call=tool_call)
            await self._append_event(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                event_type="agent.tool.queued",
                severity="info",
                code="agent.tool.queued",
                payload={
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_name": tool_call.tool_name,
                    "requires_approval": tool_call.requires_approval,
                    "approval_id": tool_call.approval_id,
                },
            )
            if tool_call.status == AgentToolCallStatus.PENDING_APPROVAL:
                self.observability.on_agent_tool_approval_requested(
                    profile_name=run.profile_name,
                    tool_name=tool_call.tool_name,
                )
                await self._append_event(
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    event_type="agent.approval.requested",
                    severity="warning",
                    code="agent.approval.requested",
                    payload={
                        "tool_call_id": tool_call.tool_call_id,
                        "tool_name": tool_call.tool_name,
                        "approval_id": tool_call.approval_id,
                    },
                )
            persisted.append(tool_call)
        return persisted

    async def _continue_existing_tool_calls(
        self,
        *,
        run: AgentRun,
        turn: AgentTurn,
        definition: Any,
        messages: list[dict[str, object]],
        tool_calls: list[AgentToolCall],
        failed_tool_attempts: int = 0,
    ) -> dict[str, object]:
        tool_retry_budget_exhausted = False
        for tool_call in tool_calls:
            if tool_call.status == AgentToolCallStatus.PENDING_APPROVAL:
                return {
                    "awaiting_approval": True,
                    "approval_id": tool_call.approval_id,
                    "tool_call_id": tool_call.tool_call_id,
                }
            if tool_call.status == AgentToolCallStatus.REJECTED:
                messages.append(
                    self._tool_result_message(
                        tool_call_id=tool_call.tool_call_id,
                        payload={"status": "rejected", "message": "Approval was rejected."},
                    )
                )
                continue
            if (
                tool_call.status == AgentToolCallStatus.COMPLETED
                and tool_call.result_payload is not None
            ):
                messages.append(
                    self._tool_result_message(
                        tool_call_id=tool_call.tool_call_id,
                        payload=tool_call.result_payload,
                    )
                )
                continue
            if tool_call.status == AgentToolCallStatus.FAILED:
                failed_tool_attempts, tool_retry_budget_exhausted = await self._append_failed_tool_result(
                    run=run,
                    turn=turn,
                    tool_call=tool_call,
                    messages=messages,
                    failed_tool_attempts=failed_tool_attempts,
                )
                continue
            if tool_call.status not in {
                AgentToolCallStatus.QUEUED,
                AgentToolCallStatus.APPROVED,
            }:
                continue
            validated_arguments = definition.tools.require(tool_call.tool_name).validate_provider_arguments(
                arguments=tool_call.arguments,
                tool_call_id=tool_call.tool_call_id,
                run_id=run.run_id,
                turn_id=turn.turn_id,
            )
            if validated_arguments != tool_call.arguments:
                tool_call.arguments = validated_arguments
                await self._update_tool_call(tool_call)
            tool_failure = await self._execute_tool_call(
                run=run,
                turn=turn,
                tool_call=tool_call,
                definition=definition,
            )
            refreshed = await self._require_tool_call(
                tool_call.tool_call_id,
                run_id=run.run_id,
                turn_id=turn.turn_id,
            )
            if refreshed.result_payload is not None:
                messages.append(
                    self._tool_result_message(
                        tool_call_id=refreshed.tool_call_id,
                        payload=refreshed.result_payload,
                    )
                )
                continue
            if refreshed.status == AgentToolCallStatus.FAILED and tool_failure is not None:
                failed_tool_attempts, tool_retry_budget_exhausted = await self._append_failed_tool_result(
                    run=run,
                    turn=turn,
                    tool_call=refreshed,
                    messages=messages,
                    failed_tool_attempts=failed_tool_attempts,
                )
        return {
            "awaiting_approval": False,
            "failed_tool_attempts": failed_tool_attempts,
            "tool_retry_budget_exhausted": tool_retry_budget_exhausted,
        }

    async def _execute_tool_call(
        self, *, run: AgentRun, turn: AgentTurn, tool_call: AgentToolCall, definition: Any
    ) -> AppError | None:
        started_at = perf_counter()
        tool_call.status = AgentToolCallStatus.RUNNING
        tool_call.started_at = utc_now()
        await self._update_tool_call(tool_call)
        self.observability.on_agent_tool_call_started(
            profile_name=run.profile_name,
            tool_name=tool_call.tool_name,
        )
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.tool.started",
            severity="info",
            code="agent.tool.started",
            payload={"tool_call_id": tool_call.tool_call_id, "tool_name": tool_call.tool_name},
        )
        try:
            with self.observability.start_agent_tool_span(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                tool_call_id=tool_call.tool_call_id,
                profile_name=run.profile_name,
                tool_name=tool_call.tool_name,
                request_id=run.request_id,
                trace_id=run.trace_id,
            ) as span:
                try:
                    result = await definition.tools.execute(
                        name=tool_call.tool_name,
                        arguments=tool_call.arguments,
                        context=AgentToolExecutionContext(
                            request_id=run.request_id,
                            trace_id=run.trace_id,
                            actor_id=run.actor_id,
                        ),
                    )
                except Exception as exc:
                    expected_tool_failure = isinstance(exc, AppError)
                    structured = (
                        exc
                        if expected_tool_failure
                        else internal_error(
                            "Agent tool execution failed unexpectedly",
                            code="agent.tool.failed_unexpected",
                            details={
                                "tool_name": tool_call.tool_name,
                                "run_id": run.run_id,
                                "turn_id": turn.turn_id,
                            },
                            operation="agent.tool.execute",
                            component="agent",
                            exc=exc,
                        )
                    )
                    tool_call.status = AgentToolCallStatus.FAILED
                    tool_call.completed_at = utc_now()
                    tool_call.error_code = structured.code  # type: ignore[attr-defined]
                    tool_call.error_category = structured.category  # type: ignore[attr-defined]
                    tool_call.error_message = structured.message  # type: ignore[attr-defined]
                    tool_call.error_details = structured.to_dict()  # type: ignore[attr-defined]
                    await self._update_tool_call(tool_call)
                    if self.sessions is not None:
                        await self.sessions.append_tool_result(run=run, turn=turn, tool_call=tool_call)
                    await self._append_event(
                        run_id=run.run_id,
                        turn_id=turn.turn_id,
                        event_type="agent.tool.failed",
                        severity=structured.severity,  # type: ignore[attr-defined]
                        code=structured.code,  # type: ignore[attr-defined]
                        payload={
                            "tool_call_id": tool_call.tool_call_id,
                            "tool_name": tool_call.tool_name,
                            "error": structured.to_dict(),  # type: ignore[attr-defined]
                        },
                    )
                    self.observability.finish_agent_tool_span(
                        span,
                        run_id=run.run_id,
                        turn_id=turn.turn_id,
                        tool_call_id=tool_call.tool_call_id,
                        profile_name=run.profile_name,
                        tool_name=tool_call.tool_name,
                        status=tool_call.status.value,
                        error_type=structured.__class__.__name__,
                    )
                    if expected_tool_failure:
                        return structured  # type: ignore[return-value]
                    raise structured from exc
                tool_call.status = AgentToolCallStatus.COMPLETED
                tool_call.completed_at = utc_now()
                tool_call.result_payload = result
                await self._update_tool_call(tool_call)
                if self.sessions is not None:
                    await self.sessions.append_tool_result(run=run, turn=turn, tool_call=tool_call)
                await self._append_event(
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    event_type="agent.tool.completed",
                    severity="info",
                    code="agent.tool.completed",
                    payload={
                        "tool_call_id": tool_call.tool_call_id,
                        "tool_name": tool_call.tool_name,
                        "result": result,
                    },
                )
                self.observability.finish_agent_tool_span(
                    span,
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    tool_call_id=tool_call.tool_call_id,
                    profile_name=run.profile_name,
                    tool_name=tool_call.tool_name,
                    status=tool_call.status.value,
                    error_type=None,
                )
                return None
        finally:
            self.observability.on_agent_tool_call_finished(
                profile_name=run.profile_name,
                tool_name=tool_call.tool_name,
                status=tool_call.status.value,
                duration_seconds=perf_counter() - started_at,
            )

    async def _append_failed_tool_result(
        self,
        *,
        run: AgentRun,
        turn: AgentTurn,
        tool_call: AgentToolCall,
        messages: list[dict[str, object]],
        failed_tool_attempts: int,
    ) -> tuple[int, bool]:
        next_failed_attempts = failed_tool_attempts + 1
        messages.append(
            self._tool_result_message(
                tool_call_id=tool_call.tool_call_id,
                payload=self._tool_failure_payload(tool_call),
            )
        )
        if next_failed_attempts > self.config.max_tool_execution_retries:
            await self._append_event(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                event_type="agent.tool.retry_limit_exceeded",
                severity="warning",
                code="agent.tool.max_retries_exceeded",
                payload={
                    "turn_id": turn.turn_id,
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_name": tool_call.tool_name,
                    "failed_tool_attempts": next_failed_attempts,
                    "max_tool_execution_retries": self.config.max_tool_execution_retries,
                    "last_error": tool_call.error_details,
                },
            )
            messages.append(
                self._tool_result_message(
                    tool_call_id=tool_call.tool_call_id,
                    payload={
                        "status": "retry_budget_exhausted",
                        "tool_name": tool_call.tool_name,
                        "error_code": "agent.tool.max_retries_exceeded",
                        "error_message": (
                            "The maximum governed-tool retry budget for this turn has been reached."
                        ),
                        "error": {
                            "code": "agent.tool.max_retries_exceeded",
                            "category": "workflow",
                            "details": {
                                "run_id": run.run_id,
                                "turn_id": turn.turn_id,
                                "tool_call_id": tool_call.tool_call_id,
                                "tool_name": tool_call.tool_name,
                                "failed_tool_attempts": next_failed_attempts,
                                "max_tool_execution_retries": self.config.max_tool_execution_retries,
                                "last_error": tool_call.error_details,
                            },
                        },
                        "instruction": (
                            "Do not call any more tools for this turn. Explain that the governed "
                            "tool retry budget has been exhausted and summarize the latest failure."
                        ),
                    },
                )
            )
            return next_failed_attempts, True
        return next_failed_attempts, False

    async def _mark_running(self, *, run: AgentRun, turn: AgentTurn) -> None:
        now = utc_now()
        run.status = AgentRunStatus.RUNNING
        run.started_at = run.started_at or now
        run.updated_at = now
        run.latest_turn_id = turn.turn_id
        turn.status = AgentTurnStatus.RUNNING
        turn.started_at = turn.started_at or now
        await self.store.update_run(run)
        await self.store.update_turn(turn)
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.turn.started",
            severity="info",
            code="agent.turn.started",
            payload={"turn_id": turn.turn_id, "sequence_no": turn.sequence_no},
        )

    async def _create_tool_call(self, tool_call: AgentToolCall) -> None:
        try:
            await self.store.create_tool_call(tool_call)
        except AppError:
            raise
        except Exception as exc:
            raise app_error(
                "Failed to persist agent tool call state",
                code="data.agent_tool_call.create_failed",
                category="data",
                status_code=500,
                details={
                    "run_id": tool_call.run_id,
                    "turn_id": tool_call.turn_id,
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_name": tool_call.tool_name,
                    "status": tool_call.status.value,
                },
                operation="agent.tool.create_state",
                component="agent",
                exc=exc,
            ) from exc

    async def _update_tool_call(self, tool_call: AgentToolCall) -> None:
        try:
            await self.store.update_tool_call(tool_call)
        except AppError:
            raise
        except Exception as exc:
            raise app_error(
                "Failed to update agent tool call state",
                code="data.agent_tool_call.update_failed",
                category="data",
                status_code=500,
                details={
                    "run_id": tool_call.run_id,
                    "turn_id": tool_call.turn_id,
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_name": tool_call.tool_name,
                    "status": tool_call.status.value,
                },
                operation="agent.tool.update_state",
                component="agent",
                exc=exc,
            ) from exc

    async def _mark_awaiting_approval(self, *, run: AgentRun, turn: AgentTurn) -> None:
        now = utc_now()
        run.status = AgentRunStatus.AWAITING_APPROVAL
        run.updated_at = now
        turn.status = AgentTurnStatus.AWAITING_APPROVAL
        await self.store.update_run(run)
        await self.store.update_turn(turn)
        if self.sessions is not None:
            await self.sessions.mark_awaiting_approval(run=run)
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.turn.awaiting_approval",
            severity="warning",
            code="agent.turn.awaiting_approval",
            payload={"turn_id": turn.turn_id},
        )

    async def _mark_completed(self, *, run: AgentRun, turn: AgentTurn, response_text: str) -> None:
        now = utc_now()
        run.status = AgentRunStatus.COMPLETED
        run.updated_at = now
        run.completed_at = now
        run.error_code = None
        run.error_category = None
        run.error_message = None
        run.error_details = None
        turn.status = AgentTurnStatus.COMPLETED
        turn.completed_at = now
        turn.response_text = response_text
        turn.error_code = None
        turn.error_category = None
        turn.error_message = None
        turn.error_details = None
        await self.store.update_turn(turn)
        await self.store.update_run(run)
        if self.sessions is not None:
            await self.sessions.append_assistant_message(run=run, turn=turn, response_text=response_text)
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.turn.completed",
            severity="info",
            code="agent.turn.completed",
            payload={"turn_id": turn.turn_id, "response_text": response_text},
        )

    async def _mark_cancelled(self, *, run: AgentRun, turn: AgentTurn) -> None:
        now = utc_now()
        run.status = AgentRunStatus.CANCELLED
        run.updated_at = now
        run.completed_at = now
        turn.status = AgentTurnStatus.CANCELLED
        turn.completed_at = now
        await self.store.update_turn(turn)
        await self.store.update_run(run)
        if self.sessions is not None:
            await self.sessions.mark_cancelled(run=run)
        for tool_call in await self.store.list_tool_calls(run.run_id, turn.turn_id):
            if tool_call.status in {
                AgentToolCallStatus.QUEUED,
                AgentToolCallStatus.RUNNING,
                AgentToolCallStatus.APPROVED,
            }:
                tool_call.status = AgentToolCallStatus.CANCELLED
                tool_call.completed_at = now
                await self.store.update_tool_call(tool_call)
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.turn.cancelled",
            severity="warning",
            code="agent.turn.cancelled",
            payload={"turn_id": turn.turn_id},
        )

    async def _mark_failed(self, *, run: AgentRun, turn: AgentTurn, exc: Exception) -> None:
        structured = (
            exc
            if isinstance(exc, AppError)
            else internal_error(
                "Generic-agent turn failed unexpectedly",
                code="agent.turn.failed_unexpected",
                details={"run_id": run.run_id, "turn_id": turn.turn_id},
                operation="agent.process_turn",
                component="agent",
                exc=exc,
            )
        )
        now = utc_now()
        run.status = AgentRunStatus.FAILED
        run.updated_at = now
        run.completed_at = now
        run.error_code = structured.code
        run.error_category = structured.category
        run.error_message = structured.message
        run.error_details = structured.to_dict()
        turn.status = AgentTurnStatus.FAILED
        turn.completed_at = now
        turn.error_code = structured.code
        turn.error_category = structured.category
        turn.error_message = structured.message
        turn.error_details = structured.to_dict()
        await self.store.update_turn(turn)
        await self.store.update_run(run)
        if self.sessions is not None:
            await self.sessions.mark_failed(
                run=run,
                error_code=structured.code,
                error_message=structured.message,
            )
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.turn.failed",
            severity=structured.severity,
            code=structured.code,
            payload={"turn_id": turn.turn_id, "error": structured.to_dict()},
        )
        self._logger.error(
            "agent.turn.failed",
            run_id=run.run_id,
            turn_id=turn.turn_id,
            profile_name=run.profile_name,
            code=structured.code,
            **self._prompt_fields(turn.prompt),
        )

    async def _append_event(
        self,
        *,
        run_id: str,
        turn_id: str | None,
        event_type: str,
        severity: str,
        payload: dict[str, object],
        code: str | None = None,
    ) -> None:
        run = await self.store.get_run(run_id)
        turn = await self.store.get_turn(turn_id) if turn_id is not None else None
        prompt_payload = self._prompt_fields(turn.prompt if turn is not None else None)
        merged_payload = {**prompt_payload, **payload}
        await self.store.append_event(
            AgentStreamEvent(
                event_id=new_id(),
                run_id=run_id,
                turn_id=turn_id,
                sequence_no=await self.store.next_event_sequence(run_id),
                event_type=event_type,
                severity=severity,
                request_id=run.request_id if run is not None else None,
                trace_id=run.trace_id if run is not None else None,
                actor_id=run.actor_id if run is not None else None,
                payload=merged_payload,
                code=code,
            )
        )
        if run is not None and event_type != "agent.response.delta":
            await self.observability.emit(
                OperationalEvent(
                    event_type=event_type,
                    severity=severity,
                    component="agent",
                    operation=run.profile_name,
                    correlation_id=run.request_id,
                    trace_id=run.trace_id,
                    code=code,
                    payload={
                        "run_id": run.run_id,
                        "turn_id": turn_id,
                        "profile_name": run.profile_name,
                        "severity": severity,
                        "code": code,
                        "message": event_type,
                        **json.loads(json.dumps(merged_payload)),
                    },
                )
            )

    @staticmethod
    def _assistant_tool_call_message(
        *, tool_calls: list[ProviderToolCall], content: str | None
    ) -> dict[str, object]:
        return {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {
                    "id": tool_call.call_id,
                    "type": "function",
                    "function": {
                        "name": tool_call.tool_name,
                        "arguments": json.dumps(tool_call.arguments, separators=(",", ":"), sort_keys=True),
                    },
                }
                for tool_call in tool_calls
            ],
        }

    @staticmethod
    def _tool_result_message(
        *, tool_call_id: str, payload: dict[str, object]
    ) -> dict[str, object]:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(payload, separators=(",", ":"), sort_keys=True),
        }

    @staticmethod
    def _tool_failure_payload(tool_call: AgentToolCall) -> dict[str, object]:
        return {
            "status": "failed",
            "tool_name": tool_call.tool_name,
            "error_code": tool_call.error_code,
            "error_message": tool_call.error_message,
            "error": tool_call.error_details,
            "retryable": False,
            "instruction": (
                "The tool call failed. Inspect the error details, correct the arguments, "
                "and only retry the tool if you can fix the failure."
            ),
        }

    def _replay_tool_messages(self, tool_calls: list[AgentToolCall]) -> list[dict[str, object]]:
        replay: list[dict[str, object]] = []
        for tool_call in tool_calls:
            replay.append(
                self._assistant_tool_call_message(
                    tool_calls=[
                        ProviderToolCall(
                            call_id=tool_call.tool_call_id,
                            tool_name=tool_call.tool_name,
                            arguments=tool_call.arguments,
                        )
                    ],
                    content=None,
                )
            )
        return replay

    @staticmethod
    def _prompt_fields(prompt: EffectivePromptRef | None) -> dict[str, object]:
        if prompt is None:
            return {}
        payload: dict[str, object] = {
            "prompt_id": prompt.prompt_id,
            "prompt_version": prompt.version,
            "prompt_owner_kind": prompt.owner_kind,
            "prompt_owner_id": prompt.owner_id,
            "prompt_purpose": prompt.purpose,
        }
        checksum = prompt.checksum
        if checksum is not None:
            payload["prompt_checksum"] = checksum
        return payload

    async def _require_tool_call(
        self, tool_call_id: str, *, run_id: str, turn_id: str
    ) -> AgentToolCall:
        for tool_call in await self.store.list_tool_calls(run_id, turn_id):
            if tool_call.tool_call_id == tool_call_id:
                return tool_call
        raise app_error(
            "Agent tool call is missing after execution",
            code="agent.tool.missing_state",
            category="internal",
            status_code=500,
            details={"tool_call_id": tool_call_id, "run_id": run_id, "turn_id": turn_id},
            operation="agent.tool.require_state",
            component="agent",
        )
