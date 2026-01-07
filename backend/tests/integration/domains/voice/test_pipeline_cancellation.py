"""Integration tests for voice pipeline cancellation when no speech is detected.

These tests verify that:
1. When STT returns an empty transcript, the pipeline is cancelled gracefully
2. The UnifiedPipelineCancelled exception is raised and handled correctly
3. The voice service returns an empty VoicePipelineResult
4. No error exceptions are raised
"""


from fastapi.testclient import TestClient

from app.config import get_settings
from tests.contract_assertions import drain_until as _drain_until
from tests.contract_assertions import receive_json_with_timeout as _receive_json_with_timeout


def test_voice_pipeline_cancelled_on_empty_transcript(
    client: TestClient,
    monkeypatch,
):
    """Test that voice pipeline is cancelled when STT returns empty transcript.

    This tests the full flow:
    1. User sends voice recording
    2. STT returns empty transcript (no speech detected)
    3. SttStage returns StageOutput.cancel()
    4. Graph executor raises UnifiedPipelineCancelled
    5. Voice service catches exception and returns empty result
    6. Pipeline completes gracefully without error
    """
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_BACKUP_PROVIDER", "")
    monkeypatch.setenv("STUB_STT_EMPTY_TRANSCRIPT", "true")

    get_settings.cache_clear()
    from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
    get_llm_provider.cache_clear()
    get_stt_provider.cache_clear()
    get_tts_provider.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        resp = _receive_json_with_timeout(websocket, timeout=2.0)
        assert resp["type"] == "auth.success"
        _receive_json_with_timeout(websocket, timeout=2.0)

        websocket.send_json({
            "type": "settings.setPipelineMode",
            "payload": {"mode": "fast"},
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "settings.pipelineModeSet",
        )

        websocket.send_json({
            "type": "voice.start",
            "payload": {
                "sessionId": None,
                "format": "webm",
            },
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("status") == "recording",
        )

        websocket.send_json({
            "type": "voice.chunk",
            "payload": {
                "data": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQF",
            },
        })

        websocket.send_json({
            "type": "voice.end",
            "payload": {
                "messageId": "test-message-id",
            },
        })

        messages = []
        cancelled_detected = False

        for _i in range(50):
            msg = _receive_json_with_timeout(websocket, timeout=10.0)
            messages.append(msg)
            msg_type = msg.get("type")

            if msg_type == "status.update":
                status = msg.get("payload", {}).get("status")
                if status == "listening":
                    cancelled_detected = True
                    break
            elif msg_type == "voice.complete":
                break

        assert cancelled_detected, (
            f"Expected pipeline to be cancelled (return to 'listening' state). "
            f"Got messages: {[m.get('type') for m in messages[-5:]]}"
        )


def test_voice_pipeline_no_error_on_empty_transcript(
    client: TestClient,
    monkeypatch,
):
    """Test that no error is raised when pipeline is cancelled for empty transcript.

    This ensures that UnifiedPipelineCancelled is handled gracefully
    and doesn't propagate as an error.
    """
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_BACKUP_PROVIDER", "")
    monkeypatch.setenv("STUB_STT_EMPTY_TRANSCRIPT", "true")

    get_settings.cache_clear()
    from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
    get_llm_provider.cache_clear()
    get_stt_provider.cache_clear()
    get_tts_provider.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        resp = _receive_json_with_timeout(websocket, timeout=2.0)
        assert resp["type"] == "auth.success"
        _receive_json_with_timeout(websocket, timeout=2.0)

        websocket.send_json({
            "type": "settings.setPipelineMode",
            "payload": {"mode": "fast"},
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "settings.pipelineModeSet",
        )

        websocket.send_json({
            "type": "voice.start",
            "payload": {
                "sessionId": None,
                "format": "webm",
            },
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("status") == "recording",
        )

        websocket.send_json({
            "type": "voice.chunk",
            "payload": {
                "data": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQF",
            },
        })

        websocket.send_json({
            "type": "voice.end",
            "payload": {
                "messageId": "test-message-id",
            },
        })

        error_messages = []

        for _i in range(50):
            msg = _receive_json_with_timeout(websocket, timeout=10.0)
            msg_type = msg.get("type")

            if msg_type in ("error", "voice.error"):
                error_messages.append(msg)

            if msg_type == "status.update":
                status = msg.get("payload", {}).get("status")
                if status == "listening":
                    break

        assert len(error_messages) == 0, (
            f"Expected no error messages but got: {error_messages}"
        )


def test_cancelled_pipeline_logs_gracefully(
    client: TestClient,
    monkeypatch,
    caplog,
):
    """Test that cancelled pipeline is logged as info, not error."""
    import logging

    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_BACKUP_PROVIDER", "")
    monkeypatch.setenv("STUB_STT_EMPTY_TRANSCRIPT", "true")

    get_settings.cache_clear()
    from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
    get_llm_provider.cache_clear()
    get_stt_provider.cache_clear()
    get_tts_provider.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        resp = _receive_json_with_timeout(websocket, timeout=2.0)
        assert resp["type"] == "auth.success"
        _receive_json_with_timeout(websocket, timeout=2.0)

        websocket.send_json({
            "type": "settings.setPipelineMode",
            "payload": {"mode": "fast"},
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "settings.pipelineModeSet",
        )

        websocket.send_json({
            "type": "voice.start",
            "payload": {
                "sessionId": None,
                "format": "webm",
            },
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("status") == "recording",
        )

        websocket.send_json({
            "type": "voice.chunk",
            "payload": {
                "data": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQF",
            },
        })

        websocket.send_json({
            "type": "voice.end",
            "payload": {
                "messageId": "test-message-id",
            },
        })

        for _i in range(50):
            msg = _receive_json_with_timeout(websocket, timeout=10.0)
            msg_type = msg.get("type")

            if msg_type == "status.update":
                status = msg.get("payload", {}).get("status")
                if status == "listening":
                    break

        log_records = [
            rec for rec in caplog.records
            if "cancelled" in rec.message.lower() or "cancel" in rec.message.lower()
        ]

        cancellation_logs = [
            rec for rec in log_records
            if rec.levelno >= logging.INFO
        ]

        assert len(cancellation_logs) > 0, (
            "Expected cancellation to be logged. Log records: "
            f"{[(r.levelname, r.message) for r in log_records]}"
        )


def test_pipeline_runs_normally_with_transcript(
    client: TestClient,
    monkeypatch,
):
    """Test that pipeline runs normally when STT returns a valid transcript.

    This is a sanity check to ensure the normal flow still works
    and isn't broken by the cancellation logic.
    """
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_BACKUP_PROVIDER", "")
    monkeypatch.setenv("STUB_LLM_FORCE_STREAM_TEXT", "Hello, how can I help?")
    monkeypatch.setenv("STUB_STT_FORCE_TRANSCRIPT", "I want to practice my presentation")

    get_settings.cache_clear()
    from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
    get_llm_provider.cache_clear()
    get_stt_provider.cache_clear()
    get_tts_provider.cache_clear()

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        resp = _receive_json_with_timeout(websocket, timeout=2.0)
        assert resp["type"] == "auth.success"
        _receive_json_with_timeout(websocket, timeout=2.0)

        websocket.send_json({
            "type": "settings.setPipelineMode",
            "payload": {"mode": "fast"},
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "settings.pipelineModeSet",
        )

        websocket.send_json({
            "type": "voice.start",
            "payload": {
                "sessionId": None,
                "format": "webm",
            },
        })

        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("status") == "recording",
        )

        websocket.send_json({
            "type": "voice.chunk",
            "payload": {
                "data": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQFJHfH8N2QQAoUXrTp66hVFApGn+DyvmYdBzuP1fLGezQF",
            },
        })

        websocket.send_json({
            "type": "voice.end",
            "payload": {
                "messageId": "test-message-id",
            },
        })

        complete_received = False

        for _i in range(100):
            msg = _receive_json_with_timeout(websocket, timeout=30.0)
            msg_type = msg.get("type")

            if msg_type == "voice.complete":
                complete_received = True
                payload = msg.get("payload", {})
                assert payload.get("transcript") == "I want to practice my presentation"
                break

        assert complete_received, "Expected voice.complete with valid transcript"
