"""Groq LLM provider implementation."""

from typing import AsyncIterator

import httpx

from app.config import Settings
from app.domain.errors import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.domain.protocols.providers import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMStreamChunk,
)
from app.infrastructure.telemetry.logging import get_logger

logger = get_logger(__name__)

# Groq pricing per 1M tokens (approximate, check latest)
GROQ_PRICING = {
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.2-1b-preview": {"input": 0.04, "output": 0.04},
    "llama-3.2-3b-preview": {"input": 0.06, "output": 0.06},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
}


class GroqProvider:
    """Groq LLM provider using their REST API."""

    def __init__(self, settings: Settings):
        self.api_key = settings.groq_api_key
        self.default_model = settings.default_llm_model
        self.base_url = "https://api.groq.com/openai/v1"
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate a chat completion."""
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.debug(
            "Calling Groq API",
            extra={"model": model, "message_count": len(messages)},
        )

        try:
            response = await self.client.post("/chat/completions", json=payload)

            if response.status_code == 429:
                raise ProviderRateLimitError(
                    message="Groq rate limit exceeded",
                    provider="groq",
                    operation="chat",
                    retry_after_seconds=60,
                )

            if response.status_code >= 500:
                raise ProviderUnavailableError(
                    message=f"Groq service error: {response.status_code}",
                    provider="groq",
                    operation="chat",
                )

            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                content=choice["message"]["content"],
                model=model,
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
                finish_reason=choice.get("finish_reason"),
            )

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                message="Groq request timed out",
                provider="groq",
                operation="chat",
            ) from e

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Generate a streaming chat completion."""
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or line == "data: [DONE]":
                        continue

                    if line.startswith("data: "):
                        import json

                        data = json.loads(line[6:])
                        choice = data["choices"][0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        finish_reason = choice.get("finish_reason")

                        if content or finish_reason:
                            yield LLMStreamChunk(
                                content=content,
                                is_final=finish_reason is not None,
                                finish_reason=finish_reason,
                            )

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                message="Groq stream timed out",
                provider="groq",
                operation="chat_stream",
            ) from e

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (approximate).

        Uses rough estimate of ~4 characters per token for English.
        """
        return len(text) // 4

    def calculate_cost_cents(self, tokens_in: int, tokens_out: int, model: str) -> int:
        """Calculate cost in cents for a request."""
        pricing = GROQ_PRICING.get(model, {"input": 0.1, "output": 0.1})

        # Pricing is per 1M tokens, convert to cents
        input_cost = (tokens_in / 1_000_000) * pricing["input"] * 100
        output_cost = (tokens_out / 1_000_000) * pricing["output"] * 100

        return int(input_cost + output_cost)


# Protocol compliance
_: type[LLMProvider] = GroqProvider  # type: ignore
