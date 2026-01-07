"""Formal port interfaces for dependency inversion.

This module defines abstract interfaces (ports) that abstract dependencies
like LLM, STT, TTS, Policy, and Chat services. Stages depend on these
abstractions rather than concrete implementations.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ai.providers.base import LLMMessage, STTResult
    from app.ai.providers.base import TTSResult as TTSResult
    from app.domains.chat.service import ChatContext
    from app.schemas.assessment import AssessmentResponse


@dataclass
class LlmRequest:
    """Request payload for LLM completion."""
    messages: list["LLMMessage"]  # Forward reference to provider message
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = True


@dataclass
class LlmResponse:
    """Response from LLM completion."""
    content: str
    model: str
    usage: dict[str, Any] | None = None


class LlmPort(ABC):
    """Abstract interface for Language Model providers."""

    @abstractmethod
    async def stream_completion(self, request: LlmRequest) -> AsyncIterator[str]:
        """Stream LLM completion token by token."""
        pass

    @abstractmethod
    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Get complete LLM response in one call."""
        pass


class SttPort(ABC):
    """Abstract interface for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, model: str | None = None) -> "STTResult":
        """Transcribe audio to text."""
        pass


class TtsPort(ABC):
    """Abstract interface for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None, model: str | None = None) -> AsyncIterator[bytes]:
        """Stream synthesized audio bytes for the given text."""
        pass


class PolicyPort(ABC):
    """Abstract interface for policy evaluation."""

    @abstractmethod
    async def evaluate_message(self, message: str, context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate message against policies."""
        pass

    @abstractmethod
    async def check_guardrails(self, content: str, context: dict[str, Any]) -> tuple[bool, str | None]:
        """Check content against guardrails. Returns (allowed, reason)."""
        pass


class ChatPort(ABC):
    """Abstract interface for chat services."""

    @abstractmethod
    async def get_context(self, user_id: str, session_id: str | None = None) -> "ChatContext":
        """Get chat context for user/session."""
        pass

    @abstractmethod
    async def enrich_context(self, context: "ChatContext", sources: list[str] | None = None) -> "ChatContext":
        """Enrich chat context with additional data."""
        pass

    @abstractmethod
    async def store_message(self, message: "LLMMessage", session_id: str) -> str:
        """Store a message in chat history."""
        pass

    @abstractmethod
    async def prefetch_enrichers(self, session_id: str) -> dict[str, Any]:
        """Prefetch enricher data for a session (e.g., summary, profile, meta_summary).

        Used by latency-sensitive pipelines (e.g., voice) to start DB queries earlier
        and inject results into context building.
        """
        pass

    @abstractmethod
    async def build_context(
        self,
        session_id: str,
        skills_context: list[Any] | None = None,
        platform: str | None = None,
        prefetched: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build chat context with all enrichments applied.

        Returns a dict with keys like 'messages', 'skills_context', etc.
        """
        pass


class AssessmentPort(ABC):
    """Abstract interface for assessment services."""

    @abstractmethod
    async def assess_response(self, user_message: str, assistant_response: str, context: dict[str, Any]) -> "AssessmentResponse":
        """Assess chat response quality and return structured response."""
        pass

    @abstractmethod
    async def get_assessment_history(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get assessment history for user (implementation-defined format)."""
        pass


class TriagePort(ABC):
    """Abstract interface for triage services."""

    @abstractmethod
    async def categorize_message(self, message: str, context: dict[str, Any]) -> str:
        """Categorize message into intent/type."""
        pass

    @abstractmethod
    async def extract_entities(self, message: str) -> dict[str, Any]:
        """Extract entities from message."""
        pass


class GuardrailsPort(ABC):
    """Abstract interface for guardrails/safety checking."""

    @abstractmethod
    async def check_content(self, content: str, context: dict[str, Any]) -> tuple[bool, str | None]:
        """Check content against guardrails. Returns (allowed, reason)."""
        pass


@dataclass(slots=True, frozen=True)
class StagePorts:
    """Standardized container for stage dependencies.

    This dataclass provides a unified way to pass all common dependencies
    that stages may need. It follows the dependency inversion principle
    by accepting port interfaces rather than concrete implementations.

    Usage:
        class MyStage(Stage):
            def __init__(self, ports: StagePorts) -> None:
                self._llm_port = ports.llm_port
                self._stt_port = ports.stt_port
                ...

    For backwards compatibility, individual ports can still be passed
    directly to stage constructors.
    """
    # Provider ports (abstract interfaces)
    llm_port: LlmPort | None = None
    stt_port: SttPort | None = None
    tts_port: TtsPort | None = None
    chat_port: ChatPort | None = None
    policy_port: PolicyPort | None = None
    assessment_port: AssessmentPort | None = None
    triage_port: TriagePort | None = None
    guardrails_port: GuardrailsPort | None = None

    # Database session (commonly needed)
    db: Any = None  # Type: AsyncSession

    # Call logger for observability
    call_logger: Any = None

    # Retry function for resilient operations
    retry_fn: Any = None

    # Convenience: raw providers (for gradual migration)
    llm_provider: Any = None
    stt_provider: Any = None
    tts_provider: Any = None
