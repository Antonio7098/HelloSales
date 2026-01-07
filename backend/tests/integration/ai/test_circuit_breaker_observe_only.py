import asyncio
import json
import os
import time
import uuid

import asyncpg
import pytest
from sqlalchemy.engine.url import make_url

from app.ai.substrate import ProviderCallLogger
from app.ai.substrate.events.sink import DbPipelineEventSink, clear_event_sink, set_event_sink
from app.models import PipelineRun, Session, User


def _postgres_dsn_from_env() -> str:
    url = make_url(os.environ["DATABASE_URL"])
    return url.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )


async def _fetch_pipeline_events(pipeline_run_id: uuid.UUID) -> list[dict]:
    dsn = _postgres_dsn_from_env()
    conn = await asyncpg.connect(dsn=dsn)
    try:
        rows = await conn.fetch(
            "SELECT type, data FROM pipeline_events WHERE pipeline_run_id = $1 ORDER BY timestamp ASC",
            pipeline_run_id,
        )
        events: list[dict] = []
        for r in rows:
            data = r["data"]
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = None
            events.append({"type": r["type"], "data": data})
        return events
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_circuit_breaker_is_observe_only_allows_calls_while_open(db_session) -> None:
    from app.ai.substrate import observability as observability_module
    from app.config import get_settings
    from app.logging_config import clear_request_context, set_request_context

    os.environ["CIRCUIT_BREAKER_FAILURE_THRESHOLD"] = "1"
    os.environ["CIRCUIT_BREAKER_OPEN_SECONDS"] = "3600"
    os.environ["CIRCUIT_BREAKER_FAILURE_WINDOW_SECONDS"] = "60"
    os.environ["CIRCUIT_BREAKER_HALF_OPEN_PROBE_COUNT"] = "1"
    get_settings.cache_clear()

    async with observability_module._circuit_breaker._lock:
        observability_module._circuit_breaker._states.clear()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="clerk", auth_subject=subject, clerk_id=subject)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    run = PipelineRun(
        id=pipeline_run_id,
        service="test",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        success=True,
        error=None,
    )
    db_session.add(run)
    await db_session.commit()

    set_request_context(
        request_id=str(request_id),
        pipeline_run_id=str(pipeline_run_id),
        session_id=str(session.id),
        user_id=str(user.id),
    )
    set_event_sink(DbPipelineEventSink(run_service="test"))

    try:
        call_logger = ProviderCallLogger(db_session)

        async def _boom():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            await call_logger.call_llm_generate(
                service="test",
                provider="stub",
                model_id="m",
                prompt_messages=[{"role": "user", "content": "hi"}],
                call=_boom,
            )

        await db_session.commit()

        async with observability_module._circuit_breaker._lock:
            state = observability_module._circuit_breaker._states.get(("llm.generate", "stub", "m"))
            assert state is not None
            assert state.get("state") == "open"

        class _Resp:
            def __init__(self) -> None:
                self.content = "ok"
                self.tokens_in = 1
                self.tokens_out = 1
                self.model = "m"

        async def _ok():
            return _Resp()

        resp, call_row = await call_logger.call_llm_generate(
            service="test",
            provider="stub",
            model_id="m",
            prompt_messages=[{"role": "user", "content": "hi"}],
            call=_ok,
        )
        assert getattr(resp, "content", None) == "ok"
        assert call_row.success is True

        await db_session.commit()

        deadline = time.time() + 1.0
        types: list[str] = []
        while time.time() < deadline:
            events = await _fetch_pipeline_events(pipeline_run_id)
            types = [str(e.get("type")) for e in events]
            if "circuit.opened" in types and "provider.call.succeeded" in types:
                break
            await asyncio.sleep(0.05)

        assert "circuit.opened" in types
        assert "provider.call.succeeded" in types
    finally:
        clear_event_sink()
        clear_request_context()
