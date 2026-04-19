"""OpenAI-compatible neutral LLM provider adapter."""

from __future__ import annotations

import json
from typing import Any, cast

import httpx

from hello_sales_backend.platform.llm.contracts import (
    JSONGenerationResult,
    JSONSchemaHint,
    LLMCallContext,
    LLMMessage,
    TextGenerationResult,
)
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.redaction import redact_mapping
from hello_sales_backend.shared.errors import app_error


def _coerce_message_content(choice: object) -> str:
    if isinstance(choice, list):
        return "".join(item.get("text", "") for item in choice if isinstance(item, dict))
    return str(choice)


def _supports_strict_json_schema(provider_name: str) -> bool:
    return provider_name in {"openai"}


class OpenAICompatibleLLMProvider:
    """Minimal OpenAI-compatible adapter for text and JSON generation."""

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

    async def generate_text(
        self,
        messages: list[LLMMessage],
        *,
        context: LLMCallContext | None = None,
    ) -> TextGenerationResult:
        payload = await self._post_chat_completion(
            messages=messages,
            response_format=None,
            operation=(context.operation if context is not None else None) or "provider.llm.generate_text",
        )
        choice = payload["choices"][0]["message"]["content"]
        return TextGenerationResult(
            provider=self.provider_name,
            model=payload.get("model", self._model),
            output_text=_coerce_message_content(choice),
            timeout_seconds=(context.timeout_seconds if context is not None else None) or self._timeout_seconds,
        )

    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint: JSONSchemaHint | None = None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult:
        response_format: dict[str, object]
        if schema_hint is None:
            response_format = {"type": "json_object"}
        else:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_hint.name,
                    "schema": schema_hint.schema,
                    "strict": schema_hint.strict and _supports_strict_json_schema(self.provider_name),
                },
            }
        payload = await self._post_chat_completion(
            messages=messages,
            response_format=response_format,
            operation=(context.operation if context is not None else None) or "provider.llm.generate_json",
        )
        raw_text = _coerce_message_content(payload["choices"][0]["message"]["content"])
        parsed: Any = None
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            parsed = None
        return JSONGenerationResult(
            provider=self.provider_name,
            model=payload.get("model", self._model),
            raw_text=raw_text,
            output_json=parsed,
            timeout_seconds=(context.timeout_seconds if context is not None else None) or self._timeout_seconds,
        )

    async def generate(self, messages: list[LLMMessage]) -> TextGenerationResult:
        """Backward-compatible chat-only entrypoint."""

        return await self.generate_text(messages)

    async def _post_chat_completion(
        self,
        *,
        messages: list[LLMMessage],
        response_format: dict[str, object] | None,
        operation: str,
    ) -> dict[str, Any]:
        request_payload: dict[str, object] = {
            "model": self._model,
            "messages": [message.model_dump(mode="json") for message in messages],
        }
        if response_format is not None:
            request_payload["response_format"] = response_format
        self._logger.info(
            "provider.call.started",
            provider=self.provider_name,
            model=self._model,
            endpoint=f"{self._base_url}/chat/completions",
            request=redact_mapping(
                {
                    "api_key": self._api_key,
                    "message_count": len(messages),
                    "response_format": response_format,
                }
            ),
        )
        try:
            response = await self._http_client.post(
                f"{self._base_url}/chat/completions",
                json=request_payload,
            )
            response.raise_for_status()
            payload = cast(dict[str, Any], response.json())
            self._logger.info(
                "provider.call.completed",
                provider=self.provider_name,
                model=payload.get("model", self._model),
                message_count=len(messages),
            )
            return payload
        except httpx.HTTPError as exc:
            self._logger.exception(
                "provider.call.failed",
                provider=self.provider_name,
                model=self._model,
                message_count=len(messages),
                operation=operation,
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
                    "operation": operation,
                },
                operation=operation,
                component="provider",
                exc=exc,
            ) from exc

    def is_configured(self) -> bool:
        return bool(self._api_key and self._model and self._base_url)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()
