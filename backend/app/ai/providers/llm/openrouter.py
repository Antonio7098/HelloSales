import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.ai.providers.base import LLMMessage, LLMProvider, LLMResponse
from app.ai.providers.registry import register_llm_provider

logger = logging.getLogger("llm")


@register_llm_provider
class OpenRouterProvider(LLMProvider):
    DEFAULT_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"

    @classmethod
    def resolve_model(cls, model: str | None) -> str | None:
        m = (model or "").strip()
        if not m:
            return cls.DEFAULT_MODEL

        if "/" not in m:
            return cls.DEFAULT_MODEL

        return m

    def __init__(
        self,
        api_key: str,
        http_referer: str | None = None,
        x_title: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._http_referer = (http_referer or "").strip() or None
        self._x_title = (x_title or "").strip() or None
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "openrouter"

    def _get_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._http_referer:
            headers["HTTP-Referer"] = self._http_referer
        if self._x_title:
            headers["X-Title"] = self._x_title
        return headers

    async def generate(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.time()
        effective_model = type(self).resolve_model(model) or self.DEFAULT_MODEL

        payload: dict[str, Any] = {
            "model": effective_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if kwargs:
            payload.update(kwargs)

        logger.info(
            "OpenRouter generate started",
            extra={
                "service": "llm",
                "provider": self.name,
                "model": effective_model,
                "message_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)

        response = await self._client.post(
            f"{self._base_url}/chat/completions",
            headers=self._get_headers(),
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        choices = data.get("choices") or []
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message") or {}
        content = message.get("content") or ""
        usage = data.get("usage") or {}

        tokens_in = int(usage.get("prompt_tokens") or 0)
        tokens_out = int(usage.get("completion_tokens") or 0)
        finish_reason = first_choice.get("finish_reason")
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "OpenRouter generate complete",
            extra={
                "service": "llm",
                "provider": self.name,
                "model": effective_model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "duration_ms": duration_ms,
            },
        )

        return LLMResponse(
            content=content,
            model=str(data.get("model") or effective_model),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            finish_reason=finish_reason,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        start_time = time.time()
        effective_model = type(self).resolve_model(model) or self.DEFAULT_MODEL

        payload: dict[str, Any] = {
            "model": effective_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if kwargs:
            payload.update(kwargs)

        logger.info(
            "OpenRouter stream started",
            extra={
                "service": "llm",
                "provider": self.name,
                "model": effective_model,
                "message_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)

        first_token_time: float | None = None
        token_count = 0

        async with self._client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            headers=self._get_headers(),
            json=payload,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line:
                    continue

                if line.startswith(":"):
                    continue

                if not line.startswith("data:"):
                    continue

                raw = line[len("data:") :].strip()
                if not raw:
                    continue

                if raw == "[DONE]":
                    break

                try:
                    data = json.loads(raw)
                except Exception:
                    continue

                if isinstance(data, dict) and data.get("error"):
                    raise RuntimeError(str(data.get("error")))

                choices = data.get("choices") if isinstance(data, dict) else None
                if not choices:
                    continue

                for choice in choices:
                    delta = (choice or {}).get("delta") or {}
                    token = delta.get("content")
                    if not token:
                        message = (choice or {}).get("message") or {}
                        token = message.get("content")

                    if not token:
                        continue

                    if first_token_time is None:
                        first_token_time = time.time()

                    token_count += 1
                    yield str(token)

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "OpenRouter stream complete",
            extra={
                "service": "llm",
                "provider": self.name,
                "model": effective_model,
                "token_count": token_count,
                "duration_ms": duration_ms,
                "ttft_ms": (
                    int((first_token_time - start_time) * 1000) if first_token_time else None
                ),
            },
        )
