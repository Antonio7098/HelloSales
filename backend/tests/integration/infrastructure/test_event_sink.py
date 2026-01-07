import json
import os
import uuid
from unittest.mock import AsyncMock

import asyncpg
import pytest
from sqlalchemy.engine.url import make_url

from app.ai.providers.stt.groq_whisper import GroqWhisperSTTProvider
from app.ai.substrate.events.sink import (
    DbPipelineEventSink,
    clear_event_sink,
    set_event_sink,
    wait_for_event_sink_tasks,
)
from app.database import get_session_context
from app.logging_config import clear_request_context, set_request_context
from app.models import Session, User


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
            "SELECT type, data, request_id FROM pipeline_events WHERE pipeline_run_id = $1 ORDER BY timestamp ASC",
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
            events.append(
                {
                    "type": r["type"],
                    "data": data,
                    "request_id": r["request_id"],
                }
            )
        return events
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_db_pipeline_event_sink_persists_event(apply_test_migrations) -> None:
    _ = apply_test_migrations
    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()

    async with get_session_context() as db:
        subject = f"test_{uuid.uuid4()}"
        user = User(
            auth_provider="clerk",
            auth_subject=subject,
            clerk_id=subject,
        )
        db.add(user)
        await db.flush()

        session = Session(user_id=user.id)
        db.add(session)
        await db.flush()
        await db.commit()

    set_request_context(
        request_id=str(request_id),
        pipeline_run_id=str(pipeline_run_id),
        session_id=str(session.id),
        user_id=str(user.id),
    )
    set_event_sink(DbPipelineEventSink(run_service="test"))

    try:
        sink = DbPipelineEventSink(run_service="test")
        await sink.emit(type="stt.transcript_filtered", data={"hello": "world"})
    finally:
        clear_event_sink()
        clear_request_context()

    events = await _fetch_pipeline_events(pipeline_run_id)
    assert any(e.get("type") == "stt.transcript_filtered" for e in events)

    filtered = next(e for e in events if e.get("type") == "stt.transcript_filtered")
    assert filtered.get("request_id") == request_id
    assert isinstance(filtered.get("data"), dict)
    assert filtered["data"].get("hello") == "world"


@pytest.mark.asyncio
async def test_db_pipeline_event_sink_is_noop_without_pipeline_run_id(
    apply_test_migrations,
) -> None:
    _ = apply_test_migrations
    clear_request_context()
    clear_event_sink()

    set_request_context(request_id=str(uuid.uuid4()))
    sink = DbPipelineEventSink(run_service="test")
    set_event_sink(sink)

    try:
        await sink.emit(type="stt.transcript_filtered", data={"hello": "world"})
    finally:
        clear_event_sink()
        clear_request_context()


@pytest.mark.asyncio
async def test_groq_whisper_filtered_event_persists_via_sink(apply_test_migrations) -> None:
    _ = apply_test_migrations
    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()

    async with get_session_context() as db:
        subject = f"test_{uuid.uuid4()}"
        user = User(
            auth_provider="clerk",
            auth_subject=subject,
            clerk_id=subject,
        )
        db.add(user)
        await db.flush()

        session = Session(user_id=user.id)
        db.add(session)
        await db.flush()
        await db.commit()

    set_request_context(
        request_id=str(request_id),
        pipeline_run_id=str(pipeline_run_id),
        session_id=str(session.id),
        user_id=str(user.id),
    )
    set_event_sink(DbPipelineEventSink(run_service="voice"))

    try:
        provider = GroqWhisperSTTProvider(api_key="test_api_key", model="whisper-large-v3")
        mock_client = AsyncMock()
        mock_client.audio.transcriptions.create = AsyncMock(
            return_value={
                "text": "Thank you.",
                "segments": [
                    {
                        "end": 1.2,
                    }
                ],
            }
        )
        provider._client = mock_client

        result = await provider.transcribe(audio_data=b"fake_audio", format="webm", language="en")
        assert result.transcript == ""

        # Wait for DbPipelineEventSink.try_emit background task to complete
        await wait_for_event_sink_tasks()
    finally:
        clear_event_sink()
        clear_request_context()

    events = await _fetch_pipeline_events(pipeline_run_id)
    assert any(e.get("type") == "stt.transcript_filtered" for e in events)
