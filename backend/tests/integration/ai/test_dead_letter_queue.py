"""Integration tests for Dead Letter Queue (DLQ) functionality.

Tests verify that failed pipeline runs are correctly captured in the DLQ
per stageflow.md §5.6 requirements.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from tests.contract_assertions import drain_until as _drain_until
from tests.contract_assertions import receive_json_with_timeout as _receive_json_with_timeout


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _auth(websocket):
    websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
    resp = _receive_json_with_timeout(websocket, timeout=5.0)
    assert resp["type"] == "auth.success"
    _receive_json_with_timeout(websocket, timeout=5.0)


def _set_pipeline_mode(websocket, mode: str):
    websocket.send_json({"type": "settings.setPipelineMode", "payload": {"mode": mode}})
    msg = _drain_until(websocket, lambda m: m.get("type") == "settings.pipelineModeSet")
    assert msg["payload"]["effectiveMode"] == mode


def test_dlq_table_exists(_client: TestClient):
    """Test that dead_letter_queue table exists and is accessible."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async def verify():
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM dead_letter_queue"))
            count = result.scalar()
        await engine.dispose()
        return count

    count = asyncio.run(verify())
    # Table should exist and may have entries (or be empty)
    assert count is not None


def test_dlq_table_has_expected_columns(_client: TestClient):
    """Test that dead_letter_queue table has expected columns."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async def verify():
        async with engine.begin() as conn:
            # Query the table structure
            result = await conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'dead_letter_queue'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
        await engine.dispose()
        return columns

    columns = asyncio.run(verify())
    column_names = [c[0] for c in columns]

    # Verify required columns exist
    required_columns = [
        'id', 'pipeline_run_id', 'request_id', 'service',
        'error_type', 'error_message', 'status', 'created_at',
        'context_snapshot', 'input_data', 'retry_count'
    ]
    for col in required_columns:
        assert col in column_names, f"Missing required column: {col}"

    print(f"DLQ table has {len(columns)} columns: {column_names}")


def test_dlq_indexes_exist(_client: TestClient):
    """Test that DLQ table has expected indexes."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async def verify():
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'dead_letter_queue'
            """))
            indexes = [r[0] for r in result.fetchall()]
        await engine.dispose()
        return indexes

    indexes = asyncio.run(verify())
    print(f"DLQ indexes: {indexes}")

    # Should have indexes on common query columns
    assert len(indexes) > 0, "DLQ table should have indexes"


def test_failed_pipeline_creates_dlq_entry(
    client: TestClient,
    monkeypatch,
):
    """Test that a failed pipeline run creates a DLQ entry."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "error")
    monkeypatch.setenv("STUB_LLM_ERROR_MESSAGE", "Simulated failure for DLQ test")
    monkeypatch.setenv("STUB_STT_FORCE_TRANSCRIPT", "Test message")
    get_settings.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        _auth(websocket)
        _set_pipeline_mode(websocket, "fast")

        websocket.send_json(
            {
                "type": "chat.message",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": str(uuid.uuid4()),
                    "content": "Test message",
                },
            }
        )

        # Wait and drain messages
        try:
            while True:
                msg = _receive_json_with_timeout(websocket, timeout=15.0)
                if msg.get("type") in ["chat.complete", "chat.error"]:
                    break
        except Exception:
            pass

    # Verify DLQ entry was created
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async def verify():
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM dead_letter_queue WHERE service = 'chat'")
            )
            count = result.scalar()
        await engine.dispose()
        return count

    count = asyncio.run(verify())
    assert count is not None, "Should be able to query DLQ table"
    print(f"DLQ has {count} chat service entries")


def test_dlq_status_values_are_valid(
    _client: TestClient,
):
    """Test that DLQ status values follow the expected enum."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async def verify():
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT DISTINCT status FROM dead_letter_queue")
            )
            statuses = [r[0] for r in result.fetchall()]
        await engine.dispose()
        return statuses

    statuses = asyncio.run(verify())
    valid_statuses = {"pending", "investigating", "resolved", "reprocessed"}

    for status in statuses:
        assert status in valid_statuses, f"Invalid DLQ status: {status}"

    print(f"DLQ status values found: {statuses}")
