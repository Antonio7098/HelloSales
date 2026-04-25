"""Application-owned voice service primitives."""

from __future__ import annotations

from hello_sales_backend.modules.voice.use_cases.commands import (
    RunDuplexSessionCommand,
    StreamTextToSpeechCommand,
    SynthesizeSpeechCommand,
    TranscribeAudioCommand,
)
from hello_sales_backend.modules.voice.use_cases.session import (
    VoiceSessionRuntime,
    new_voice_session_id,
)
from hello_sales_backend.modules.voice.use_cases.streaming import (
    LLMToTTSBridge,
    TextSegmenter,
    iter_text_deltas,
)
from hello_sales_backend.modules.voice.use_cases.views import (
    SpeechChunkView,
    SpeechSynthesisView,
    TranscriptEventView,
    TranscriptionView,
    VoiceEventView,
    VoiceSessionView,
)
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.platform.voice import (
    AudioInput,
    SpeechChunk,
    SpeechSynthesisRequest,
    STTProviderPort,
    TranscriptionRequest,
    TTSProviderPort,
    TurnDetectionPort,
    VoiceCallContext,
)
from hello_sales_backend.platform.voice.errors import provider_disabled, voice_error


class VoiceService:
    """Expose provider-neutral STT, TTS, bridge, and duplex primitives."""

    def __init__(
        self,
        *,
        settings: Settings,
        stt_provider: STTProviderPort,
        tts_provider: TTSProviderPort,
        turn_detection: TurnDetectionPort,
        observability: ObservabilityRuntime,
    ) -> None:
        self._settings = settings
        self._stt_provider = stt_provider
        self._tts_provider = tts_provider
        self._turn_detection = turn_detection
        self._observability = observability

    async def transcribe(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        org_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        command: TranscribeAudioCommand,
    ) -> TranscriptionView:
        if not self._stt_provider.is_configured():
            raise provider_disabled("stt", self._stt_provider.provider_name)
        audio = self._audio_input(command)
        context = self._context(
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
            org_id=org_id,
            user_id=user_id,
            session_id=session_id,
            operation="voice.stt.transcribe",
        )
        try:
            result = await self._stt_provider.transcribe(
                TranscriptionRequest(
                    audio=audio,
                    model=command.model,
                    language=command.language,
                    enable_interim=command.enable_interim,
                    enable_speaker_metadata=command.enable_speaker_metadata,
                ),
                context=context,
            )
        except Exception as exc:
            raise voice_error(
                "Voice STT provider failed",
                code="voice.stt.provider_failed",
                details={"provider": self._stt_provider.provider_name, "raw_audio_redacted": True},
                operation="voice.stt.transcribe",
                exc=exc,
            ) from exc
        await self._emit("voice.transcript.final", context, {"provider": result.provider, "chars": len(result.text)})
        return TranscriptionView(
            provider=result.provider,
            text=result.text,
            events=[
                TranscriptEventView(
                    kind=event.kind.value,
                    text=event.text,
                    sequence_no=event.sequence_no,
                    confidence=event.confidence,
                    language=event.language,
                    speaker_id=event.speaker_id,
                    provider=event.provider,
                    model=event.model,
                    metadata=event.metadata,
                )
                for event in result.events
            ],
            language=result.language,
            duration_ms=result.duration_ms,
            metadata={**result.metadata, "raw_audio_persisted": self._settings.voice_persist_raw_audio},
        )

    async def synthesize(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: SynthesizeSpeechCommand,
    ) -> SpeechSynthesisView:
        if not self._tts_provider.is_configured():
            raise provider_disabled("tts", self._tts_provider.provider_name)
        context = self._context(
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
            operation="voice.tts.synthesize",
        )
        request = self._speech_request(command)
        try:
            result = await self._tts_provider.synthesize(request, context=context)
        except Exception as exc:
            raise voice_error(
                "Voice TTS provider failed",
                code="voice.tts.provider_failed",
                details={"provider": self._tts_provider.provider_name, "text_redacted": True},
                operation="voice.tts.synthesize",
                exc=exc,
            ) from exc
        await self._emit("voice.tts.first_chunk", context, {"provider": result.provider, "chunks": len(result.chunks)})
        return SpeechSynthesisView(
            provider=result.provider,
            audio=result.audio,
            chunks=[_chunk_view(chunk) for chunk in result.chunks],
            voice=result.voice,
            model=result.model,
            output_format=result.output_format.value,
            sample_rate_hz=result.sample_rate_hz,
            metadata=result.metadata,
        )

    async def stream_text_to_speech(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: StreamTextToSpeechCommand,
    ) -> list[VoiceEventView]:
        if not self._tts_provider.is_configured():
            raise provider_disabled("tts", self._tts_provider.provider_name)
        context = self._context(
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
            voice_session_id=new_voice_session_id(),
            operation="voice.stream.llm_to_tts",
        )
        bridge = LLMToTTSBridge(
            tts_provider=self._tts_provider,
            segmenter=TextSegmenter(
                max_chars=command.max_segment_chars,
                max_delay_seconds=command.max_delay_ms / 1000,
            ),
        )
        request = SpeechSynthesisRequest(
            text="placeholder",
            voice=command.voice or self._settings.voice_default_tts_voice or None,
            model=command.model or self._settings.voice_tts_model or None,
            output_format=command.output_format,
            sample_rate_hz=command.sample_rate_hz,
        )
        events = [
            VoiceEventView.model_validate(event.model_dump(mode="python"))
            async for event in bridge.stream(iter_text_deltas(command.text_deltas), request=request, context=context)
        ]
        for event in events:
            await self._emit(event.event_type, context, {"sequence_no": event.sequence_no})
        return events

    async def run_fake_duplex(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: RunDuplexSessionCommand,
    ) -> VoiceSessionView:
        if not self._stt_provider.is_configured():
            raise provider_disabled("stt", self._stt_provider.provider_name)
        if not self._tts_provider.is_configured():
            raise provider_disabled("tts", self._tts_provider.provider_name)
        context = self._context(
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
            voice_session_id=new_voice_session_id(),
            operation="voice.session.duplex",
        )
        runtime = VoiceSessionRuntime(
            stt_provider=self._stt_provider,
            tts_provider=self._tts_provider,
            turn_detection=self._turn_detection,
        )
        audio_inputs = tuple(
            AudioInput(
                data=item,
                format=command.audio_format,
                sample_rate_hz=command.sample_rate_hz,
            )
            for item in command.audio_inputs
        )
        speech_request = SpeechSynthesisRequest(
            text=command.response_text,
            voice=command.voice or self._settings.voice_default_tts_voice or None,
            model=command.model or self._settings.voice_tts_model or None,
            output_format=command.output_format,
            sample_rate_hz=command.sample_rate_hz,
        )
        events = await runtime.run_fake_duplex(
            audio_inputs=audio_inputs,
            response_text=command.response_text,
            speech_request=speech_request,
            context=context,
        )
        for event in events:
            await self._emit(event.event_type, context, {"sequence_no": event.sequence_no})
        return VoiceSessionView(
            voice_session_id=context.voice_session_id or "",
            state=runtime.state.value,
            events=[VoiceEventView.model_validate(event.model_dump(mode="python")) for event in events],
            active_tasks=runtime.active_task_count,
            terminal_error_code=runtime.terminal_error_code,
        )

    def _audio_input(self, command: TranscribeAudioCommand) -> AudioInput:
        max_bytes = self._settings.voice_max_audio_bytes
        if len(command.audio) > max_bytes:
            raise voice_error(
                "Voice audio payload exceeds the configured limit",
                code="voice.stt.audio_too_large",
                category="validation",
                status_code=413,
                details={"max_audio_bytes": max_bytes, "raw_audio_redacted": True},
                operation="voice.stt.validate",
            )
        return AudioInput(
            data=command.audio,
            format=command.audio_format,
            sample_rate_hz=command.sample_rate_hz,
            channels=command.channels,
            duration_ms=command.duration_ms,
            language=command.language,
        )

    def _speech_request(self, command: SynthesizeSpeechCommand) -> SpeechSynthesisRequest:
        if not command.text.strip():
            raise voice_error(
                "Voice TTS text is empty",
                code="voice.tts.empty_text",
                category="validation",
                status_code=422,
                operation="voice.tts.validate",
            )
        return SpeechSynthesisRequest(
            text=command.text,
            voice=command.voice or self._settings.voice_default_tts_voice or None,
            model=command.model or self._settings.voice_tts_model or None,
            output_format=command.output_format,
            sample_rate_hz=command.sample_rate_hz,
            instructions=command.instructions,
        )

    def _context(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        org_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        voice_session_id: str | None = None,
        operation: str,
    ) -> VoiceCallContext:
        return VoiceCallContext(
            request_id=request_id,
            trace_id=trace_id,
            actor_id=actor_id,
            org_id=org_id,
            user_id=user_id,
            session_id=session_id,
            voice_session_id=voice_session_id,
            operation=operation,
        )

    async def _emit(self, event_type: str, context: VoiceCallContext, payload: dict[str, object]) -> None:
        await self._observability.emit(
            OperationalEvent(
                event_type=event_type,
                severity="info",
                component="voice",
                operation=context.operation,
                correlation_id=context.request_id,
                trace_id=context.trace_id,
                code=event_type,
                payload=payload,
            )
        )


def _chunk_view(chunk: SpeechChunk) -> SpeechChunkView:
    data = chunk.model_dump(mode="python")
    data["kind"] = chunk.kind.value
    data["output_format"] = chunk.output_format.value
    data["audio"] = data.pop("data")
    return SpeechChunkView.model_validate(data)
