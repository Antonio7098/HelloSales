from __future__ import annotations

import asyncio

import pytest

from hello_sales_backend.modules.agent_runs.use_cases.agent_run_service import AgentRunService
from hello_sales_backend.modules.agent_runs.use_cases.commands import AppendAgentTurnCommand
from hello_sales_backend.platform.agents.memory import InMemoryAgentStore
from hello_sales_backend.platform.agents.models import (
    AgentRun,
    AgentRunStatus,
    AgentTurn,
    AgentTurnStatus,
)
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.shared.errors import AppError
from tests.support.auth import build_test_auth_context


class _NoopRuntime:
    async def process_turn(self, *, run_id: str, turn_id: str) -> None:
        del run_id, turn_id
        await asyncio.sleep(0)


class _AgentResolver:
    def require(self, profile_name: str):  # noqa: ANN001
        del profile_name
        raise AssertionError("append_turn should not resolve agent definitions")


@pytest.mark.asyncio
async def test_append_turn_recovers_orphaned_running_run() -> None:
    store = InMemoryAgentStore()
    tasks = BackgroundTaskRunner()
    service = AgentRunService(
        store=store,
        runtime=_NoopRuntime(),
        tasks=tasks,
        agents=_AgentResolver(),
    )
    run = AgentRun(
        run_id="run-1",
        profile_name="generic",
        status=AgentRunStatus.RUNNING,
        request_id="req-1",
        trace_id="trace-1",
        actor_id=None,
    )
    turn = AgentTurn(
        turn_id="turn-1",
        run_id=run.run_id,
        sequence_no=1,
        input_text="first",
        status=AgentTurnStatus.RUNNING,
    )
    run.latest_turn_id = turn.turn_id
    await store.create_run(run)
    await store.create_turn(turn)

    summary = await service.append_turn(
        run_id=run.run_id,
        request_id="req-2",
        trace_id="trace-2",
        auth_context=build_test_auth_context(),
        command=AppendAgentTurnCommand(input_text="second"),
    )

    assert summary.status == "pending"
    recovered_turn = await store.get_turn("turn-1")
    assert recovered_turn is not None
    assert recovered_turn.status == AgentTurnStatus.FAILED
    assert recovered_turn.error_code == "agent.run.orphaned"
    events = await store.list_events(run.run_id)
    assert any(event.code == "agent.run.orphaned" for event in events)
    await tasks.shutdown()


@pytest.mark.asyncio
async def test_append_turn_rejects_awaiting_approval_run() -> None:
    store = InMemoryAgentStore()
    service = AgentRunService(
        store=store,
        runtime=_NoopRuntime(),
        tasks=BackgroundTaskRunner(),
        agents=_AgentResolver(),
    )
    run = AgentRun(
        run_id="run-1",
        profile_name="generic",
        status=AgentRunStatus.AWAITING_APPROVAL,
        request_id="req-1",
        trace_id="trace-1",
        actor_id=None,
    )
    turn = AgentTurn(
        turn_id="turn-1",
        run_id=run.run_id,
        sequence_no=1,
        input_text="first",
        status=AgentTurnStatus.AWAITING_APPROVAL,
    )
    run.latest_turn_id = turn.turn_id
    await store.create_run(run)
    await store.create_turn(turn)

    with pytest.raises(AppError) as exc_info:
        await service.append_turn(
            run_id=run.run_id,
            request_id="req-2",
            trace_id="trace-2",
            auth_context=build_test_auth_context(),
            command=AppendAgentTurnCommand(input_text="second"),
        )

    assert exc_info.value.code == "agent.run.busy"
    assert exc_info.value.details == {"run_id": run.run_id, "status": "awaiting_approval"}
