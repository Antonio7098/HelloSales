"""OpenAI-compatible neutral LLM provider adapter."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx

from hello_sales_backend.platform.llm.contracts import (
    JSONGenerationResult,
    JSONSchemaHint,
    LLMCallContext,
    LLMMessage,
    ProviderToolCall,
    ProviderToolDefinition,
    TextGenerationResult,
    ToolCallCompletionResult,
)
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.redaction import redact_mapping
from hello_sales_backend.shared.errors import app_error


def _coerce_message_content(choice: object) -> str:
    if isinstance(choice, list):
        return "".join(item.get("text", "") for item in choice if isinstance(item, dict))
    return str(choice)


def _extract_tool_calls(message: dict[str, object]) -> list[ProviderToolCall]:
    tool_calls: list[ProviderToolCall] = []
    raw_calls = message.get("tool_calls", [])
    if isinstance(raw_calls, list):
        for idx, raw_call in enumerate(raw_calls):
            if isinstance(raw_call, dict):
                func = raw_call.get("function", {})
                tool_calls.append(
                    ProviderToolCall(
                        call_id=raw_call.get("id", f"call_{idx}"),
                        tool_name=func.get("name", "") if isinstance(func, dict) else "",
                        arguments=json.loads(func.get("arguments", "{}")) if isinstance(func, dict) else {},
                        raw_tool_call=raw_call,
                    )
                )
    return tool_calls


def _safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _merge_tool_call_chunks(chunks: list[dict[str, object]]) -> list[ProviderToolCall]:
    by_index: dict[int, dict[str, object]] = defaultdict(
        lambda: {"id": "", "function": {"name": "", "arguments": ""}}
    )
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        index = _safe_int(chunk.get("index"), 0)
        current = by_index[index]
        call_id = chunk.get("id")
        if isinstance(call_id, str) and call_id:
            current["id"] = call_id
        function = chunk.get("function")
        if isinstance(function, dict):
            current_function = cast(dict[str, object], current["function"])
            name = function.get("name")
            if isinstance(name, str) and name:
                current_function["name"] = name
            arguments = function.get("arguments")
            if isinstance(arguments, str) and arguments:
                current_function["arguments"] = str(current_function.get("arguments", "")) + arguments
    materialized = [by_index[idx] for idx in sorted(by_index)]
    return _extract_tool_calls({"tool_calls": materialized})


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
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        request_payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                message.model_dump(mode="json") if hasattr(message, "model_dump") else message
                for message in messages
            ],
        }
        if response_format is not None:
            request_payload["response_format"] = response_format
        if tools is not None:
            request_payload["tools"] = tools
            request_payload["parallel_tool_calls"] = False
        if tool_choice is not None:
            request_payload["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}
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

    async def _stream_chat_completion(
        self,
        *,
        messages: list[dict[str, object]],
        operation: str,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | None = None,
        on_text_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> ToolCallCompletionResult:
        request_payload: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }
        if tools is not None:
            request_payload["tools"] = tools
            request_payload["parallel_tool_calls"] = False
        if tool_choice is not None:
            request_payload["tool_choice"] = {"type": "function", "function": {"name": tool_choice}}
        self._logger.info(
            "provider.call.started",
            provider=self.provider_name,
            model=self._model,
            endpoint=f"{self._base_url}/chat/completions",
            request=redact_mapping(
                {
                    "api_key": self._api_key,
                    "message_count": len(messages),
                    "stream": True,
                    "tool_count": len(tools or []),
                }
            ),
        )
        content_parts: list[str] = []
        tool_call_chunks: list[dict[str, object]] = []
        resolved_model = self._model
        try:
            async with self._http_client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=request_payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if not data:
                        continue
                    if data == "[DONE]":
                        break
                    payload = cast(dict[str, Any], json.loads(data))
                    resolved_model = str(payload.get("model", resolved_model))
                    choices = payload.get("choices", [])
                    if not isinstance(choices, list):
                        continue
                    for choice in choices:
                        if not isinstance(choice, dict):
                            continue
                        delta = choice.get("delta", {})
                        if not isinstance(delta, dict):
                            continue
                        content_delta = delta.get("content")
                        if isinstance(content_delta, str) and content_delta:
                            content_parts.append(content_delta)
                            if on_text_delta is not None:
                                await on_text_delta(content_delta)
                        raw_tool_calls = delta.get("tool_calls", [])
                        if isinstance(raw_tool_calls, list):
                            tool_call_chunks.extend(
                                item for item in raw_tool_calls if isinstance(item, dict)
                            )
            self._logger.info(
                "provider.call.completed",
                provider=self.provider_name,
                model=resolved_model,
                message_count=len(messages),
            )
            tool_calls = _merge_tool_call_chunks(tool_call_chunks)
            content = "".join(content_parts)
            return ToolCallCompletionResult(
                provider=self.provider_name,
                model=resolved_model,
                content=None if tool_calls else content,
                tool_calls=tool_calls,
            )
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

    async def complete_with_tools(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[ProviderToolDefinition],
        context: LLMCallContext | None = None,
        tool_choice: str | None = None,
        on_text_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> ToolCallCompletionResult:
        provider_tools: list[dict[str, object]] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]
        return await self._stream_chat_completion(
            messages=messages,
            operation=(context.operation if context is not None else None) or "provider.llm.complete_with_tools",
            tools=provider_tools,
            tool_choice=tool_choice,
            on_text_delta=on_text_delta,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()
