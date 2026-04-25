"""In-process duplex voice session runtime."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from hello_sales_backend.modules.voice.use_cases.streaming import LLMToTTSBridge, iter_text_deltas
from hello_sales_backend.platform.voice import (
    AudioInput,
    SpeechSynthesisRequest,
    STTProviderPort,
    TranscriptEventKind,
    TranscriptionRequest,
    TTSProviderPort,
    TurnDetectionPort,
    VoiceCallContext,
    VoiceEvent,
    VoiceEventKind,
    VoiceSessionState,
)
from hello_sales_backend.shared.ids import new_id


@dataclass(slots=True)
class VoiceSessionRuntime:
    """Coordinate STT, turn detection, TTS, interruption, and terminal state."""

    stt_provider: STTProviderPort
    tts_provider: TTSProviderPort
    turn_detection: TurnDetectionPort
    events: list[VoiceEvent] = field(default_factory=list)
    state: VoiceSessionState = VoiceSessionState.PENDING
    terminal_error_code: str | None = None
    _sequence_no: int = 0
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    _active_tasks: set[asyncio.Task[object]] = field(default_factory=set)

    @property
    def active_task_count(self) -> int:
        return len([task for task in self._active_tasks if not task.done()])

    async def run_fake_duplex(
        self,
        *,
        audio_inputs: tuple[AudioInput, ...],
        response_text: str,
        speech_request: SpeechSynthesisRequest,
        context: VoiceCallContext,
    ) -> list[VoiceEvent]:
        self._transition(VoiceSessionState.LISTENING, VoiceEventKind.SESSION_STARTED.value, context)
        try:
            for audio in audio_inputs:
                if self._cancel_event.is_set():
                    break
                if self.state == VoiceSessionState.SPEAKING:
                    self._interrupt(context)
                self._transition(VoiceSessionState.TRANSCRIBING, "voice.session.transcribing", context)
                result = await self.stt_provider.transcribe(
                    TranscriptionRequest(audio=audio, enable_interim=True),
                    context=context,
                )
                for transcript in result.events:
                    self._emit(
                        VoiceEventKind.TRANSCRIPT_FINAL.value
                        if transcript.kind == TranscriptEventKind.FINAL
                        else VoiceEventKind.TRANSCRIPT_INTERIM.value,
                        context,
                        payload={
                            "text": transcript.text,
                            "confidence": transcript.confidence,
                            "provider": transcript.provider,
                        },
                    )
                    decision = await self.turn_detection.evaluate(transcript, state=self.state, context=context)
                    if decision.should_interrupt:
                        self._interrupt(context)
                self._transition(VoiceSessionState.THINKING, "voice.session.thinking", context)
                await self._speak(response_text=response_text, speech_request=speech_request, context=context)
            if self._cancel_event.is_set():
                self._transition(VoiceSessionState.CANCELLED, VoiceEventKind.SESSION_CANCELLED.value, context)
            elif self.state not in {VoiceSessionState.FAILED, VoiceSessionState.CANCELLED}:
                self._transition(VoiceSessionState.COMPLETED, VoiceEventKind.SESSION_COMPLETED.value, context)
        except asyncio.CancelledError:
            self.cancel(context=context)
            raise
        except Exception as exc:
            self.terminal_error_code = "voice.session.failed"
            self._transition(
                VoiceSessionState.FAILED,
                VoiceEventKind.SESSION_FAILED.value,
                context,
                payload={"code": self.terminal_error_code, "message": str(exc)},
            )
        finally:
            await self._cancel_active_tasks()
        return self.events

    def cancel(self, *, context: VoiceCallContext) -> None:
        self._cancel_event.set()
        self._transition(VoiceSessionState.CANCELLED, VoiceEventKind.SESSION_CANCELLED.value, context)

    def _interrupt(self, context: VoiceCallContext) -> None:
        self._cancel_event.set()
        self._transition(
            VoiceSessionState.INTERRUPTED,
            VoiceEventKind.INTERRUPTED.value,
            context,
            payload={"code": "voice.interruption.barge_in"},
        )
        self._cancel_event = asyncio.Event()

    async def _speak(
        self,
        *,
        response_text: str,
        speech_request: SpeechSynthesisRequest,
        context: VoiceCallContext,
    ) -> None:
        self._transition(VoiceSessionState.SPEAKING, "voice.session.speaking", context)
        bridge = LLMToTTSBridge(tts_provider=self.tts_provider)
        async for event in bridge.stream(
            iter_text_deltas((response_text,)),
            request=speech_request,
            context=context,
            cancel_event=self._cancel_event,
        ):
            self.events.append(event.model_copy(update={"sequence_no": self._next_sequence()}))

    def _transition(
        self,
        state: VoiceSessionState,
        event_type: str,
        context: VoiceCallContext,
        *,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.state = state
        self._emit(event_type, context, payload={"state": state.value, **(payload or {})})

    def _emit(
        self,
        event_type: str,
        context: VoiceCallContext,
        *,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.events.append(
            VoiceEvent(
                event_type=event_type,
                sequence_no=self._next_sequence(),
                voice_session_id=context.voice_session_id,
                request_id=context.request_id,
                trace_id=context.trace_id,
                payload=payload or {},
            )
        )

    def _next_sequence(self) -> int:
        self._sequence_no += 1
        return self._sequence_no

    async def _cancel_active_tasks(self) -> None:
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)


async def one_shot_audio_stream(audio_inputs: tuple[AudioInput, ...]) -> AsyncIterator[AudioInput]:
    """Yield queued audio inputs for deterministic tests."""

    for audio in audio_inputs:
        yield audio


def new_voice_session_id() -> str:
    """Create a voice session id."""

    return f"voice_{new_id()}"
