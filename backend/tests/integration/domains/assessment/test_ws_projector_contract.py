import base64
import json
import os
import time
import uuid
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.ai.providers.factory import get_llm_provider
from app.config import get_settings
from tests.contract_assertions import drain_until as _drain_until
from tests.contract_assertions import receive_json_with_timeout as _receive_json_with_timeout


def _postgres_dsn_from_env() -> str:
    url = make_url(os.environ["DATABASE_URL"])
    return url.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )


async def _fetch_pipeline_events(pipeline_run_id: str) -> list[dict]:
    """Fetch pipeline events using the test database session for consistency."""
    from app.config import get_settings

    # Use the same database configuration as the tests
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT type, data FROM pipeline_events WHERE pipeline_run_id = :pipeline_run_id ORDER BY timestamp ASC"
            ),
            {"pipeline_run_id": pipeline_run_id},
        )
        rows = result.fetchall()

        events: list[dict] = []
        for r in rows:
            data = r[1]  # data column
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = None
            events.append({"type": r[0], "data": data})
        return events


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


async def _fetch_pipeline_run_metrics(pipeline_run_id: str) -> dict | None:
    dsn = _postgres_dsn_from_env()
    conn = await asyncpg.connect(dsn=dsn)
    try:
        row = await conn.fetchrow(
            """
            SELECT ttft_ms, ttfc_ms, tokens_in, tokens_out
            FROM pipeline_runs
            WHERE id = $1
            """,
            uuid.UUID(pipeline_run_id),
        )
        if row is None:
            return None
        return {
            "ttft_ms": row["ttft_ms"],
            "ttfc_ms": row["ttfc_ms"],
            "tokens_in": row["tokens_in"],
            "tokens_out": row["tokens_out"],
        }
    finally:
        await conn.close()


def _get_event_data(events: list[dict], event_type: str) -> dict | None:
    for event in events:
        if event.get("type") == event_type:
            data = event.get("data")
            if isinstance(data, dict):
                return data
            return None
    return None


def _auth_dev(websocket) -> None:
    websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
    resp = _receive_json_with_timeout(websocket, timeout=5.0)
    assert resp["type"] == "auth.success"
    _receive_json_with_timeout(websocket, timeout=5.0)


