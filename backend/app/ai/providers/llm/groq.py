"""Groq LLM provider implementation."""

import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from groq import AsyncGroq

from app.ai.providers.base import LLMMessage, LLMProvider, LLMResponse
from app.ai.providers.registry import register_llm_provider

logger = logging.getLogger("llm")


@register_llm_provider
class GroqProvider(LLMProvider):
    """Groq LLM provider using Llama models."""

    DEFAULT_MODEL = "llama-3.1-8b-instant"

    @classmethod
    def resolve_model(cls, model: str | None) -> str | None:
        m = (model or "").strip()
        if not m:
            return cls.DEFAULT_MODEL

        if m.startswith("gemini-"):
            return cls.DEFAULT_MODEL

        return m

    def __init__(self, api_key: str):
        """Initialize Groq provider.

        Args:
            api_key: Groq API key
        """
        self._client = AsyncGroq(api_key=api_key)
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "groq"

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a complete response.

        Args:
            messages: Conversation history
            model: Model ID (defaults to llama-3.1-8b-instant)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Groq-specific options

        Returns:
            LLMResponse with full content and metadata
        """
        model = model or self.DEFAULT_MODEL
        start_time = time.time()

        groq_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        logger.info(
            "Groq generate started",
            extra={
                "service": "llm",
                "provider": self.name,
                "model": model,
                "message_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "prompt": groq_messages,
            },
        )

        try:
            # Extract prompt_cache_key from kwargs if provided
            api_kwargs = kwargs.copy()
            prompt_cache_key = api_kwargs.pop("prompt_cache_key", None)
            if prompt_cache_key:
                api_kwargs["prompt_cache_key"] = prompt_cache_key

            response = await self._client.chat.completions.create(
                model=model,
                messages=groq_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **api_kwargs,
            )

            duration_ms = int((time.time() - start_time) * 1000)
            content = response.choices[0].message.content or ""
            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0
            cached_tokens = (
                response.usage.prompt_tokens_details.cached_tokens
                if (response.usage and response.usage.prompt_tokens_details)
                else 0
            )

            logger.info(
                "Groq generate complete",
                extra={
                    "service": "llm",
                    "provider": self.name,
                    "model": model,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cached_tokens": cached_tokens,
                    "duration_ms": duration_ms,
                },
            )

            return LLMResponse(
                content=content,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                finish_reason=response.choices[0].finish_reason,
                cached_tokens=cached_tokens,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Groq generate failed",
                extra={
                    "service": "llm",
                    "provider": self.name,
                    "model": model,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens.

        Args:
            messages: Conversation history
            model: Model ID (defaults to llama-3.1-8b-instant)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Groq-specific options

        Yields:
            String tokens as they are generated
        """
        model = model or self.DEFAULT_MODEL
        start_time = time.time()
        first_token_time: float | None = None
        token_count = 0

        groq_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        logger.info(
            "Groq stream started",
            extra={
                "service": "llm",
                "provider": self.name,
                "model": model,
                "message_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "prompt": groq_messages,
            },
        )

        try:
            # Extract prompt_cache_key from kwargs if provided
            api_kwargs = kwargs.copy()
            prompt_cache_key = api_kwargs.pop("prompt_cache_key", None)
            if prompt_cache_key:
                api_kwargs["prompt_cache_key"] = prompt_cache_key

            stream = await self._client.chat.completions.create(
                model=model,
                messages=groq_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **api_kwargs,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content

                    if first_token_time is None:
                        first_token_time = time.time()
                        ttft_ms = int((first_token_time - start_time) * 1000)
                        logger.debug(
                            "Groq first token",
                            extra={
                                "service": "llm",
                                "provider": self.name,
                                "model": model,
                                "ttft_ms": ttft_ms,
                            },
                        )

                    token_count += 1
                    yield token

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Groq stream complete",
                extra={
                    "service": "llm",
                    "provider": self.name,
                    "model": model,
                    "token_count": token_count,
                    "duration_ms": duration_ms,
                    "ttft_ms": (
                        int((first_token_time - start_time) * 1000) if first_token_time else None
                    ),
                },
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Groq stream failed",
                extra={
                    "service": "llm",
                    "provider": self.name,
                    "model": model,
                    "error": str(e),
                    "duration_ms": duration_ms,
                    "tokens_streamed": token_count,
                },
                exc_info=True,
            )
            raise
