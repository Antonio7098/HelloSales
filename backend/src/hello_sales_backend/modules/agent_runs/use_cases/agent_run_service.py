"""Agent-runs application service."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from hello_sales_backend.modules.agent_runs.use_cases.commands import (
    AppendAgentTurnCommand,
    ApprovalDecisionCommand,
    StartAgentRunCommand,
)
from hello_sales_backend.modules.agent_runs.use_cases.views import (
    AgentApprovalView,
    AgentEventView,
    AgentRunDetailView,
    AgentRunSummaryView,
    AgentToolCallView,
    AgentTurnView,
    PromptRefView,
)
from hello_sales_backend.platform.agents.contracts import AgentDefinitionResolverPort
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
from hello_sales_backend.platform.agents.runtime import AgentExecutionRuntime
from hello_sales_backend.platform.llm import EffectivePromptRef
from hello_sales_backend.platform.tasks.models import TaskMetadata, TaskStatus
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.shared.errors import app_error
from hello_sales_backend.shared.ids import new_id


class AgentRunService:
    """Expose operational generic-agent actions through a stable module facade."""

    def __init__(
        self,
        *,
        store: AgentStorePort,
        runtime: AgentExecutionRuntime,
        tasks: BackgroundTaskRunner,
        agents: AgentDefinitionResolverPort,
    ) -> None:
        self._store = store
        self._runtime = runtime
        self._tasks = tasks
        self._agents = agents

    async def start_run(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        session_id: str | None,
        command: StartAgentRunCommand,
    ) -> AgentRunSummaryView:
        run = AgentRun(
            run_id=new_id(),
            profile_name=command.profile_name,
            status=AgentRunStatus.PENDING,
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
            session_id=session_id,
            prompt=self._agents.require(command.profile_name).effective_prompt_ref(),
        )
        turn = AgentTurn(
            turn_id=new_id(),
            run_id=run.run_id,
            sequence_no=await self._store.next_turn_sequence(run.run_id),
            input_text=command.input_text,
            status=AgentTurnStatus.PENDING,
            prompt=run.prompt,
        )
        run.latest_turn_id = turn.turn_id
        await self._store.create_run(run)
        await self._store.create_turn(turn)
        self._schedule_turn(run=run, turn=turn)
        return self._run_summary_view(run)

    async def append_turn(
        self,
        *,
        run_id: str,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: AppendAgentTurnCommand,
    ) -> AgentRunSummaryView:
        run = await self._require_run(run_id)
        run = await self._recover_orphaned_run(run)
        if run.status in {AgentRunStatus.RUNNING, AgentRunStatus.AWAITING_APPROVAL}:
            raise app_error(
                "Agent run is not ready to accept another turn",
                code="agent.run.busy",
                category="validation",
                status_code=409,
                details={"run_id": run_id, "status": run.status.value},
                operation="agent_run.append_turn",
                component="agent",
            )
        if run.status == AgentRunStatus.CANCELLED:
            raise app_error(
                "Cancelled agent runs cannot accept more turns",
                code="agent.run.cancelled",
                category="validation",
                status_code=409,
                details={"run_id": run_id},
                operation="agent_run.append_turn",
                component="agent",
            )
        turn = AgentTurn(
            turn_id=new_id(),
            run_id=run_id,
            sequence_no=await self._store.next_turn_sequence(run_id),
            input_text=command.input_text,
            status=AgentTurnStatus.PENDING,
            prompt=run.prompt,
        )
        run.request_id = request_id or run.request_id
        run.trace_id = trace_id or run.trace_id
        run.actor_id = actor_id or run.actor_id
        run.latest_turn_id = turn.turn_id
        run.status = AgentRunStatus.PENDING
        run.updated_at = utc_now()
        await self._store.update_run(run)
        await self._store.create_turn(turn)
        self._schedule_turn(run=run, turn=turn)
        return self._run_summary_view(run)

    async def get_run(self, run_id: str) -> AgentRunDetailView | None:
        run = await self._store.get_run(run_id)
        if run is None:
            return None
        turns = await self._store.list_turns(run_id)
        detailed_turns: list[AgentTurnView] = []
        for turn in turns:
            detailed_turns.append(
                self._turn_view(turn, await self._store.list_tool_calls(run_id, turn.turn_id))
            )
        return AgentRunDetailView(
            **self._run_summary_view(run).model_dump(),
            turns=detailed_turns,
        )

    async def list_events(self, run_id: str, *, limit: int = 100) -> list[AgentEventView]:
        return [
            AgentEventView(
                event_id=item.event_id,
                sequence_no=item.sequence_no,
                event_type=item.event_type,
                severity=item.severity,
                code=item.code,
                turn_id=item.turn_id,
                payload=item.payload,
                created_at=item.created_at.isoformat(),
            )
            for item in await self._store.list_events(run_id, limit=limit)
        ]

    async def observe_events(
        self,
        run_id: str,
        *,
        after_sequence: int = 0,
        poll_interval_seconds: float = 0.05,
    ) -> AsyncIterator[AgentEventView]:
        await self._require_run(run_id)
        next_sequence = after_sequence + 1
        terminal_statuses = {
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }
        while True:
            emitted = False
            for event in await self._store.list_events_after(
                run_id,
                after_sequence=next_sequence - 1,
                limit=500,
            ):
                emitted = True
                next_sequence = event.sequence_no + 1
                yield AgentEventView(
                    event_id=event.event_id,
                    sequence_no=event.sequence_no,
                    event_type=event.event_type,
                    severity=event.severity,
                    code=event.code,
                    turn_id=event.turn_id,
                    payload=event.payload,
                    created_at=event.created_at.isoformat(),
                )
            run = await self._require_run(run_id)
            if run.status in terminal_statuses and not emitted:
                break
            await asyncio.sleep(poll_interval_seconds)

    async def decide_approval(
        self,
        *,
        approval_id: str,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: ApprovalDecisionCommand,
    ) -> AgentApprovalView:
        tool_call = await self._store.get_tool_call_by_approval_id(approval_id)
        if tool_call is None:
            raise app_error(
                "Approval request was not found",
                code="agent.approval.not_found",
                category="validation",
                status_code=404,
                details={"approval_id": approval_id},
                operation="agent_run.decide_approval",
                component="agent",
            )
        run = await self._require_run(tool_call.run_id)
        turn = await self._store.get_turn(tool_call.turn_id)
        if turn is None:
            raise app_error(
                "Approval request references a missing turn",
                code="agent.approval.invalid_state",
                category="internal",
                status_code=500,
                details={"approval_id": approval_id, "turn_id": tool_call.turn_id},
                operation="agent_run.decide_approval",
                component="agent",
            )
        decided_at = utc_now()
        tool_call.status = (
            AgentToolCallStatus.APPROVED if command.approved else AgentToolCallStatus.REJECTED
        )
        tool_call.completed_at = decided_at if not command.approved else None
        await self._store.update_tool_call(tool_call)
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id,
            event_type="agent.approval.approved" if command.approved else "agent.approval.rejected",
            severity="info" if command.approved else "warning",
            code="agent.approval.approved" if command.approved else "agent.approval.rejected",
            payload={
                "approval_id": approval_id,
                "tool_call_id": tool_call.tool_call_id,
                "tool_name": tool_call.tool_name,
                "approved": command.approved,
            },
        )
        if command.approved:
            run.status = AgentRunStatus.PENDING
            run.request_id = request_id or run.request_id
            run.trace_id = trace_id or run.trace_id
            run.actor_id = actor_id or run.actor_id
            run.updated_at = decided_at
            await self._store.update_run(run)
            turn.status = AgentTurnStatus.PENDING
            await self._store.update_turn(turn)
            self._schedule_turn(run=run, turn=turn)
        else:
            run.status = AgentRunStatus.COMPLETED
            run.updated_at = decided_at
            run.completed_at = run.updated_at
            await self._store.update_run(run)
            turn.status = AgentTurnStatus.COMPLETED
            turn.completed_at = decided_at
            turn.response_text = "Approval was rejected. No tool execution was performed."
            await self._store.update_turn(turn)
            await self._append_event(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                event_type="agent.turn.completed",
                severity="info",
                code="agent.turn.completed",
                payload={"turn_id": turn.turn_id, "response_text": turn.response_text},
            )
        return AgentApprovalView(
            approval_id=approval_id,
            approved=command.approved,
            run_id=tool_call.run_id,
            turn_id=tool_call.turn_id,
            tool_call_id=tool_call.tool_call_id,
            status=tool_call.status.value,
        )

    async def cancel_run(self, run_id: str) -> AgentRunSummaryView:
        run = await self._require_run(run_id)
        if run.status in {
            AgentRunStatus.COMPLETED,
            AgentRunStatus.FAILED,
            AgentRunStatus.CANCELLED,
        }:
            raise app_error(
                "Agent run is already terminal and cannot be cancelled",
                code="agent.run.not_cancellable",
                category="validation",
                status_code=409,
                details={"run_id": run_id, "status": run.status.value},
                operation="agent_run.cancel_run",
                component="agent",
            )
        turn = (
            await self._store.get_turn(run.latest_turn_id)
            if run.latest_turn_id is not None
            else None
        )
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id if turn is not None else None,
            event_type="agent.run.cancel_requested",
            severity="warning",
            code="agent.run.cancel_requested",
            payload={"run_id": run.run_id},
        )
        task_cancelled = self._tasks.cancel(run_id)
        run.status = AgentRunStatus.CANCELLED
        run.updated_at = utc_now()
        run.completed_at = run.updated_at
        await self._store.update_run(run)
        if turn is not None:
            turn.status = AgentTurnStatus.CANCELLED
            turn.completed_at = utc_now()
            await self._store.update_turn(turn)
            if not task_cancelled:
                for tool_call in await self._store.list_tool_calls(run.run_id, turn.turn_id):
                    if tool_call.status not in {
                        AgentToolCallStatus.COMPLETED,
                        AgentToolCallStatus.FAILED,
                        AgentToolCallStatus.REJECTED,
                    }:
                        tool_call.status = AgentToolCallStatus.CANCELLED
                        tool_call.completed_at = turn.completed_at
                        await self._store.update_tool_call(tool_call)
                        await self._append_event(
                            run_id=run.run_id,
                            turn_id=turn.turn_id,
                            event_type="agent.tool.cancelled",
                            severity="warning",
                            code="agent.tool.cancelled",
                            payload={
                                "tool_call_id": tool_call.tool_call_id,
                                "tool_name": tool_call.tool_name,
                            },
                        )
                await self._append_event(
                    run_id=run.run_id,
                    turn_id=turn.turn_id,
                    event_type="agent.turn.cancelled",
                    severity="warning",
                    code="agent.turn.cancelled",
                    payload={"turn_id": turn.turn_id},
                )
        await self._append_event(
            run_id=run.run_id,
            turn_id=turn.turn_id if turn is not None else None,
            event_type="agent.run.cancelled",
            severity="warning",
            code="agent.run.cancelled",
            payload={"run_id": run.run_id},
        )
        return self._run_summary_view(await self._require_run(run_id))

    def _schedule_turn(self, *, run: AgentRun, turn: AgentTurn) -> None:
        self._tasks.start(
            TaskMetadata(
                task_id=run.run_id,
                purpose="generic_agent_turn",
                request_id=run.request_id,
                trace_id=run.trace_id,
                actor_id=run.actor_id,
            ),
            self._runtime.process_turn(run_id=run.run_id, turn_id=turn.turn_id),
        )

    async def _require_run(self, run_id: str) -> AgentRun:
        run = await self._store.get_run(run_id)
        if run is None:
            raise app_error(
                "Agent run was not found",
                code="agent.run.not_found",
                category="validation",
                status_code=404,
                details={"run_id": run_id},
                operation="agent_run.require_run",
                component="agent",
            )
        return run

    async def _recover_orphaned_run(self, run: AgentRun) -> AgentRun:
        if run.status != AgentRunStatus.RUNNING:
            return run
        snapshot = self._tasks.get_snapshot(run.run_id)
        if snapshot is not None and snapshot.status == TaskStatus.RUNNING:
            return run
        now = utc_now()
        error = app_error(
            "Previous agent turn stopped before reaching a terminal state",
            code="agent.run.orphaned",
            category="internal",
            status_code=500,
            details={
                "run_id": run.run_id,
                "task_status": snapshot.status.value if snapshot is not None else None,
            },
            operation="agent_run.recover_orphaned",
            component="agent",
        )
        run.status = AgentRunStatus.FAILED
        run.updated_at = now
        run.completed_at = now
        run.error_code = error.code
        run.error_category = error.category
        run.error_message = error.message
        run.error_details = error.to_dict()
        await self._store.update_run(run)
        turn = await self._store.get_turn(run.latest_turn_id) if run.latest_turn_id is not None else None
        if turn is not None and turn.status == AgentTurnStatus.RUNNING:
            turn.status = AgentTurnStatus.FAILED
            turn.completed_at = now
            turn.error_code = error.code
            turn.error_category = error.category
            turn.error_message = error.message
            turn.error_details = error.to_dict()
            await self._store.update_turn(turn)
            await self._append_event(
                run_id=run.run_id,
                turn_id=turn.turn_id,
                event_type="agent.turn.failed",
                severity=error.severity,
                code=error.code,
                payload={"turn_id": turn.turn_id, "error": error.to_dict()},
            )
        return await self._require_run(run.run_id)

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
        await self._store.append_event(
            AgentStreamEvent(
                event_id=new_id(),
                run_id=run_id,
                turn_id=turn_id,
                sequence_no=await self._store.next_event_sequence(run_id),
                event_type=event_type,
                severity=severity,
                payload=payload,
                code=code,
            )
        )

    @staticmethod
    def _run_summary_view(run: AgentRun) -> AgentRunSummaryView:
        return AgentRunSummaryView(
            run_id=run.run_id,
            profile_name=run.profile_name,
            status=run.status.value,
            prompt=AgentRunService._prompt_view(run.prompt),
            request_id=run.request_id,
            trace_id=run.trace_id,
            actor_id=run.actor_id,
            latest_turn_id=run.latest_turn_id,
            created_at=run.created_at.isoformat(),
            updated_at=run.updated_at.isoformat(),
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            error_code=run.error_code,
            error_category=run.error_category,
            error_message=run.error_message,
        )

    @staticmethod
    def _turn_view(turn: AgentTurn, tools: list[AgentToolCall]) -> AgentTurnView:
        return AgentTurnView(
            turn_id=turn.turn_id,
            sequence_no=turn.sequence_no,
            status=turn.status.value,
            input_text=turn.input_text,
            prompt=AgentRunService._prompt_view(turn.prompt),
            response_text=turn.response_text,
            created_at=turn.created_at.isoformat(),
            started_at=turn.started_at.isoformat() if turn.started_at else None,
            completed_at=turn.completed_at.isoformat() if turn.completed_at else None,
            error_code=turn.error_code,
            error_category=turn.error_category,
            error_message=turn.error_message,
            tools=[
                AgentToolCallView(
                    tool_call_id=item.tool_call_id,
                    tool_name=item.tool_name,
                    status=item.status.value,
                    requires_approval=item.requires_approval,
                    approval_id=item.approval_id,
                    arguments=item.arguments,
                    result_payload=item.result_payload,
                    error_code=item.error_code,
                    error_category=item.error_category,
                    error_message=item.error_message,
                )
                for item in tools
            ],
        )

    @staticmethod
    def _prompt_view(prompt: EffectivePromptRef | None) -> PromptRefView | None:
        if prompt is None:
            return None
        return PromptRefView(
            prompt_id=prompt.prompt_id,
            version=prompt.version,
            owner_kind=prompt.owner_kind,
            owner_id=prompt.owner_id,
            purpose=prompt.purpose,
            checksum=prompt.checksum,
        )
