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


def test_chat_typed_orchestrated_flow_emits_tokens_and_chat_complete(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Hello, how can I help you?")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "normal")
    get_settings.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        resp = _receive_json_with_timeout(websocket, timeout=2.0)
        assert resp["type"] == "auth.success"
        _receive_json_with_timeout(websocket, timeout=2.0)

        websocket.send_json(
            {
                "type": "chat.typed",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": str(uuid.uuid4()),
                    "content": "hello",
                },
            }
        )

        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("service") == "pipeline"
            and m.get("payload", {}).get("status") == "running",
        )

        tokens: list[str] = []
        complete_msg = None
        for _ in range(120):
            msg = _receive_json_with_timeout(websocket, timeout=2.0)
            if msg.get("type") == "chat.token":
                tokens.append(msg["payload"]["token"])
            if msg.get("type") == "chat.complete":
                complete_msg = msg
                break

        assert complete_msg is not None
        full = complete_msg["payload"]["content"]
        assert full == "".join(tokens)

        md_run_id = complete_msg["payload"].get("pipelineRunId")
        assert md_run_id
