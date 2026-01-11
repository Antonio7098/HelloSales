"""Provider protocols - abstract interfaces for external services."""

from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class LLMMessage:
    """A message for LLM chat completion."""

    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    tokens_in: int
    tokens_out: int
    finish_reason: str | None = None


@dataclass
class LLMStreamChunk:
    """A streaming chunk from LLM provider."""

    content: str
    is_final: bool = False
    finish_reason: str | None = None


class LLMProvider(Protocol):
    """Abstract interface for LLM providers (Groq, Google, etc.)."""

    @property
    def provider_name(self) -> str:
        """Get the provider name for logging/metrics."""
        ...

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate a chat completion."""
        ...

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Generate a streaming chat completion."""
        ...

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (approximate)."""
        ...

    def calculate_cost_cents(self, tokens_in: int, tokens_out: int, model: str) -> int:
        """Calculate cost in cents for a request."""
        ...
