import asyncio
import os
import time
import uuid

import asyncpg
from fastapi.testclient import TestClient
from sqlalchemy.engine.url import make_url

from app.ai.providers.factory import get_llm_provider
from app.ai.providers.llm.stub import StubLLMProvider
from app.config import get_settings
from tests.contract_assertions import receive_json_with_timeout as _receive_json_with_timeout


def _postgres_dsn_from_env() -> str:
    url = make_url(os.environ["DATABASE_URL"])
    return url.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )


async def _fetch_pipeline_run_status(pipeline_run_id: str) -> str | None:
    dsn = _postgres_dsn_from_env()
    conn = await asyncpg.connect(dsn=dsn)
    try:
        return await conn.fetchval(
            "SELECT status FROM pipeline_runs WHERE id = $1",
            uuid.UUID(pipeline_run_id),
        )
    finally:
        await conn.close()


def _auth_dev(websocket) -> None:
    websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
    resp = _receive_json_with_timeout(websocket, timeout=5.0)
    assert resp["type"] == "auth.success"
    _receive_json_with_timeout(websocket, timeout=5.0)


def test_ws_mid_stream_failure_stops_tokens_and_marks_run_failed(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")

    # Disable fallback so a mid-stream failure results in a failed pipeline.
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("LLM_BACKUP_PROVIDER", "")

    async def failing_stream(_self, messages, model: str | None = None, **_kwargs):
        _ = messages
        _ = model
        yield "x"
        yield "y"
        raise RuntimeError("stub_llm_mid_stream_failure")

    monkeypatch.setattr(StubLLMProvider, "stream", failing_stream, raising=True)

    get_settings.cache_clear()
    get_llm_provider.cache_clear()

    request_id = str(uuid.uuid4())

    with client.websocket_connect("/ws") as websocket:
        _auth_dev(websocket)

        websocket.send_json(
            {
                "type": "chat.typed",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": request_id,
                    "content": "hello",
                },
            }
        )

        tokens: list[str] = []
        pipeline_run_id: str | None = None

        failed_status = None
        for _ in range(300):
            msg = _receive_json_with_timeout(websocket, timeout=10.0)
            md = msg.get("metadata")
            if not isinstance(md, dict):
                continue
            if md.get("request_id") != request_id:
                continue

            if pipeline_run_id is None:
                pipeline_run_id = md.get("pipeline_run_id")
            if md.get("pipeline_run_id") != pipeline_run_id:
                continue

            if msg.get("type") == "chat.token":
                tokens.append(msg.get("payload", {}).get("token"))

            if msg.get("type") == "chat.complete":
                raise AssertionError("Unexpected chat.complete in mid-stream failure mode")

            if msg.get("type") == "error":
                failed_status = failed_status or msg

            if (
                msg.get("type") == "status.update"
                and msg.get("payload", {}).get("service") == "pipeline"
                and msg.get("payload", {}).get("status") == "failed"
            ):
                failed_status = msg
                break

        assert pipeline_run_id
        assert failed_status is not None
        assert len([t for t in tokens if isinstance(t, str) and t]) >= 1

        deadline = time.time() + 5.0
        status = None
        while time.time() < deadline:
            status = asyncio.run(_fetch_pipeline_run_status(pipeline_run_id))
            if status == "failed":
                break
            time.sleep(0.1)
        assert status == "failed"

        for _ in range(60):
            try:
                msg = _receive_json_with_timeout(websocket, timeout=0.25)
            except TimeoutError:
                break

            md = msg.get("metadata")
            if not isinstance(md, dict):
                continue
            if md.get("request_id") != request_id:
                continue
            if md.get("pipeline_run_id") != pipeline_run_id:
                continue

            if msg.get("type") == "chat.token":
                raise AssertionError("Received chat.token after pipeline failed")
            if msg.get("type") == "chat.complete":
                raise AssertionError("Received chat.complete after pipeline failed")
