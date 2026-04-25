"""Deterministic fake voice providers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from hello_sales_backend.platform.voice.contracts import (
    AudioInput,
    SpeechChunk,
    SpeechChunkKind,
    SpeechSynthesisRequest,
    SpeechSynthesisResult,
    STTProviderPort,
    TranscriptEvent,
    TranscriptEventKind,
    TranscriptionRequest,
    TranscriptionResult,
    TTSProviderPort,
    TurnDetectionPort,
    TurnDetectionResult,
    VoiceCallContext,
    VoiceEvent,
    VoiceSessionState,
)


class FakeSTTProvider(STTProviderPort):
    """Fake STT provider that decodes UTF-8 payloads when possible."""

    provider_name = "fake-stt"

    def is_configured(self) -> bool:
        return True

    async def transcribe(
        self,
        request: TranscriptionRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> TranscriptionResult:
        text = _audio_to_text(request.audio)
        event = TranscriptEvent(
            kind=TranscriptEventKind.FINAL,
            text=text,
            sequence_no=1,
            confidence=1.0,
            language=request.language or request.audio.language or "en",
            provider=self.provider_name,
            model=request.model or "deterministic-fake-stt",
            metadata={"audio_bytes": len(request.audio.data), "raw_audio_redacted": True},
        )
        return TranscriptionResult(
            provider=self.provider_name,
            text=text,
            events=[event],
            language=event.language,
            duration_ms=request.audio.duration_ms,
            metadata={"raw_audio_redacted": True},
        )

    async def stream_transcript(
        self,
        request: TranscriptionRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> AsyncIterator[TranscriptEvent]:
        result = await self.transcribe(request, context=context)
        if request.enable_interim and result.text:
            first = result.text.split(" ", 1)[0]
            yield TranscriptEvent(
                kind=TranscriptEventKind.INTERIM,
                text=first,
                sequence_no=1,
                confidence=0.75,
                language=result.language,
                provider=self.provider_name,
                model=request.model or "deterministic-fake-stt",
            )
            final = result.events[0].model_copy(update={"sequence_no": 2})
            yield final
            return
        yield result.events[0]


class FakeTTSProvider(TTSProviderPort):
    """Fake TTS provider that emits deterministic bytes per text segment."""

    provider_name = "fake-tts"

    def is_configured(self) -> bool:
        return True

    async def synthesize(
        self,
        request: SpeechSynthesisRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> SpeechSynthesisResult:
        chunks = [chunk async for chunk in self.stream_speech(request, context=context)]
        audio = b"".join(chunk.data for chunk in chunks if chunk.kind == SpeechChunkKind.DELTA)
        return SpeechSynthesisResult(
            provider=self.provider_name,
            audio=audio,
            chunks=chunks,
            voice=request.voice or "fake",
            model=request.model or "deterministic-fake-tts",
            output_format=request.output_format,
            sample_rate_hz=request.sample_rate_hz,
            metadata={"text_chars": len(request.text)},
        )

    async def stream_speech(
        self,
        request: SpeechSynthesisRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> AsyncIterator[SpeechChunk]:
        encoded = f"AUDIO:{request.text}".encode()
        midpoint = max(1, len(encoded) // 2)
        for sequence_no, data in enumerate((encoded[:midpoint], encoded[midpoint:]), start=1):
            if not data:
                continue
            yield SpeechChunk(
                kind=SpeechChunkKind.DELTA,
                data=data,
                sequence_no=sequence_no,
                provider=self.provider_name,
                voice=request.voice or "fake",
                model=request.model or "deterministic-fake-tts",
                output_format=request.output_format,
                sample_rate_hz=request.sample_rate_hz,
            )
        yield SpeechChunk(
            kind=SpeechChunkKind.COMPLETED,
            sequence_no=3,
            provider=self.provider_name,
            voice=request.voice or "fake",
            model=request.model or "deterministic-fake-tts",
            output_format=request.output_format,
            sample_rate_hz=request.sample_rate_hz,
        )


class FakeRealtimeVoiceProvider:
    """No-op realtime S2S extension point for diagnostics and tests."""

    provider_name = "fake-realtime-voice"

    def is_configured(self) -> bool:
        return True

    async def start_session(
        self,
        *,
        context: VoiceCallContext | None = None,
    ) -> AsyncIterator[VoiceEvent]:
        yield VoiceEvent(
            event_type="voice.realtime.session.started",
            sequence_no=1,
            voice_session_id=context.voice_session_id if context else None,
        )


class FakeTurnDetectionProvider(TurnDetectionPort):
    """Simple final-transcript and speech-start based turn detection."""

    provider_name = "fake-turn-detection"

    def is_configured(self) -> bool:
        return True

    async def evaluate(
        self,
        event: TranscriptEvent | AudioInput,
        *,
        state: VoiceSessionState,
        context: VoiceCallContext | None = None,
    ) -> TurnDetectionResult:
        del context
        if isinstance(event, TranscriptEvent):
            has_words = bool(event.text.strip())
            return TurnDetectionResult(
                speech_started=has_words,
                speech_final=event.kind == TranscriptEventKind.FINAL and has_words,
                should_interrupt=state == VoiceSessionState.SPEAKING and has_words,
                confidence=event.confidence,
                reason="transcript_final" if event.kind == TranscriptEventKind.FINAL else "transcript_interim",
            )
        return TurnDetectionResult(
            speech_started=bool(event.data),
            should_interrupt=state == VoiceSessionState.SPEAKING and bool(event.data),
            reason="audio_input",
        )


def _audio_to_text(audio: AudioInput) -> str:
    try:
        decoded = audio.data.decode("utf-8").strip()
    except UnicodeDecodeError:
        decoded = ""
    return decoded or f"transcribed {len(audio.data)} bytes"
