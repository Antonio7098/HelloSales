from __future__ import annotations

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.platform.agents.models import (
    AgentRun,
    AgentRunStatus,
    AgentStreamEvent,
    AgentToolCall,
    AgentToolCallStatus,
    AgentTurn,
    AgentTurnStatus,
)
from hello_sales_backend.platform.db.base import metadata
from hello_sales_backend.platform.db.engine import build_engine
from hello_sales_backend.platform.db.repositories import SqlAlchemyAgentStore
from hello_sales_backend.platform.db.session import build_session_factory
from hello_sales_backend.platform.config.settings import Settings

pytestmark = pytest.mark.postgres


@pytest.mark.skipif(
    os.getenv("HELLO_SALES_RUN_POSTGRES_TESTS") != "1",
    reason="Set HELLO_SALES_RUN_POSTGRES_TESTS=1 to run PostgreSQL integration tests.",
)
@pytest.mark.asyncio
async def test_sqlalchemy_agent_store_round_trips_operational_state():
    database_url = os.getenv(
        "HELLO_SALES_POSTGRES_TEST_DATABASE_URL",
        "postgresql+asyncpg://hello_sales:hello_sales@localhost:5432/hello_sales",
    )
    settings = Settings(environment="test", database_url=database_url)
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    store = SqlAlchemyAgentStore(session_factory)

    async with engine.begin() as connection:
        await connection.run_sync(metadata.drop_all)
        await connection.run_sync(metadata.create_all)

    run = AgentRun(
        run_id="pg-run-1",
        profile_name="generic",
        status=AgentRunStatus.PENDING,
        request_id="req-1",
        trace_id="tr-1",
        actor_id=None,
    )
    turn = AgentTurn(
        turn_id="pg-turn-1",
        run_id=run.run_id,
        sequence_no=1,
        input_text="status",
        status=AgentTurnStatus.PENDING,
    )
    tool_call = AgentToolCall(
        tool_call_id="pg-tool-1",
        run_id=run.run_id,
        turn_id=turn.turn_id,
        sequence_no=1,
        tool_name="get_runtime_status",
        status=AgentToolCallStatus.COMPLETED,
        arguments={"limit": 1},
        requires_approval=False,
        result_payload={"status": "ok"},
    )
    event = AgentStreamEvent(
        event_id="pg-event-1",
        run_id=run.run_id,
        turn_id=turn.turn_id,
        sequence_no=1,
        event_type="agent.turn.completed",
        severity="info",
        payload={"turn_id": turn.turn_id},
        code="agent.turn.completed",
    )

    await store.create_run(run)
    await store.create_turn(turn)
    await store.create_tool_call(tool_call)
    await store.append_event(event)

    fetched_run = await store.get_run(run.run_id)
    fetched_turn = await store.get_turn(turn.turn_id)
    fetched_tools = await store.list_tool_calls(run.run_id, turn.turn_id)
    fetched_events = await store.list_events(run.run_id)
    summary = await store.summarize(limit=10)

    assert fetched_run is not None and fetched_run.run_id == run.run_id
    assert fetched_turn is not None and fetched_turn.turn_id == turn.turn_id
    assert fetched_tools[0].tool_call_id == tool_call.tool_call_id
    assert fetched_tools[0].result_payload == {"status": "ok"}
    assert fetched_events[0].event_id == event.event_id
    assert summary.total_count >= 1
    assert any(item.run_id == run.run_id for item in summary.recent_runs)

    async with engine.begin() as connection:
        await connection.run_sync(metadata.drop_all)
    await engine.dispose()
