"""Voice module views."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptEventView(BaseModel):
    """Transcript event returned by the voice module."""

    kind: str
    text: str
    sequence_no: int
    confidence: float | None = None
    language: str | None = None
    speaker_id: str | None = None
    provider: str
    model: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class TranscriptionView(BaseModel):
    """Normalized transcription response."""

    provider: str
    text: str
    events: list[TranscriptEventView]
    language: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SpeechChunkView(BaseModel):
    """Synthesized speech chunk metadata."""

    kind: str
    sequence_no: int
    text_sequence_no: int | None = None
    audio: bytes = b""
    provider: str
    voice: str | None = None
    model: str | None = None
    output_format: str
    sample_rate_hz: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SpeechSynthesisView(BaseModel):
    """Complete speech synthesis response."""

    provider: str
    audio: bytes
    chunks: list[SpeechChunkView]
    voice: str | None = None
    model: str | None = None
    output_format: str
    sample_rate_hz: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class VoiceEventView(BaseModel):
    """Canonical voice runtime event view."""

    event_type: str
    sequence_no: int
    voice_session_id: str | None = None
    turn_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class VoiceSessionView(BaseModel):
    """Duplex voice session result."""

    voice_session_id: str
    state: str
    events: list[VoiceEventView]
    active_tasks: int = 0
    terminal_error_code: str | None = None
