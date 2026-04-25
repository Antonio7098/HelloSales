from __future__ import annotations

import pytest

from hello_sales_backend.modules.voice.use_cases.commands import (
    RunDuplexSessionCommand,
    StreamTextToSpeechCommand,
    SynthesizeSpeechCommand,
    TranscribeAudioCommand,
)
from hello_sales_backend.modules.voice.use_cases.streaming import TextSegmenter
from hello_sales_backend.modules.voice.use_cases.voice_service import VoiceService
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import (
    AlertPolicy,
    InMemoryOperationalStore,
    ObservabilityRuntime,
)
from hello_sales_backend.platform.voice import AudioFormat
from hello_sales_backend.platform.voice.providers import (
    FakeSTTProvider,
    FakeTTSProvider,
    FakeTurnDetectionProvider,
)
from hello_sales_backend.shared.errors import AppError


def _service(settings: Settings | None = None) -> VoiceService:
    return VoiceService(
        settings=settings or Settings(database_url="sqlite+aiosqlite:///:memory:", voice_tts_model="fake-tts"),
        stt_provider=FakeSTTProvider(),
        tts_provider=FakeTTSProvider(),
        turn_detection=FakeTurnDetectionProvider(),
        observability=ObservabilityRuntime(store=InMemoryOperationalStore(), alert_policy=AlertPolicy()),
    )


def test_text_segmenter_flushes_on_punctuation_and_length() -> None:
    segmenter = TextSegmenter(max_chars=10, max_delay_seconds=999)

    assert segmenter.push("Hello") == []
    assert segmenter.push(" world.") == ["Hello world."]
    assert segmenter.push("abcdefghijk") == ["abcdefghijk"]


async def test_voice_service_transcribes_with_fake_provider() -> None:
    result = await _service().transcribe(
        request_id="request-1",
        trace_id="trace-1",
        actor_id="actor-1",
        command=TranscribeAudioCommand(audio=b"hello there", audio_format=AudioFormat.WAV),
    )

    assert result.provider == "fake-stt"
    assert result.text == "hello there"
    assert result.events[0].kind == "final"
    assert result.metadata["raw_audio_persisted"] is False


async def test_voice_service_rejects_oversized_audio() -> None:
    service = _service(Settings(database_url="sqlite+aiosqlite:///:memory:", voice_max_audio_bytes=3))

    with pytest.raises(AppError) as exc_info:
        await service.transcribe(
            request_id=None,
            trace_id=None,
            actor_id=None,
            command=TranscribeAudioCommand(audio=b"too large", audio_format=AudioFormat.WAV),
        )

    assert exc_info.value.code == "voice.stt.audio_too_large"
    assert exc_info.value.details["raw_audio_redacted"] is True


async def test_voice_service_synthesizes_with_fake_provider() -> None:
    result = await _service().synthesize(
        request_id="request-1",
        trace_id="trace-1",
        actor_id="actor-1",
        command=SynthesizeSpeechCommand(text="Hello.", voice="fake", output_format=AudioFormat.PCM),
    )

    assert result.provider == "fake-tts"
    assert result.audio.startswith(b"AUDIO:")
    assert [chunk.kind for chunk in result.chunks] == ["delta", "delta", "completed"]


async def test_llm_to_tts_bridge_orders_segments_and_audio() -> None:
    events = await _service().stream_text_to_speech(
        request_id="request-1",
        trace_id="trace-1",
        actor_id="actor-1",
        command=StreamTextToSpeechCommand(text_deltas=("Hello", " world.", " Next.")),
    )

    event_types = [event.event_type for event in events]
    assert event_types[0] == "voice.text.segment"
    assert "voice.audio.delta" in event_types
    assert event_types[-1] == "voice.audio.completed"
    assert [event.sequence_no for event in events] == sorted(event.sequence_no for event in events)


async def test_fake_duplex_session_has_terminal_state_and_events() -> None:
    result = await _service().run_fake_duplex(
        request_id="request-1",
        trace_id="trace-1",
        actor_id="actor-1",
        command=RunDuplexSessionCommand(
            audio_inputs=(b"hello",),
            audio_format=AudioFormat.WAV,
            response_text="Hi.",
        ),
    )

    assert result.state == "completed"
    assert result.active_tasks == 0
    assert result.events[0].event_type == "voice.session.started"
    assert any(event.event_type == "voice.transcript.final" for event in result.events)
    assert result.events[-1].event_type == "voice.session.completed"
