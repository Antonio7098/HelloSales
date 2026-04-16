"""Stageflow-backed agent runtime."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

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
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.platform.providers.llm.contracts import ChatModelPort
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
    llm_provider: ChatModelPort
    store: AgentStorePort
    agents: AgentRegistry
    observability: ObservabilityRuntime
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
        await self._mark_running(run=run, turn=turn)
        try:
            definition = self.agents.require(run.profile_name)
            result = await self._run_pipeline(run=run, turn=turn, definition=definition)
        except asyncio.CancelledError:
            await self._mark_cancelled(run=run, turn=turn)
            raise
        except Exception as exc:
            await self._mark_failed(run=run, turn=turn, exc=exc)
            raise
        if result.get("awaiting_approval") is True:
            await self._mark_awaiting_approval(run=run, turn=turn)
            return
        response_text = str(result.get("response_text", "")).strip()
        await self._mark_completed(run=run, turn=turn, response_text=response_text)

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

        async def prepare_turn(_ctx: Any) -> dict[str, object]:
            existing_calls = await self.store.list_tool_calls(run.run_id, turn.turn_id)
            if existing_calls:
                awaiting = any(item.status == AgentToolCallStatus.PENDING_APPROVAL for item in existing_calls)
                return {
                    "awaiting_approval": awaiting,
                    "tool_call_ids": [item.tool_call_id for item in existing_calls],
                }

            selected_tools = definition.selection_policy.select(turn.input_text, definition.tools)
            for request in selected_tools:
                tool_definition = definition.tools.require(request.name)
                tool_call = AgentToolCall(
                    tool_call_id=new_id(),
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    sequence_no=await self.store.next_tool_sequence(run.run_id, turn.turn_id),
                    tool_name=request.name,
                    status=(
                        AgentToolCallStatus.PENDING_APPROVAL
                        if tool_definition.requires_approval
                        else AgentToolCallStatus.QUEUED
                    ),
                    arguments=request.arguments,
                    requires_approval=tool_definition.requires_approval,
                    approval_id=new_id() if tool_definition.requires_approval else None,
                )
                await self.store.create_tool_call(tool_call)
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
            return {
                "awaiting_approval": any(definition.tools.require(item.name).requires_approval for item in selected_tools),
            }

        async def execute_tools(_ctx: Any) -> dict[str, object]:
            tool_calls = await self.store.list_tool_calls(run.run_id, turn.turn_id)
            pending_approval = next(
                (item for item in tool_calls if item.status == AgentToolCallStatus.PENDING_APPROVAL),
                None,
            )
            if pending_approval is not None:
                return {
                    "awaiting_approval": True,
                    "approval_id": pending_approval.approval_id,
                    "tool_results": [],
                }
            tool_results: list[str] = []
            for tool_call in tool_calls:
                if tool_call.status == AgentToolCallStatus.COMPLETED and tool_call.result_payload is not None:
                    tool_results.append(self._tool_result_summary(tool_call))
                    continue
                if tool_call.status == AgentToolCallStatus.REJECTED:
                    tool_results.append(f"{tool_call.tool_name}: approval rejected")
                    continue
                await self._execute_tool_call(run=run, turn=turn, tool_call=tool_call, definition=definition)
                refreshed = await self._require_tool_call(tool_call.tool_call_id, turn_id=turn.turn_id, run_id=run.run_id)
                if refreshed.result_payload is not None:
                    tool_results.append(self._tool_result_summary(refreshed))
            return {"awaiting_approval": False, "tool_results": tool_results}

        async def generate_response(ctx: Any) -> dict[str, object]:
            executed = ctx.inputs.get_output("execute_tools")
            if executed is None:
                raise RuntimeError("Generic-agent execute_tools output is missing")
            result: dict[str, object] = executed.data
            if result.get("awaiting_approval") is True:
                return result
            tool_results_raw = result.get("tool_results", [])
            tool_results = [str(item) for item in tool_results_raw] if isinstance(tool_results_raw, list) else []
            if self.llm_provider.is_configured():
                messages = definition.build_messages(turn.input_text, tool_results)
                completion = await self.llm_provider.generate(messages)
                return {
                    "awaiting_approval": False,
                    "response_text": completion.output_text,
                    "provider": completion.provider,
                    "model": completion.model,
                }
            return {
                "awaiting_approval": False,
                "response_text": definition.build_fallback_response(turn.input_text, tool_results),
                "provider": "fallback",
                "model": "deterministic-summary",
            }

        pipeline = self.workflow_runtime.pipeline_factory.create_pipeline(
            name="generic_agent_turn",
            stages=[
                WorkflowStageSpec(name="prepare_turn", handler=prepare_turn, kind=WorkflowStageKind.GUARD),
                WorkflowStageSpec(
                    name="execute_tools",
                    handler=execute_tools,
                    kind=WorkflowStageKind.WORK,
                    dependencies=("prepare_turn",),
                ),
                WorkflowStageSpec(
                    name="generate_response",
                    handler=generate_response,
                    kind=WorkflowStageKind.TRANSFORM,
                    dependencies=("execute_tools",),
                ),
            ],
        )
        self._logger.info("agent.turn.pipeline.started", run_id=run.run_id, turn_id=turn.turn_id)
        try:
            results = await pipeline.run()
        except UnifiedStageExecutionError as exc:
            if isinstance(exc.original, AppError):
                raise exc.original from exc
            raise
        output = results["generate_response"].data
        self._logger.info("agent.turn.pipeline.completed", run_id=run.run_id, turn_id=turn.turn_id)
        return dict(output)

    async def _execute_tool_call(self, *, run: AgentRun, turn: AgentTurn, tool_call: AgentToolCall, definition: Any) -> None:
        tool_call.status = AgentToolCallStatus.RUNNING
        tool_call.started_at = utc_now()
        await self.store.update_tool_call(tool_call)
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.tool.started",
            severity="info",
            code="agent.tool.started",
            payload={"tool_call_id": tool_call.tool_call_id, "tool_name": tool_call.tool_name},
        )
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
            structured = exc if isinstance(exc, AppError) else internal_error(
                "Agent tool execution failed unexpectedly",
                code="agent.tool.failed_unexpected",
                details={"tool_name": tool_call.tool_name, "run_id": run.run_id, "turn_id": turn.turn_id},
                operation="agent.tool.execute",
                component="agent",
                exc=exc,
            )
            tool_call.status = AgentToolCallStatus.FAILED
            tool_call.completed_at = utc_now()
            tool_call.error_code = structured.code
            tool_call.error_category = structured.category
            tool_call.error_message = structured.message
            tool_call.error_details = structured.to_dict()
            await self.store.update_tool_call(tool_call)
            await self._append_event(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                event_type="agent.tool.failed",
                severity=structured.severity,
                code=structured.code,
                payload={
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_name": tool_call.tool_name,
                    "error": structured.to_dict(),
                },
            )
            raise structured from exc
        tool_call.status = AgentToolCallStatus.COMPLETED
        tool_call.completed_at = utc_now()
        tool_call.result_payload = result
        await self.store.update_tool_call(tool_call)
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

    async def _mark_awaiting_approval(self, *, run: AgentRun, turn: AgentTurn) -> None:
        now = utc_now()
        run.status = AgentRunStatus.AWAITING_APPROVAL
        run.updated_at = now
        turn.status = AgentTurnStatus.AWAITING_APPROVAL
        await self.store.update_run(run)
        await self.store.update_turn(turn)
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
        for tool_call in await self.store.list_tool_calls(run.run_id, turn.turn_id):
            if tool_call.status in {AgentToolCallStatus.QUEUED, AgentToolCallStatus.RUNNING, AgentToolCallStatus.APPROVED}:
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
        structured = exc if isinstance(exc, AppError) else internal_error(
            "Generic-agent turn failed unexpectedly",
            code="agent.turn.failed_unexpected",
            details={"run_id": run.run_id, "turn_id": turn.turn_id},
            operation="agent.process_turn",
            component="agent",
            exc=exc,
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
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.turn.failed",
            severity=structured.severity,
            code=structured.code,
            payload={"turn_id": turn.turn_id, "error": structured.to_dict()},
        )
        await self.observability.emit(
            OperationalEvent(
                event_type="agent.turn.failed",
                severity=structured.severity,
                component="agent",
                operation="agent.process_turn",
                correlation_id=run.request_id,
                trace_id=run.trace_id,
                code=structured.code,
                payload=structured.to_dict(),
            )
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
                payload=payload,
                code=code,
            )
        )

    async def _require_tool_call(self, tool_call_id: str, *, run_id: str, turn_id: str) -> AgentToolCall:
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

    @staticmethod
    def _tool_result_summary(tool_call: AgentToolCall) -> str:
        return f"{tool_call.tool_name}: {tool_call.result_payload}"
