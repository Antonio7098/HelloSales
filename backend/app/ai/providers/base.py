"""Abstract base classes for external service providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMMessage:
    """A message in an LLM conversation."""

    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    tokens_in: int
    tokens_out: int
    finish_reason: str | None = None
    cached_tokens: int | None = None  # Number of cached tokens for cost tracking


@dataclass
class STTResult:
    """Result from speech-to-text transcription."""

    transcript: str
    confidence: float | None = None
    duration_ms: int | None = None
    words: list[dict[str, Any]] | None = None  # Word-level timestamps


@dataclass
class TTSResult:
    """Result from text-to-speech synthesis."""

    audio_data: bytes
    format: str  # 'mp3', 'wav', 'opus'
    duration_ms: int | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers (e.g., Groq, OpenAI, Gemini)."""

    DEFAULT_MODEL: str | None = None

    @classmethod
    def resolve_model(cls, model: str | None) -> str | None:
        """Resolve a model ID for this provider.

        Subclasses can override this to enforce provider-specific model
        families. By default, returns the configured model if set, otherwise
        falls back to DEFAULT_MODEL.
        """

        m = (model or "").strip() if model is not None else ""
        return m or cls.DEFAULT_MODEL

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """Generate a complete response.

        Args:
            messages: Conversation history
            model: Model ID (provider-specific)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with full content and metadata
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens.

        Args:
            messages: Conversation history
            model: Model ID (provider-specific)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options

        Yields:
            String tokens as they are generated
        """
        pass


class STTProvider(ABC):
    """Abstract base class for STT providers (e.g., Deepgram, Whisper)."""

    DEFAULT_MODEL: str | None = None

    @classmethod
    def resolve_model(cls, model: str | None) -> str | None:
        """Resolve a model ID for this provider.

        Subclasses can override this to enforce provider-specific model
        families. By default, returns the configured model if set, otherwise
        falls back to DEFAULT_MODEL.
        """

        m = (model or "").strip() if model is not None else ""
        return m or cls.DEFAULT_MODEL

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "webm",
        language: str = "en",
        **kwargs,
    ) -> STTResult:
        """Transcribe audio to text.

        Args:
            audio_data: Raw audio bytes
            format: Audio format (webm, wav, mp3, etc.)
            language: Language code
            **kwargs: Provider-specific options

        Returns:
            STTResult with transcript and metadata
        """
        pass


class TTSProvider(ABC):
    """Abstract base class for TTS providers (e.g., Google Cloud, OpenAI)."""

    DEFAULT_VOICE: str | None = None

    @classmethod
    def resolve_voice(cls, voice: str | None) -> str | None:
        """Resolve a voice ID/preset for this provider.

        Subclasses can override this to enforce provider-specific voice
        families. By default, returns the configured voice if set, otherwise
        falls back to DEFAULT_VOICE.
        """

        v = (voice or "").strip() if voice is not None else ""
        return v or cls.DEFAULT_VOICE

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        speed: float = 1.0,
        **kwargs,
    ) -> TTSResult:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize
            voice: Voice ID (provider-specific)
            format: Output audio format
            speed: Speaking speed multiplier
            **kwargs: Provider-specific options

        Returns:
            TTSResult with audio data and metadata
        """
        pass

    async def stream(
        self,
        text: str,
        voice: str | None = None,
        format: str = "mp3",
        speed: float = 1.0,
        **kwargs,
    ) -> AsyncGenerator[bytes, None]:
        """Stream synthesized audio chunks.

        Default implementation synthesizes full audio then yields it.
        Override for true streaming support.

        Args:
            text: Text to synthesize
            voice: Voice ID (provider-specific)
            format: Output audio format
            speed: Speaking speed multiplier
            **kwargs: Provider-specific options

        Yields:
            Audio data chunks
        """
        result = await self.synthesize(text, voice, format, speed, **kwargs)
        yield result.audio_data
