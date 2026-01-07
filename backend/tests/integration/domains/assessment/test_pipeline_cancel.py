import asyncio
import uuid

from fastapi.testclient import TestClient

from app.ai.providers.llm.stub import StubLLMProvider
from app.config import get_settings
from tests.contract_assertions import assert_websocket_no_chat_complete
from tests.contract_assertions import drain_until as _drain_until
from tests.contract_assertions import receive_json_with_timeout as _receive_json_with_timeout


def test_pipeline_cancel_mid_run_marks_canceled_and_stops_completion(
    client: TestClient,
    monkeypatch,
):
    # Override specific settings for this test
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_BACKUP_PROVIDER", "")

    # Clear caches to pick up any changes
    get_settings.cache_clear()
    from app.ai.providers.factory import get_llm_provider, get_stt_provider, get_tts_provider
    get_llm_provider.cache_clear()
    get_stt_provider.cache_clear()
    get_tts_provider.cache_clear()

    async def slow_stream(_self, messages, model: str | None = None, **_kwargs):
        _ = messages
        _ = model
        for _ in range(500):
            await asyncio.sleep(0.02)
            yield "x"

    monkeypatch.setattr(StubLLMProvider, "stream", slow_stream, raising=True)

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

        running = _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("service") == "pipeline"
            and m.get("payload", {}).get("status") == "running",
        )
        metadata = running["payload"].get("metadata") or {}
        pipeline_run_id = metadata.get("pipelineRunId") or metadata.get("pipeline_run_id")
        assert pipeline_run_id

        _drain_until(websocket, lambda m: m.get("type") == "chat.token")

        websocket.send_json(
            {
                "type": "pipeline.cancel_requested",
                "payload": {
                    "pipelineRunId": pipeline_run_id,
                    "requestId": str(uuid.uuid4()),
                },
            }
        )

        canceled = _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("service") == "pipeline"
            and m.get("payload", {}).get("status") == "canceled",
        )
        md = canceled["payload"].get("metadata") or {}
        assert (md.get("pipelineRunId") or md.get("pipeline_run_id")) == pipeline_run_id

        assert_websocket_no_chat_complete(websocket)
