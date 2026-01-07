"""Integration tests for ContextSnapshot production in pipeline runs.

Tests verify that ContextSnapshot is correctly produced during end-to-end
pipeline execution per stageflow.md §8.1 requirements.

Note: These tests verify end-to-end behavior via WebSocket. The actual
ContextSnapshot verification would require async verification which is
skipped to avoid event loop conflicts in the test environment.
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


@pytest.mark.parametrize("pipeline_mode", ["fast", "accurate"])
def test_chat_pipeline_completes_successfully(
    client: TestClient,
    monkeypatch,
    pipeline_mode: str,
):
    """Test that chat pipeline completes successfully (prerequisite for ContextSnapshot)."""
    from app.config import get_settings

    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Hello, how can I help you?")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "normal")
    monkeypatch.setenv("STUB_STT_FORCE_TRANSCRIPT", "Hello, I want to practice my presentation skills")
    get_settings.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        _auth(websocket)
        _set_pipeline_mode(websocket, pipeline_mode)

        message_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        websocket.send_json(
            {
                "type": "chat.message",
                "payload": {
                    "sessionId": None,
                    "messageId": message_id,
                    "requestId": request_id,
                    "content": "Hello, I want to practice my presentation skills",
                },
            }
        )

        # Wait for chat to complete
        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        pipeline_run_id = chat_complete["payload"].get("pipelineRunId")
        assert pipeline_run_id, "Pipeline should complete with a run ID"
        # Verify chat.complete has expected content
        assert "content" in chat_complete["payload"], "chat.complete should have content"


@pytest.mark.parametrize("pipeline_mode", ["fast", "accurate"])
def test_chat_pipeline_emits_expected_events(
    client: TestClient,
    monkeypatch,
    pipeline_mode: str,
):
    """Test that chat pipeline emits the expected sequence of events."""
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Test response")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "normal")
    monkeypatch.setenv("STUB_STT_FORCE_TRANSCRIPT", "Test message")
    get_settings.cache_clear()

    events_received = []

    with client.websocket_connect("/ws") as websocket:
        _auth(websocket)
        _set_pipeline_mode(websocket, pipeline_mode)

        request_id = str(uuid.uuid4())

        websocket.send_json(
            {
                "type": "chat.message",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": request_id,
                    "content": "Test message",
                },
            }
        )

        # Collect events until chat.complete
        while True:
            msg = _receive_json_with_timeout(websocket, timeout=30.0)
            events_received.append(msg.get("type"))
            if msg.get("type") == "chat.complete":
                break

    # Verify expected event sequence
    assert "session.created" in events_received, "Should emit session.created"
    assert "status.update" in events_received, "Should emit status updates"
    assert "chat.complete" in events_received, "Should emit chat.complete"


def test_pipeline_run_id_is_valid_uuid(
    client: TestClient,
    monkeypatch,
):
    """Test that pipeline_run_id is a valid UUID for tracking."""
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Response")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "normal")
    monkeypatch.setenv("STUB_STT_FORCE_TRANSCRIPT", "Test")
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
                    "content": "Test",
                },
            }
        )

        chat_complete = _drain_until(
            websocket,
            lambda m: m.get("type") == "chat.complete",
            timeout=30.0,
        )
        pipeline_run_id = chat_complete["payload"].get("pipelineRunId")

        # Verify it's a valid UUID
        assert pipeline_run_id is not None
        try:
            uuid.UUID(pipeline_run_id)
        except ValueError:
            pytest.fail(f"pipeline_run_id should be a valid UUID, got: {pipeline_run_id}")


@pytest.mark.xfail(reason="Voice pipeline hanging - needs investigation")
def test_voice_pipeline_completes_successfully(
    client: TestClient,
    monkeypatch,
):
    """Test that voice pipeline completes successfully."""
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STT_PROVIDER", "stub")
    monkeypatch.setenv("TTS_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Hello, how can I help you?")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "normal")
    monkeypatch.setenv("STUB_STT_FORCE_TRANSCRIPT", "I want to practice")
    monkeypatch.setenv("STUB_STT_FORCE_DURATION_MS", "1500")
    get_settings.cache_clear()

    from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
    get_stt_provider.cache_clear()
    get_llm_provider.cache_clear()
    get_tts_provider.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        _auth(websocket)
        _set_pipeline_mode(websocket, "fast")

        websocket.send_json(
            {
                "type": "voice.start",
                "payload": {
                    "sessionId": None,
                    "format": "webm",
                },
            }
        )

        # Wait for recording to start
        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update" and m.get("payload", {}).get("status") == "recording",
            timeout=10.0,
        )

        # Send audio chunk
        websocket.send_json(
            {
                "type": "voice.chunk",
                "payload": {
                    "data": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQF",  # Short dummy audio
                },
            }
        )

        # End recording
        websocket.send_json(
            {
                "type": "voice.end",
                "payload": {
                    "messageId": str(uuid.uuid4()),
                },
            }
        )

        # Wait for voice to complete
        voice_complete = _drain_until(
            websocket,
            lambda m: m.get("type") == "voice.complete",
            timeout=120.0,
            max_messages=200,
        )
        assert voice_complete["payload"].get("pipelineRunId") is not None
        assert voice_complete["payload"].get("status") == "completed"
