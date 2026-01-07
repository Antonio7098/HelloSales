import asyncio
import uuid
from types import SimpleNamespace

import pytest

from app.ai.stages.voice import SttStage, TtsIncrementalStage
from app.ai.substrate import CircuitBreakerOpenError
from app.ai.substrate.agent.context_snapshot import ContextSnapshot
from app.ai.substrate.stages.base import StageContext, StageOutput, StageStatus
from app.ai.substrate.stages.inputs import StagePorts, create_stage_inputs


class DummyEventSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def try_emit(self, *, type: str, data: dict | None) -> None:  # noqa: A003 - external API
        self.events.append((type, data or {}))


class DummyRecording:
    def __init__(self) -> None:
        self.session_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.format = "webm"


async def _immediate_retry(fn):
    result = fn()
    if asyncio.iscoroutine(result):
        return await result
    return result


class _BreakerCallLogger:
    """Call logger stub that simulates breaker denials."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.db = None

    async def call_stt_transcribe(self, **_: object):
        raise self.error

    async def call_tts_synthesize(self, **_: object):
        raise self.error


@pytest.mark.asyncio
async def test_stt_stage_emits_degraded_and_raises_on_breaker():
    """Test STT stage handles circuit breaker error correctly."""
    recording = DummyRecording()

    # Create the context snapshot
    snapshot = ContextSnapshot(
        pipeline_run_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        session_id=recording.session_id,
        user_id=recording.user_id,
        org_id=None,
        interaction_id=None,
        topology="voice_fast",
        channel="voice",
        behavior="practice",
    )

    # Create stage context with inputs
    stage_ports = StagePorts(
        audio_data=b"audio-bytes",
        recording=recording,
    )
    inputs = create_stage_inputs(
        snapshot=snapshot,
        prior_outputs={},
        ports=stage_ports,
    )
    ctx = StageContext(
        snapshot=snapshot,
        config={"inputs": inputs},
    )

    breaker_error = CircuitBreakerOpenError("STT call denied by circuit breaker")
    stage = SttStage(
        call_logger=_BreakerCallLogger(breaker_error),
        stt_provider=SimpleNamespace(name="stub_stt", transcribe=asyncio.sleep),
        retry_fn=_immediate_retry,
    )

    result = await stage.execute(ctx)

    # The unified stage should return a failed output with stt_degraded flag
    assert result.status.value == "fail"
    assert result.data.get('stt_degraded', False)


@pytest.mark.asyncio
async def test_tts_stage_returns_degraded_stage_result_on_breaker():
    """Test TTS stage handles circuit breaker error correctly."""
    # Create the context snapshot
    snapshot = ContextSnapshot(
        pipeline_run_id=uuid.uuid4(),
        request_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        org_id=None,
        interaction_id=None,
        topology="voice_fast",
        channel="voice",
        behavior="practice",
    )

    # Create stage context with inputs - need full_response for TTS stage to proceed
    stage_ports = StagePorts()
    # Provide full_response so TTS stage doesn't fail validation
    prior_outputs = {
        "llm_stream": StageOutput(
            status=StageStatus.OK,
            data={"full_response": "Hello, this is a test response."}
        )
    }
    inputs = create_stage_inputs(
        snapshot=snapshot,
        prior_outputs=prior_outputs,
        ports=stage_ports,
    )
    ctx = StageContext(
        snapshot=snapshot,
        config={"inputs": inputs},
    )

    breaker_error = CircuitBreakerOpenError("TTS call denied by circuit breaker")
    stage = TtsIncrementalStage(
        call_logger=_BreakerCallLogger(breaker_error),
        tts_provider=SimpleNamespace(name="stub_tts", synthesize=asyncio.sleep),
        retry_fn=_immediate_retry,
    )

    result = await stage.execute(ctx)

    # The unified stage should return ok with tts_degraded flag when circuit breaker opens
    assert result.status.value == "ok"
    assert result.data.get('tts_degraded', False)
