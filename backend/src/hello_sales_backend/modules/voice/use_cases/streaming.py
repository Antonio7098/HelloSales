"""Streaming LLM text to TTS bridge."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from time import monotonic

from hello_sales_backend.platform.voice import (
    SpeechSynthesisRequest,
    TTSProviderPort,
    VoiceCallContext,
    VoiceEvent,
    VoiceEventKind,
)


@dataclass(slots=True)
class TextSegmenter:
    """Buffer text deltas into TTS-sized segments."""

    max_chars: int = 180
    max_delay_seconds: float = 0.3
    terminators: tuple[str, ...] = (".", "?", "!", "\n")
    _buffer: str = ""
    _last_flush_at: float = field(default_factory=monotonic)

    def push(self, delta: str, *, now: float | None = None) -> list[str]:
        if not delta:
            return []
        current_time = monotonic() if now is None else now
        self._buffer += delta
        if self._should_flush(current_time):
            return self.flush(now=current_time)
        return []

    def flush(self, *, now: float | None = None) -> list[str]:
        current_time = monotonic() if now is None else now
        text = self._buffer.strip()
        self._buffer = ""
        self._last_flush_at = current_time
        return [text] if text else []

    def _should_flush(self, now: float) -> bool:
        text = self._buffer.strip()
        if not text:
            return False
        if len(text) >= self.max_chars:
            return True
        if text.endswith(self.terminators):
            return True
        return now - self._last_flush_at >= self.max_delay_seconds


class LLMToTTSBridge:
    """Turn ordered text deltas into ordered TTS voice events."""

    def __init__(
        self,
        *,
        tts_provider: TTSProviderPort,
        segmenter: TextSegmenter | None = None,
    ) -> None:
        self._tts_provider = tts_provider
        self._segmenter = segmenter or TextSegmenter()

    async def stream(
        self,
        deltas: AsyncIterator[str],
        *,
        request: SpeechSynthesisRequest,
        context: VoiceCallContext,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[VoiceEvent]:
        event_sequence = 0
        text_sequence = 0

        async for delta in deltas:
            if cancel_event is not None and cancel_event.is_set():
                yield _event(
                    VoiceEventKind.SESSION_CANCELLED.value,
                    sequence_no=event_sequence + 1,
                    context=context,
                    payload={"code": "voice.stream.cancelled"},
                )
                return
            for segment in self._segmenter.push(delta):
                text_sequence += 1
                event_sequence += 1
                yield _event(
                    VoiceEventKind.TEXT_SEGMENT.value,
                    sequence_no=event_sequence,
                    context=context,
                    payload={"text_sequence_no": text_sequence, "text": segment},
                )
                async for event in self._synthesize_segment(
                    segment,
                    base_request=request,
                    context=context,
                    text_sequence=text_sequence,
                    start_sequence=event_sequence,
                ):
                    event_sequence = event.sequence_no
                    yield event

        for segment in self._segmenter.flush():
            text_sequence += 1
            event_sequence += 1
            yield _event(
                VoiceEventKind.TEXT_SEGMENT.value,
                sequence_no=event_sequence,
                context=context,
                payload={"text_sequence_no": text_sequence, "text": segment, "flush": True},
            )
            async for event in self._synthesize_segment(
                segment,
                base_request=request,
                context=context,
                text_sequence=text_sequence,
                start_sequence=event_sequence,
            ):
                event_sequence = event.sequence_no
                yield event
        event_sequence += 1
        yield _event(VoiceEventKind.AUDIO_COMPLETED.value, sequence_no=event_sequence, context=context)

    async def _synthesize_segment(
        self,
        segment: str,
        *,
        base_request: SpeechSynthesisRequest,
        context: VoiceCallContext,
        text_sequence: int,
        start_sequence: int,
    ) -> AsyncIterator[VoiceEvent]:
        sequence = start_sequence
        request = base_request.model_copy(update={"text": segment})
        try:
            async for chunk in self._tts_provider.stream_speech(request, context=context):
                sequence += 1
                yield _event(
                    VoiceEventKind.AUDIO_DELTA.value
                    if chunk.kind.value == "delta"
                    else VoiceEventKind.AUDIO_COMPLETED.value,
                    sequence_no=sequence,
                    context=context,
                    payload={
                        "text_sequence_no": text_sequence,
                        "chunk_sequence_no": chunk.sequence_no,
                        "audio": chunk.data,
                        "provider": chunk.provider,
                        "output_format": chunk.output_format.value,
                    },
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            sequence += 1
            yield _event(
                VoiceEventKind.SESSION_FAILED.value,
                sequence_no=sequence,
                context=context,
                payload={"code": "voice.tts.stream_failed", "message": str(exc)},
            )
            return


async def iter_text_deltas(deltas: tuple[str, ...]) -> AsyncIterator[str]:
    """Create an async delta stream for tests and smokes."""

    for delta in deltas:
        yield delta


def _event(
    event_type: str,
    *,
    sequence_no: int,
    context: VoiceCallContext,
    payload: dict[str, object] | None = None,
) -> VoiceEvent:
    return VoiceEvent(
        event_type=event_type,
        sequence_no=sequence_no,
        voice_session_id=context.voice_session_id,
        request_id=context.request_id,
        trace_id=context.trace_id,
        payload=payload or {},
    )
