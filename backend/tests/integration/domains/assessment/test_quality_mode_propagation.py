import uuid

import pytest
from fastapi.testclient import TestClient

from app.ai.substrate.stages.context import extract_quality_mode
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


@pytest.mark.parametrize(
    "pipeline_mode, expected_topology",
    [
        ("fast", "chat_fast"),
        ("accurate", "chat_accurate"),
    ],
)
def test_chat_typed_pipeline_topology_propagates_in_status_update(
    client: TestClient,
    monkeypatch,
    pipeline_mode: str,
    expected_topology: str,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Hello, how can I help you?")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "normal")
    get_settings.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        _auth(websocket)
        _set_pipeline_mode(websocket, pipeline_mode)

        message_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        websocket.send_json(
            {
                "type": "chat.typed",
                "payload": {
                    "sessionId": None,
                    "messageId": message_id,
                    "requestId": request_id,
                    "content": "hello",
                },
            }
        )

        pipeline_running = _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("service") == "pipeline"
            and m.get("payload", {}).get("status") in ("running", "streaming")
            and (m.get("payload", {}).get("metadata") or {}).get("mode") == "typed",
        )
        md = pipeline_running["payload"].get("metadata") or {}
        assert md.get("topology") == expected_topology
        assert md.get("behavior") == "typed"

        pipeline_completed = _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("service") == "pipeline"
            and m.get("payload", {}).get("status") == "completed"
            and (m.get("payload", {}).get("metadata") or {}).get("mode") == "typed",
        )

        md2 = pipeline_completed["payload"].get("metadata") or {}
        assert md2.get("topology") == expected_topology
        assert md2.get("behavior") == "typed"
        assert md2.get("pipeline_run_id") is not None

        expected_quality_mode = extract_quality_mode(expected_topology)
        assert expected_quality_mode == pipeline_mode
