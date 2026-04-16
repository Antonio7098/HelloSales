"""OpenAI-compatible chat provider adapter."""

from __future__ import annotations

from typing import Any

import httpx

from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.redaction import redact_mapping
from hello_sales_backend.platform.providers.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
)
from hello_sales_backend.shared.errors import app_error


class OpenAICompatibleChatModel(ChatModelPort):
    """Minimal OpenAI-compatible chat completion adapter."""

    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider_name = provider_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._logger = get_logger("hello_sales_backend.providers.llm")
        self._http_client = http_client or httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        self._owns_client = http_client is None

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion:
        request_payload = {
            "model": self._model,
            "messages": [message.model_dump(mode="json") for message in messages],
        }
        self._logger.info(
            "provider.call.started",
            provider=self.provider_name,
            model=self._model,
            endpoint=f"{self._base_url}/chat/completions",
            request=redact_mapping(
                {
                    "api_key": self._api_key,
                    "message_count": len(messages),
                }
            ),
        )
        try:
            response = await self._http_client.post(
                f"{self._base_url}/chat/completions",
                json=request_payload,
            )
            response.raise_for_status()
            payload = response.json()
            choice = payload["choices"][0]["message"]["content"]
            if isinstance(choice, list):
                content = "".join(
                    item.get("text", "")
                    for item in choice
                    if isinstance(item, dict)
                )
            else:
                content = str(choice)
            result = ChatCompletion(
                provider=self.provider_name,
                model=payload.get("model", self._model),
                output_text=content,
            )
            self._logger.info(
                "provider.call.completed",
                provider=self.provider_name,
                model=result.model,
                message_count=len(messages),
                output_length=len(result.output_text),
            )
            return result
        except httpx.HTTPError as exc:
            self._logger.exception(
                "provider.call.failed",
                provider=self.provider_name,
                model=self._model,
                message_count=len(messages),
            )
            status_code = getattr(getattr(exc, "response", None), "status_code", 502) or 502
            error_code = "provider.http.failure"
            if isinstance(exc, httpx.TimeoutException):
                error_code = "provider.timeout"
            elif isinstance(exc, httpx.HTTPStatusError):
                if status_code == 429:
                    error_code = "provider.rate_limit"
                elif status_code == 401:
                    error_code = "provider.authentication_failed"
                elif status_code >= 500:
                    error_code = "provider.remote_5xx"
            raise app_error(
                message="LLM provider request failed",
                code=error_code,
                category="provider",
                status_code=status_code if isinstance(exc, httpx.HTTPStatusError) else 502,
                retryable=isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))
                or (isinstance(exc, httpx.HTTPStatusError) and status_code in {408, 409, 425, 429, 500, 502, 503, 504}),
                details={
                    "provider": self.provider_name,
                    "model": self._model,
                    "error": str(exc),
                    "timeout_seconds": self._timeout_seconds,
                    "base_url": self._base_url,
                    "message_count": len(messages),
                    "response_status_code": status_code if isinstance(exc, httpx.HTTPStatusError) else None,
                    "provider_request_id": getattr(getattr(exc, "response", None), "headers", {}).get("x-request-id"),
                },
                operation="provider.llm.generate",
                component="provider",
                exc=exc,
            ) from exc

    def is_configured(self) -> bool:
        return bool(self._api_key and self._model and self._base_url)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()
