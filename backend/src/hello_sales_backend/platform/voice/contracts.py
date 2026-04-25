"""Provider-neutral voice contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, field_validator


class AudioFormat(StrEnum):
    """Supported normalized audio container/codec labels."""

    MP3 = "mp3"
    MP4 = "mp4"
    MPEG = "mpeg"
    MPGA = "mpga"
    M4A = "m4a"
    WAV = "wav"
    WEBM = "webm"
    PCM = "pcm"


class TranscriptEventKind(StrEnum):
    """Provider-neutral transcript event kind."""

    INTERIM = "interim"
    FINAL = "final"


class SpeechChunkKind(StrEnum):
    """Provider-neutral synthesized speech event kind."""

    DELTA = "delta"
    COMPLETED = "completed"


class VoiceEventKind(StrEnum):
    """Canonical voice runtime event types."""

    SESSION_STARTED = "voice.session.started"
    SESSION_COMPLETED = "voice.session.completed"
    SESSION_FAILED = "voice.session.failed"
    SESSION_CANCELLED = "voice.session.cancelled"
    TRANSCRIPT_INTERIM = "voice.transcript.interim"
    TRANSCRIPT_FINAL = "voice.transcript.final"
    TEXT_SEGMENT = "voice.text.segment"
    AUDIO_DELTA = "voice.audio.delta"
    AUDIO_COMPLETED = "voice.audio.completed"
    INTERRUPTED = "voice.session.interrupted"


class VoiceSessionState(StrEnum):
    """Duplex voice session lifecycle state."""

    PENDING = "pending"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoiceCallContext(BaseModel):
    """Request and actor metadata propagated through voice providers."""

    request_id: str | None = None
    trace_id: str | None = None
    actor_id: str | None = None
    org_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    agent_run_id: str | None = None
    voice_session_id: str | None = None
    operation: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)
    metadata: dict[str, object] = Field(default_factory=dict)


class AudioInput(BaseModel):
    """Audio payload accepted by STT providers."""

    data: bytes = Field(min_length=1)
    format: AudioFormat
    sample_rate_hz: int | None = Field(default=None, ge=8000, le=192000)
    channels: int | None = Field(default=None, ge=1, le=8)
    duration_ms: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, min_length=2, max_length=32)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("language", mode="before")
    @classmethod
    def strip_language(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class TranscriptEvent(BaseModel):
    """One interim or final transcript event."""

    kind: TranscriptEventKind
    text: str
    sequence_no: int = Field(ge=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    language: str | None = None
    speaker_id: str | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    provider: str
    model: str | None = None
    provider_request_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class TranscriptionRequest(BaseModel):
    """Provider-neutral transcription request."""

    audio: AudioInput
    model: str | None = None
    language: str | None = None
    enable_interim: bool = False
    enable_speaker_metadata: bool = False


class TranscriptionResult(BaseModel):
    """Normalized final transcription result."""

    provider: str
    text: str
    events: list[TranscriptEvent]
    language: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    provider_request_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SpeechSynthesisRequest(BaseModel):
    """Provider-neutral speech synthesis request."""

    text: str = Field(min_length=1, max_length=8000)
    voice: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    output_format: AudioFormat = AudioFormat.PCM
    sample_rate_hz: int | None = Field(default=24000, ge=8000, le=192000)
    instructions: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, object] = Field(default_factory=dict)

    @field_validator("text", "voice", "model", "instructions", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class SpeechChunk(BaseModel):
    """One synthesized audio chunk or terminal marker."""

    kind: SpeechChunkKind
    data: bytes = b""
    sequence_no: int = Field(ge=1)
    text_sequence_no: int | None = Field(default=None, ge=1)
    provider: str
    voice: str | None = None
    model: str | None = None
    output_format: AudioFormat = AudioFormat.PCM
    sample_rate_hz: int | None = Field(default=None, ge=8000, le=192000)
    provider_request_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SpeechSynthesisResult(BaseModel):
    """Complete speech synthesis result."""

    provider: str
    audio: bytes
    chunks: list[SpeechChunk]
    voice: str | None = None
    model: str | None = None
    output_format: AudioFormat = AudioFormat.PCM
    sample_rate_hz: int | None = Field(default=None, ge=8000, le=192000)
    provider_request_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class VoiceEvent(BaseModel):
    """Provider-neutral event emitted by voice runtimes."""

    event_type: str
    sequence_no: int = Field(ge=1)
    voice_session_id: str | None = None
    turn_id: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class TurnDetectionResult(BaseModel):
    """Decision produced by a turn-detection policy."""

    speech_started: bool = False
    speech_final: bool = False
    should_interrupt: bool = False
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str = "manual"
    metadata: dict[str, object] = Field(default_factory=dict)


class VoiceTransportMessage(BaseModel):
    """Message exchanged with a transport adapter."""

    event_type: str
    audio: AudioInput | None = None
    text: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class STTProviderPort(Protocol):
    """Speech-to-text provider contract."""

    provider_name: str

    async def transcribe(
        self,
        request: TranscriptionRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> TranscriptionResult: ...

    def stream_transcript(
        self,
        request: TranscriptionRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> AsyncIterator[TranscriptEvent]: ...

    def is_configured(self) -> bool: ...


class TTSProviderPort(Protocol):
    """Text-to-speech provider contract."""

    provider_name: str

    async def synthesize(
        self,
        request: SpeechSynthesisRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> SpeechSynthesisResult: ...

    def stream_speech(
        self,
        request: SpeechSynthesisRequest,
        *,
        context: VoiceCallContext | None = None,
    ) -> AsyncIterator[SpeechChunk]: ...

    def is_configured(self) -> bool: ...


class RealtimeVoiceProviderPort(Protocol):
    """Provider-native realtime speech-to-speech extension point."""

    provider_name: str

    def start_session(
        self,
        *,
        context: VoiceCallContext | None = None,
    ) -> AsyncIterator[VoiceEvent]: ...

    def is_configured(self) -> bool: ...


class TurnDetectionPort(Protocol):
    """Turn detection and interruption policy contract."""

    provider_name: str

    async def evaluate(
        self,
        event: TranscriptEvent | AudioInput,
        *,
        state: VoiceSessionState,
        context: VoiceCallContext | None = None,
    ) -> TurnDetectionResult: ...

    def is_configured(self) -> bool: ...


class VoiceTransportPort(Protocol):
    """Transport adapter contract for duplex sessions."""

    provider_name: str

    async def receive(self) -> AsyncIterator[VoiceTransportMessage]: ...

    async def send(self, event: VoiceEvent) -> None: ...

    async def aclose(self) -> None: ...

    def is_configured(self) -> bool: ...