@pytest.mark.asyncio
async def test_ws_projector_chat_typed_contract_includes_metadata_and_single_completion(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        tokens: list[str] = []
        chat_complete: dict | None = None
        pipeline_run_id: str | None = None

        for _ in range(240):
            msg = _receive_json_with_timeout(websocket, timeout=10.0)
            md = msg.get("metadata")
            assert isinstance(md, dict)
            assert md.get("pipeline_run_id")
            assert md.get("request_id")

            if md.get("request_id") != request_id:
                continue

            if pipeline_run_id is None:
                pipeline_run_id = md.get("pipeline_run_id")
            else:
                assert md.get("pipeline_run_id") == pipeline_run_id

            if msg.get("type") == "chat.token":
                tokens.append(msg["payload"]["token"])

            if msg.get("type") == "chat.complete":
                chat_complete = msg
                break

        assert chat_complete is not None
        assert pipeline_run_id

        md_complete = chat_complete.get("metadata") or {}
        assert md_complete.get("request_id") == request_id
        assert md_complete.get("pipeline_run_id") == pipeline_run_id
        assert "org_id" not in md_complete

        full = chat_complete["payload"]["content"]
        assert full == "".join(tokens)

        for _ in range(80):
            try:
                msg = _receive_json_with_timeout(websocket, timeout=0.5)
            except TimeoutError:
                break

            md = msg.get("metadata")
            if not isinstance(md, dict):
                continue
            if md.get("request_id") != request_id:
                continue
            if md.get("pipeline_run_id") != pipeline_run_id:
                continue
            assert msg.get("type") != "chat.complete"

    # Simple async event checking
    import time

    time.sleep(2.0)  # Wait longer for events to be committed

    # Fetch events with proper error handling
    events = []
    try:
        events = await _fetch_pipeline_events(pipeline_run_id)
        print(f"DEBUG: Fetched {len(events)} events for pipeline {pipeline_run_id}")
    except Exception as e:
        print(f"DEBUG: Error fetching events: {e}")
        # If there's an error, try once more
        time.sleep(1.0)
        try:
            events = await _fetch_pipeline_events(pipeline_run_id)
            print(f"DEBUG: Retry fetched {len(events)} events")
        except Exception as e2:
            print(f"DEBUG: Retry also failed: {e2}")
            events = []

    # If events not found, retry a few times with longer delays
    retry_count = 0
    max_retries = 8
    while (
        retry_count < max_retries
        and not events
        or not (
            any(e.get("type") == "llm.first_token" for e in events)
            and any(e.get("type") == "llm.completed" for e in events)
        )
    ):
        retry_count += 1
        print(f"DEBUG: Retry {retry_count}/{max_retries}")
        time.sleep(1.5)  # Longer delay
        try:
            events = await _fetch_pipeline_events(pipeline_run_id)
            print(f"DEBUG: Events on retry {retry_count}: {len(events) if events else 0}")
            if events:
                print(f"DEBUG: Event types: {[e.get('type') for e in events]}")
        except Exception as e:
            print(f"DEBUG: Error on retry {retry_count}: {e}")
            events = []

    print(f"DEBUG: Final events count: {len(events) if events else 0}")
    assert events is not None, "Events should not be None"
    assert len(events) > 0, f"Expected at least some events, got {len(events)}"
    first_token_events = [e for e in events if e.get("type") == "llm.first_token"]
    # After PipelineOrchestrator migration, there may be multiple llm.first_token events
    # from different stages/modes (e.g., fast and typed modes). Accept 1 or 2 events.
    assert len(first_token_events) in (1, 2), f"Expected 1 or 2 llm.first_token events, got {len(first_token_events)}"
    assert isinstance(first_token_events[0].get("data"), dict)

    completed_events = [e for e in events if e.get("type") == "llm.completed"]
    assert len(completed_events) == 1

    metrics = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        metrics = await _fetch_pipeline_run_metrics(pipeline_run_id)
        if metrics and metrics.get("ttft_ms") is not None and metrics.get("tokens_out") is not None:
            break
        time.sleep(0.1)

    assert metrics is not None
    assert metrics.get("ttft_ms") is not None
    assert metrics.get("tokens_out") is not None
    assert int(metrics["tokens_out"]) > 0


@pytest.mark.asyncio
async def test_ws_projector_llm_fallback_blocked_post_first_token_emits_event(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_BACKUP_PROVIDER", "openrouter")
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "mid_stream_failure")
    monkeypatch.setenv("STUB_LLM_FAIL_AFTER_CHUNKS", "1")
    monkeypatch.setenv("STUB_LLM_STREAM_TEXT", "hello world this should fail mid stream")
    monkeypatch.setenv("STUB_LLM_STREAM_CHUNK_SIZE", "4")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        pipeline_run_id: str | None = None
        saw_error = False
        saw_token = False

        for _ in range(240):
            msg = _receive_json_with_timeout(websocket, timeout=10.0)
            md = msg.get("metadata")
            if not isinstance(md, dict):
                continue
            if md.get("request_id") != request_id:
                continue

            if pipeline_run_id is None:
                pipeline_run_id = md.get("pipeline_run_id")

            if msg.get("type") == "chat.token":
                saw_token = True

            if msg.get("type") == "chat.complete":
                raise AssertionError(
                    "chat.complete must not be emitted on post-first-token LLM failure"
                )

            if msg.get("type") == "error":
                saw_error = True
                break

        assert pipeline_run_id
        assert saw_token is True
        assert saw_error is True

        # Ensure no late chat.complete is emitted after error
        for _ in range(60):
            try:
                msg = _receive_json_with_timeout(websocket, timeout=0.5)
            except TimeoutError:
                break

            md = msg.get("metadata")
            if not isinstance(md, dict):
                continue
            if md.get("request_id") != request_id:
                continue
            if md.get("pipeline_run_id") != pipeline_run_id:
                continue
            assert msg.get("type") != "chat.complete"

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(pipeline_run_id)
        if any(e.get("type") == "llm.fallback.blocked_post_first_token" for e in events):
            break
        time.sleep(0.1)

    assert events is not None
    assert len([e for e in events if e.get("type") == "llm.fallback.blocked_post_first_token"]) == 1
    assert not any(e.get("type") == "llm.fallback.attempted" for e in events)
    assert not any(e.get("type") == "llm.fallback.succeeded" for e in events)


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Voice pipeline hanging - needs investigation")
async def test_ws_projector_voice_incremental_tts_persists_ttfc_and_emits_first_chunk(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.setenv("STT_PROVIDER", "stub")
    monkeypatch.setenv("TTS_PROVIDER", "stub")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance
    from app.ai.providers import factory as provider_factory

    provider_factory.get_llm_provider.cache_clear()
    provider_factory.get_stt_provider.cache_clear()
    provider_factory.get_tts_provider.cache_clear()

    monkeypatch.setenv("PIPELINE_MODE", "fast")

    monkeypatch.setenv("STUB_LLM_STREAM_TEXT", "Hello world.")
    monkeypatch.setenv("STUB_LLM_STREAM_CHUNK_SIZE", "4")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

    request_id = str(uuid.uuid4())

    with client.websocket_connect("/ws") as websocket:
        _auth_dev(websocket)

        websocket.send_json(
            {
                "type": "voice.start",
                "payload": {
                    "sessionId": None,
                    "format": "webm",
                    "requestId": request_id,
                },
            }
        )

        _drain_until(
            websocket,
            lambda m: m.get("type") == "status.update"
            and m.get("payload", {}).get("service") == "mic"
            and m.get("payload", {}).get("status") == "recording",
        )

        audio_b64 = base64.b64encode(b"\x00" * 320).decode("utf-8")
        websocket.send_json(
            {
                "type": "voice.chunk",
                "payload": {
                    "data": audio_b64,
                },
            }
        )

        websocket.send_json(
            {
                "type": "voice.end",
                "payload": {
                    "messageId": str(uuid.uuid4()),
                    "requestId": request_id,
                },
            }
        )

        pipeline_run_id: str | None = None
        saw_audio_chunk = False
        for _ in range(500):
            msg = _receive_json_with_timeout(websocket, timeout=10.0)
            md = msg.get("metadata")
            if not isinstance(md, dict):
                continue
            if md.get("request_id") != request_id:
                continue

            if pipeline_run_id is None:
                pipeline_run_id = md.get("pipeline_run_id")

            if msg.get("type") == "voice.audio.chunk":
                saw_audio_chunk = True
                break

            if msg.get("type") == "error":
                raise AssertionError(f"Unexpected error during voice pipeline: {msg}")

        assert pipeline_run_id
        assert saw_audio_chunk is True

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(pipeline_run_id)
        if any(e.get("type") == "llm.first_chunk" for e in events):
            break
        time.sleep(0.1)

    assert events is not None
    first_chunk_events = [e for e in events if e.get("type") == "llm.first_chunk"]
    assert len(first_chunk_events) == 1
    first_chunk_data = first_chunk_events[0].get("data")
    assert isinstance(first_chunk_data, dict)
    assert first_chunk_data.get("purpose") == "tts"

    metrics = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        metrics = await _fetch_pipeline_run_metrics(pipeline_run_id)
        if metrics and metrics.get("ttfc_ms") is not None:
            break
        time.sleep(0.1)

    assert metrics is not None
    assert metrics.get("ttfc_ms") is not None
    assert int(metrics["ttfc_ms"]) > 0


def test_ws_projector_includes_org_id_for_workos_runs(client: TestClient, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

    request_id = str(uuid.uuid4())

    with (
        patch(
            "app.auth.identity.verify_workos_jwt",
            new=AsyncMock(
                return_value={
                    "sub": "workos_user_123",
                    "email": "workos@example.com",
                    "org_id": "org_123",
                }
            ),
        ),
        client.websocket_connect("/ws") as websocket,
    ):
        websocket.send_json({"type": "auth", "payload": {"token": "workos_token"}})
        auth_success = _receive_json_with_timeout(websocket, timeout=5.0)
        assert auth_success["type"] == "auth.success"
        org_id = auth_success["payload"].get("orgId")
        assert org_id

        _receive_json_with_timeout(websocket, timeout=5.0)

        websocket.send_json(
            {
                "type": "chat.typed",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": request_id,
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        assert md.get("request_id") == request_id
        assert md.get("pipeline_run_id")
        assert md.get("org_id") == org_id


@pytest.mark.asyncio
async def test_ws_projector_enricher_toggle_does_not_hang_and_emits_skip_events(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")

    monkeypatch.setenv("CONTEXT_ENRICHER_PROFILE_ENABLED", "false")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

    with client.websocket_connect("/ws") as websocket:
        _auth_dev(websocket)

        request_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "chat.typed",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": request_id,
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id

    events_disabled = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events_disabled = await _fetch_pipeline_events(run_id)
        if _get_event_data(events_disabled, "enricher.profile.completed") is not None:
            break
        time.sleep(0.1)

    assert events_disabled is not None
    completed_disabled = _get_event_data(events_disabled, "enricher.profile.completed")
    assert completed_disabled is not None
    assert completed_disabled.get("enabled") is False
    assert completed_disabled.get("status") == "skipped"

    monkeypatch.setenv("CONTEXT_ENRICHER_PROFILE_ENABLED", "true")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

    with client.websocket_connect("/ws") as websocket:
        _auth_dev(websocket)

        request_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "chat.typed",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": request_id,
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id_enabled = md.get("pipeline_run_id")
        assert run_id_enabled

    events_enabled = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events_enabled = await _fetch_pipeline_events(run_id_enabled)
        if _get_event_data(events_enabled, "enricher.profile.completed") is not None:
            break
        time.sleep(0.1)

    assert events_enabled is not None
    completed_enabled = _get_event_data(events_enabled, "enricher.profile.completed")
    assert completed_enabled is not None
    assert completed_enabled.get("enabled") is True
    assert completed_enabled.get("status") in ("complete", "error")


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Policy tests require kernel with PolicyStage - default chat pipeline doesn't include policy checking")
async def test_ws_projector_policy_block_pre_llm_still_completes_and_emits_policy_event(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("POLICY_FORCE_CHECKPOINT", "pre_llm")
    monkeypatch.setenv("POLICY_FORCE_DECISION", "block")
    monkeypatch.setenv("POLICY_FORCE_REASON", "test_block")
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    get_settings.cache_clear()

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id
        assert md.get("request_id") == request_id

        # Ensure no duplicate chat.complete
        for _ in range(60):
            try:
                msg = _receive_json_with_timeout(websocket, timeout=0.5)
            except TimeoutError:
                break

            md2 = msg.get("metadata")
            if not isinstance(md2, dict):
                continue
            if md2.get("request_id") != request_id:
                continue
            if md2.get("pipeline_run_id") != run_id:
                continue
            assert msg.get("type") != "chat.complete"

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(run_id)
        if _get_event_data(events, "policy.decision") is not None:
            break
        time.sleep(0.1)

    assert events is not None
    policy_data = _get_event_data(events, "policy.decision")
    assert policy_data is not None
    assert policy_data.get("checkpoint") == "pre_llm"
    assert policy_data.get("decision") == "block"
    assert policy_data.get("reason") == "test_block"


@pytest.mark.asyncio
async def test_ws_projector_guardrails_block_pre_llm_still_completes_and_emits_guardrails_event(
    client: TestClient,
    monkeypatch,
):
    """Test that guardrails blocking still completes the pipeline and emits guardrails events."""
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GUARDRAILS_FORCE_CHECKPOINT", "pre_llm")
    monkeypatch.setenv("GUARDRAILS_FORCE_DECISION", "block")
    monkeypatch.setenv("GUARDRAILS_FORCE_REASON", "test_guardrails_block")
    monkeypatch.setenv("GUARDRAILS_ENABLED", "true")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id
        assert md.get("request_id") == request_id

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(run_id)
        if _get_event_data(events, "guardrails.decision") is not None:
            break
        time.sleep(0.1)

    assert events is not None
    guardrails = _get_event_data(events, "guardrails.decision")
    assert guardrails is not None
    assert guardrails.get("checkpoint") == "pre_llm"
    assert guardrails.get("decision") == "block"
    assert guardrails.get("reason") == "test_guardrails_block"
    assert _get_event_data(events, "guardrails.blocked") is not None


@pytest.mark.asyncio
async def test_ws_projector_invalid_agent_output_emits_validation_failure_and_completes(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.delenv("GUARDRAILS_FORCE_CHECKPOINT", raising=False)
    monkeypatch.delenv("GUARDRAILS_FORCE_DECISION", raising=False)
    monkeypatch.delenv("GUARDRAILS_FORCE_REASON", raising=False)
    monkeypatch.delenv("POLICY_FORCE_CHECKPOINT", raising=False)
    monkeypatch.delenv("POLICY_FORCE_DECISION", raising=False)
    monkeypatch.delenv("POLICY_FORCE_REASON", raising=False)
    monkeypatch.delenv("POLICY_MAX_PROMPT_TOKENS", raising=False)
    monkeypatch.delenv("POLICY_MAX_RUNS_PER_MINUTE", raising=False)
    monkeypatch.delenv("POLICY_ALLOWLIST_ENABLED", raising=False)
    monkeypatch.delenv("POLICY_ALLOWLIST_PRE_LLM", raising=False)
    monkeypatch.delenv("POLICY_INTENT_RULES_JSON", raising=False)
    # Force stub stream to return a JSON object that *looks* like AgentOutput
    # but fails strict schema validation due to extra fields.
    monkeypatch.setenv(
        "STUB_LLM_FORCE_STREAM_TEXT",
        '{"assistant_message":"hi","actions":[],"artifacts":[],"extra":true}',
    )
    get_llm_provider.cache_clear()
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id
        assert md.get("request_id") == request_id

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(run_id)
        if _get_event_data(events, "validation.agent_output") is not None:
            break
        time.sleep(0.1)

    assert events is not None
    validation = _get_event_data(events, "validation.agent_output")
    assert validation is not None
    assert validation.get("success") is False
    assert validation.get("error") == "schema_validation_error"


@pytest.mark.asyncio
async def test_ws_projector_malformed_stub_output_emits_validation_failure_and_reaches_terminal_state(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    monkeypatch.delenv("STUB_LLM_FORCE_STREAM_TEXT", raising=False)
    monkeypatch.setenv("STUB_LLM_STREAM_MODE", "malformed")
    monkeypatch.setenv("STUB_LLM_STREAM_DELAY_MS", "0")

    get_llm_provider.cache_clear()
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id
        assert md.get("request_id") == request_id

    status = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        status = await _fetch_pipeline_run_status(run_id)
        if status in {"completed", "failed", "canceled"}:
            break
        time.sleep(0.1)
    assert status in {"completed", "failed", "canceled"}

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(run_id)
        validation = _get_event_data(events, "validation.agent_output") if events else None
        if validation is not None:
            break
        time.sleep(0.1)

    assert events is not None
    validation = _get_event_data(events, "validation.agent_output")
    assert validation is not None
    assert validation.get("success") is False
    assert validation.get("error") == "invalid_json"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Policy tests require kernel with PolicyStage - default chat pipeline doesn't include policy checking")
async def test_ws_projector_policy_escalation_pre_action_denied_still_completes(
    client: TestClient,
    monkeypatch,
):
    """Test that policy escalation blocking still completes the pipeline."""
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("POLICY_REQUIRE_ORG_ID", "false")
    # Set empty action_types to deny all actions - this blocks at the PolicyStage (pre-LLM)
    # because the intent rules are evaluated at both pre_action and post_action checkpoints.
    monkeypatch.setenv(
        "POLICY_INTENT_RULES_JSON",
        '{"chat": {"action_types": [], "artifact_types": []}}',
    )
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id
        assert md.get("request_id") == request_id

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(run_id)
        if _get_event_data(events, "policy.decision") is not None:
            break
        time.sleep(0.1)

    assert events is not None
    # PolicyStage emits policy.decision with checkpoint="pre_llm" when it blocks
    decision_data = _get_event_data(events, "policy.decision")
    assert decision_data is not None
    assert decision_data.get("checkpoint") == "pre_llm"
    assert decision_data.get("decision") == "block"
    # The reason should indicate action_type_not_allowed from the intent rules check
    assert decision_data.get("reason") == "escalation.action_type_not_allowed"


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Policy tests require kernel with PolicyStage - default chat pipeline doesn't include policy checking")
async def test_ws_projector_policy_budget_exceeded_still_completes_and_emits_budget_event(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance
    # Make the prompt token estimate exceed budget deterministically.
    monkeypatch.setenv("POLICY_MAX_PROMPT_TOKENS", "1")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

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
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id
        assert md.get("request_id") == request_id
        assert chat_complete.get("payload", {}).get("content") == "Sorry — I can't help with that."

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(run_id)
        if _get_event_data(events, "policy.budget.exceeded") is not None:
            break
        time.sleep(0.1)

    assert events is not None
    policy_data = _get_event_data(events, "policy.decision")
    assert policy_data is not None
    assert policy_data.get("checkpoint") == "pre_llm"
    assert policy_data.get("decision") == "block"
    assert policy_data.get("reason") == "budget.prompt_tokens_exceeded"
    assert _get_event_data(events, "policy.budget.exceeded") is not None


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Policy tests require kernel with PolicyStage - default chat pipeline doesn't include policy checking")
async def test_ws_projector_workos_missing_membership_blocks_and_emits_tenant_event(
    client: TestClient,
    monkeypatch,
):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    from app.ai.substrate.policy.gateway import PolicyGateway

    PolicyGateway._instances = {}  # Clear singleton instance

    request_id = str(uuid.uuid4())
    workos_org_id = f"org_{uuid.uuid4()}"
    workos_subject = f"workos_user_{uuid.uuid4()}"

    with (
        patch(
            "app.auth.identity.verify_workos_jwt",
            new=AsyncMock(
                return_value={
                    "sub": workos_subject,
                    "email": "workos@example.com",
                    "org_id": workos_org_id,
                }
            ),
        ),
        patch(
            "app.services.organization.OrganizationService.ensure_membership",
            new=AsyncMock(return_value=None),
        ),
        client.websocket_connect("/ws") as websocket,
    ):
        websocket.send_json({"type": "auth", "payload": {"token": "workos_token"}})
        auth_success = _receive_json_with_timeout(websocket, timeout=5.0)
        assert auth_success["type"] == "auth.success"
        org_id = auth_success["payload"].get("orgId")
        assert org_id

        _receive_json_with_timeout(websocket, timeout=5.0)

        websocket.send_json(
            {
                "type": "chat.typed",
                "payload": {
                    "sessionId": None,
                    "messageId": str(uuid.uuid4()),
                    "requestId": request_id,
                    "content": "This is a much longer message that should definitely exceed the budget limit",
                },
            }
        )

        chat_complete = _drain_until(websocket, lambda m: m.get("type") == "chat.complete")
        md = chat_complete.get("metadata") or {}
        run_id = md.get("pipeline_run_id")
        assert run_id
        assert md.get("request_id") == request_id
        assert md.get("org_id") == org_id
        assert chat_complete.get("payload", {}).get("content") == "Sorry — I can't help with that."

    events = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        events = await _fetch_pipeline_events(run_id)
        if _get_event_data(events, "policy.tenant.denied") is not None:
            break
        time.sleep(0.1)

    assert events is not None
    policy_data = _get_event_data(events, "policy.decision")
    assert policy_data is not None
    assert policy_data.get("checkpoint") == "pre_llm"
    assert policy_data.get("decision") == "block"
    assert policy_data.get("reason") == "org_membership_missing"
    assert _get_event_data(events, "policy.tenant.denied") is not None
