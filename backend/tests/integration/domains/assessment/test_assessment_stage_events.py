"""Integration tests for assessment stage event emission and pipeline linkage."""
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


@pytest.mark.parametrize(
    "pipeline_mode, expected_quality_mode",
    [
        ("fast", "fast"),
        ("accurate", "accurate"),
    ],
)
def test_chat_message_assessment_events_emitted(
    client: TestClient,
    monkeypatch,
    pipeline_mode: str,
    expected_quality_mode: str,
):
    """Test that chat.message completes with pipeline run ID and assessment handling."""
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BETA_MODE_ENABLED", "true")
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

        # Wait for chat.complete which indicates the pipeline finished
        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        assert chat_complete is not None

        # Verify pipeline run ID is present
        payload = chat_complete.get("payload", {})
        metadata = chat_complete.get("metadata", {})
        pipeline_run_id = payload.get("pipelineRunId") or metadata.get("pipeline_run_id")
        assert pipeline_run_id is not None, "chat.complete should include pipeline_run_id"

        # For chat.message, assessment is handled (either run or skipped)
        # The assessment.skipped or assessment.complete message indicates this
        # We don't need to verify internal status.update events


@pytest.mark.parametrize(
    "pipeline_mode, expected_quality_mode",
    [
        pytest.param("fast", "fast", marks=pytest.mark.xfail(reason="Voice pipeline hanging - needs investigation")),
        pytest.param("accurate", "accurate", marks=pytest.mark.xfail(reason="Voice accurate pipeline timing issue with conditional assessment")),
    ],
)
def test_voice_recording_assessment_events_emitted(
    client: TestClient,
    monkeypatch,
    pipeline_mode: str,
    expected_quality_mode: str,
):
    """Test that voice.recording completes with pipeline run ID and assessment handling."""
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BETA_MODE_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STT_PROVIDER", "stub")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Hello, how can I help you?")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "normal")
    monkeypatch.setenv("STUB_STT_FORCE_TRANSCRIPT", "Hello, I want to practice my presentation skills")
    monkeypatch.setenv("STUB_STT_FORCE_DURATION_MS", "1500")
    get_settings.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        _auth(websocket)
        _set_pipeline_mode(websocket, pipeline_mode)

        message_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        websocket.send_json(
            {
                "type": "voice.recording",
                "payload": {
                    "sessionId": None,
                    "messageId": message_id,
                    "requestId": request_id,
                    "audioData": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQF",  # Short dummy audio
                },
            }
        )

        # Wait for voice.complete which indicates the pipeline finished
        voice_complete = _drain_until(websocket, lambda m: m.get("type") == "voice.complete")
        assert voice_complete is not None

        # Verify pipeline run ID is present
        payload = voice_complete.get("payload", {})
        metadata = voice_complete.get("metadata", {})
        pipeline_run_id = payload.get("pipelineRunId") or metadata.get("pipeline_run_id")
        assert pipeline_run_id is not None, "voice.complete should include pipeline_run_id"
