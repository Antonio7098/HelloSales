"""Voice module commands."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from hello_sales_backend.platform.voice import AudioFormat


class TranscribeAudioCommand(BaseModel):
    """Request speech-to-text transcription."""

    audio: bytes = Field(min_length=1)
    audio_format: AudioFormat
    sample_rate_hz: int | None = Field(default=None, ge=8000, le=192000)
    channels: int | None = Field(default=None, ge=1, le=8)
    duration_ms: int | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=32)
    model: str | None = Field(default=None, max_length=100)
    enable_interim: bool = False
    enable_speaker_metadata: bool = False


class SynthesizeSpeechCommand(BaseModel):
    """Request text-to-speech synthesis."""

    text: str = Field(min_length=1, max_length=8000)
    voice: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    output_format: AudioFormat = AudioFormat.PCM
    sample_rate_hz: int | None = Field(default=24000, ge=8000, le=192000)
    instructions: str | None = Field(default=None, max_length=1000)
    stream: bool = False

    @field_validator("text", "voice", "model", "instructions", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class StreamTextToSpeechCommand(BaseModel):
    """Request streaming text segmentation and TTS."""

    text_deltas: tuple[str, ...]
    voice: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    output_format: AudioFormat = AudioFormat.PCM
    sample_rate_hz: int | None = Field(default=24000, ge=8000, le=192000)
    max_segment_chars: int = Field(default=180, ge=20, le=1000)
    max_delay_ms: int = Field(default=300, ge=0, le=5000)


class RunDuplexSessionCommand(BaseModel):
    """Run an in-process duplex session from queued audio inputs."""

    audio_inputs: tuple[bytes, ...]
    audio_format: AudioFormat = AudioFormat.WAV
    voice: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    output_format: AudioFormat = AudioFormat.PCM
    sample_rate_hz: int | None = Field(default=24000, ge=8000, le=192000)
    response_text: str = Field(default="Acknowledged.", min_length=1, max_length=8000)
