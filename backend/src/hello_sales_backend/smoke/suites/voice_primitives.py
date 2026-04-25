"""Voice primitive smoke suites."""

from __future__ import annotations

from pydantic import BaseModel

from hello_sales_backend.app import create_app
from hello_sales_backend.modules.voice.use_cases.commands import (
    RunDuplexSessionCommand,
    StreamTextToSpeechCommand,
    SynthesizeSpeechCommand,
    TranscribeAudioCommand,
)
from hello_sales_backend.platform.voice import AudioFormat
from hello_sales_backend.smoke.contracts import SmokeCase, SmokeContext


class VoiceSmokeResult(BaseModel):
    """Serializable voice smoke result."""

    status: str
    provider: str | None = None
    event_count: int = 0
    state: str | None = None


class VoiceSTTSmoke(SmokeCase):
    name = "voice-stt"
    description = "Run deterministic fake voice STT through the voice module."

    async def run(self, context: SmokeContext) -> VoiceSmokeResult:
        app = _build_voice_app(context)
        service = app.state.container.modules.voice.service
        result = await service.transcribe(
            request_id="smoke-voice-stt",
            trace_id="smoke-voice-stt",
            actor_id="smoke-actor",
            command=TranscribeAudioCommand(audio=b"hello voice", audio_format=AudioFormat.WAV),
        )
        return VoiceSmokeResult(status="completed", provider=result.provider, event_count=len(result.events))


class VoiceTTSSmoke(SmokeCase):
    name = "voice-tts"
    description = "Run deterministic fake voice TTS through the voice module."

    async def run(self, context: SmokeContext) -> VoiceSmokeResult:
        app = _build_voice_app(context)
        service = app.state.container.modules.voice.service
        result = await service.synthesize(
            request_id="smoke-voice-tts",
            trace_id="smoke-voice-tts",
            actor_id="smoke-actor",
            command=SynthesizeSpeechCommand(text="Hello voice.", output_format=AudioFormat.PCM),
        )
        return VoiceSmokeResult(status="completed", provider=result.provider, event_count=len(result.chunks))


class VoiceLLMToTTSSmoke(SmokeCase):
    name = "voice-llm-to-tts"
    description = "Run deterministic streaming text-to-TTS bridge."

    async def run(self, context: SmokeContext) -> VoiceSmokeResult:
        app = _build_voice_app(context)
        service = app.state.container.modules.voice.service
        events = await service.stream_text_to_speech(
            request_id="smoke-voice-bridge",
            trace_id="smoke-voice-bridge",
            actor_id="smoke-actor",
            command=StreamTextToSpeechCommand(text_deltas=("Hello", " bridge.")),
        )
        return VoiceSmokeResult(status="completed", event_count=len(events))


class VoiceDuplexSmoke(SmokeCase):
    name = "voice-duplex"
    description = "Run deterministic fake duplex voice session."

    async def run(self, context: SmokeContext) -> VoiceSmokeResult:
        app = _build_voice_app(context)
        service = app.state.container.modules.voice.service
        result = await service.run_fake_duplex(
            request_id="smoke-voice-duplex",
            trace_id="smoke-voice-duplex",
            actor_id="smoke-actor",
            command=RunDuplexSessionCommand(audio_inputs=(b"hello",), response_text="Hi."),
        )
        return VoiceSmokeResult(status="completed", event_count=len(result.events), state=result.state)


def _build_voice_app(context: SmokeContext):
    settings = context.settings.model_copy(
        update={
            "voice_stt_provider": "fake",
            "voice_tts_provider": "fake",
            "voice_realtime_provider": "fake",
            "voice_turn_detection_provider": "fake",
        }
    )
    return create_app(settings, overrides=context.overrides)
