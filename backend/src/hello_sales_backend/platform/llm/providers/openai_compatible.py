"""OpenAI-compatible neutral LLM provider adapter."""

from __future__ import annotations

import asyncio
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
from hello_sales_backend.shared.errors import AppError, app_error

TRANSIENT_PROVIDER_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
RETRYABLE_STRUCTURED_OUTPUT_FAILURE_MARKERS = (
    "failed to validate json",
    "failed to generate json",
)


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


def _json_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _provider_error_message(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message:
            return message
        code = error.get("code")
        if isinstance(code, str) and code:
            return code
    message = payload.get("message")
    if isinstance(message, str) and message:
        return message
    return "LLM provider request failed"


def _is_retryable_structured_output_failure(*, status_code: int, error_message: str) -> bool:
    if status_code != 400:
        return False
    lowered = error_message.lower()
    return any(marker in lowered for marker in RETRYABLE_STRUCTURED_OUTPUT_FAILURE_MARKERS)


def _provider_request_id(headers: httpx.Headers | dict[str, str]) -> str | None:
    return headers.get("x-request-id") or headers.get("x-openai-request-id")


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
        max_retries: int = 0,
        retry_backoff_seconds: float = 0.0,
        backup_model: str | None = None,
        backup_model_attempt: int = 2,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be >= 0")
        if backup_model_attempt < 1:
            raise ValueError("backup_model_attempt must be >= 1")
        self.provider_name = provider_name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._backup_model = backup_model or None
        self._backup_model_attempt = backup_model_attempt
        self._logger = get_logger("hello_sales_backend.providers.llm")
        self._http_client = http_client or httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        self._owns_client = http_client is None

    def _model_for_attempt(self, attempt_number: int) -> str:
        if self._backup_model is not None and attempt_number >= self._backup_model_attempt:
            return self._backup_model
        return self._model

    async def _sleep_before_retry(self, attempt_number: int) -> None:
        if self._retry_backoff_seconds <= 0:
            return
        await asyncio.sleep(self._retry_backoff_seconds * attempt_number)

    def _http_status_error(
        self,
        *,
        response: httpx.Response,
        payload: dict[str, Any],
        operation: str,
        model: str,
        message_count: int,
        attempt_number: int,
        max_attempts: int,
    ) -> AppError:
        status_code = response.status_code
        remote_message = _provider_error_message(payload)
        retryable = status_code in TRANSIENT_PROVIDER_STATUS_CODES or _is_retryable_structured_output_failure(
            status_code=status_code,
            error_message=remote_message,
        )
        error_code = "provider.http.failure"
        if status_code == 408:
            error_code = "provider.timeout"
        elif status_code == 429:
            error_code = "provider.rate_limit"
        elif status_code in {401, 403}:
            error_code = "provider.authentication_failed"
            retryable = False
        elif _is_retryable_structured_output_failure(status_code=status_code, error_message=remote_message):
            error_code = "provider.structured_output_rejected"
        elif status_code >= 500:
            error_code = "provider.remote_5xx"
        elif status_code in TRANSIENT_PROVIDER_STATUS_CODES:
            error_code = "provider.remote_retryable"
        return app_error(
            message="LLM provider request failed",
            code=error_code,
            category="provider",
            status_code=status_code,
            retryable=retryable,
            details={
                "provider": self.provider_name,
                "model": model,
                "primary_model": self._model,
                "backup_model": self._backup_model,
                "remote_error_message": remote_message,
                "remote_error_payload": payload,
                "timeout_seconds": self._timeout_seconds,
                "base_url": self._base_url,
                "message_count": message_count,
                "response_status_code": status_code,
                "provider_request_id": _provider_request_id(response.headers),
                "retry_after": response.headers.get("retry-after"),
                "operation": operation,
                "attempt": attempt_number,
                "max_attempts": max_attempts,
                "attempts_remaining": max(max_attempts - attempt_number, 0),
            },
            operation=operation,
            component="provider",
        )

    def _transport_error(
        self,
        *,
        exc: httpx.HTTPError,
        operation: str,
        model: str,
        message_count: int,
        attempt_number: int,
        max_attempts: int,
    ) -> AppError:
        status_code = getattr(getattr(exc, "response", None), "status_code", 502) or 502
        error_code = "provider.http.failure"
        if isinstance(exc, httpx.TimeoutException):
            error_code = "provider.timeout"
        elif isinstance(exc, httpx.ConnectError):
            error_code = "provider.connection_failed"
        elif isinstance(exc, httpx.HTTPStatusError):
            if status_code == 429:
                error_code = "provider.rate_limit"
            elif status_code in {401, 403}:
                error_code = "provider.authentication_failed"
            elif status_code >= 500:
                error_code = "provider.remote_5xx"
        return app_error(
            message="LLM provider request failed",
            code=error_code,
            category="provider",
            status_code=status_code if isinstance(exc, httpx.HTTPStatusError) else 502,
            retryable=isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))
            or (isinstance(exc, httpx.HTTPStatusError) and status_code in TRANSIENT_PROVIDER_STATUS_CODES),
            details={
                "provider": self.provider_name,
                "model": model,
                "primary_model": self._model,
                "backup_model": self._backup_model,
                "error": str(exc),
                "timeout_seconds": self._timeout_seconds,
                "base_url": self._base_url,
                "message_count": message_count,
                "response_status_code": status_code if isinstance(exc, httpx.HTTPStatusError) else None,
                "provider_request_id": _provider_request_id(getattr(getattr(exc, "response", None), "headers", {})),
                "operation": operation,
                "attempt": attempt_number,
                "max_attempts": max_attempts,
                "attempts_remaining": max(max_attempts - attempt_number, 0),
            },
            operation=operation,
            component="provider",
            exc=exc,
        )

    def _protocol_error(
        self,
        *,
        message: str,
        code: str,
        operation: str,
        model: str,
        message_count: int,
        attempt_number: int,
        max_attempts: int,
        retryable: bool = True,
        exc: BaseException | None = None,
        details: dict[str, object] | None = None,
    ) -> AppError:
        return app_error(
            message=message,
            code=code,
            category="provider",
            status_code=502,
            retryable=retryable,
            details={
                "provider": self.provider_name,
                "model": model,
                "primary_model": self._model,
                "backup_model": self._backup_model,
                "timeout_seconds": self._timeout_seconds,
                "base_url": self._base_url,
                "message_count": message_count,
                "operation": operation,
                "attempt": attempt_number,
                "max_attempts": max_attempts,
                "attempts_remaining": max(max_attempts - attempt_number, 0),
                **(details or {}),
            },
            operation=operation,
            component="provider",
            exc=exc,
        )

    async def _retry_or_raise(self, exc: AppError, *, attempt_number: int, max_attempts: int) -> None:
        if exc.retryable and attempt_number < max_attempts:
            self._logger.warning(
                "provider.call.retry_scheduled",
                provider=self.provider_name,
                model=exc.details.get("model"),
                operation=exc.operation,
                code=exc.code,
                attempt=attempt_number,
                next_attempt=attempt_number + 1,
                max_attempts=max_attempts,
            )
            await self._sleep_before_retry(attempt_number)
            return
        raise exc

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
        normalized_messages = [
            message.model_dump(mode="json") if hasattr(message, "model_dump") else message
            for message in messages
        ]
        max_attempts = self._max_retries + 1
        for attempt_number in range(1, max_attempts + 1):
            active_model = self._model_for_attempt(attempt_number)
            request_payload: dict[str, object] = {
                "model": active_model,
                "messages": normalized_messages,
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
                model=active_model,
                endpoint=f"{self._base_url}/chat/completions",
                attempt=attempt_number,
                max_attempts=max_attempts,
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
                payload = _json_payload(response)
                if response.status_code >= 400:
                    structured = self._http_status_error(
                        response=response,
                        payload=payload,
                        operation=operation,
                        model=active_model,
                        message_count=len(messages),
                        attempt_number=attempt_number,
                        max_attempts=max_attempts,
                    )
                    self._logger.warning(
                        "provider.call.failed",
                        provider=self.provider_name,
                        model=active_model,
                        operation=operation,
                        code=structured.code,
                        attempt=attempt_number,
                        max_attempts=max_attempts,
                        details=structured.details,
                    )
                    await self._retry_or_raise(
                        structured,
                        attempt_number=attempt_number,
                        max_attempts=max_attempts,
                    )
                    continue
                if not payload:
                    structured = self._protocol_error(
                        message="LLM provider returned a non-JSON response",
                        code="provider.response.invalid_json",
                        operation=operation,
                        model=active_model,
                        message_count=len(messages),
                        attempt_number=attempt_number,
                        max_attempts=max_attempts,
                    )
                    await self._retry_or_raise(
                        structured,
                        attempt_number=attempt_number,
                        max_attempts=max_attempts,
                    )
                    continue
                self._logger.info(
                    "provider.call.completed",
                    provider=self.provider_name,
                    model=payload.get("model", active_model),
                    message_count=len(messages),
                    attempt=attempt_number,
                    max_attempts=max_attempts,
                )
                return payload
            except httpx.HTTPError as exc:
                structured = self._transport_error(
                    exc=exc,
                    operation=operation,
                    model=active_model,
                    message_count=len(messages),
                    attempt_number=attempt_number,
                    max_attempts=max_attempts,
                )
                self._logger.exception(
                    "provider.call.failed",
                    provider=self.provider_name,
                    model=active_model,
                    message_count=len(messages),
                    operation=operation,
                    code=structured.code,
                    attempt=attempt_number,
                    max_attempts=max_attempts,
                )
                await self._retry_or_raise(
                    structured,
                    attempt_number=attempt_number,
                    max_attempts=max_attempts,
                )
                continue
        raise self._protocol_error(
            message="LLM provider retry loop exhausted without terminal state",
            code="provider.retry_loop_exhausted",
            operation=operation,
            model=self._model_for_attempt(max_attempts),
            message_count=len(messages),
            attempt_number=max_attempts,
            max_attempts=max_attempts,
            retryable=False,
        )

    async def _stream_chat_completion(
        self,
        *,
        messages: list[dict[str, object]],
        operation: str,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | None = None,
        on_text_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> ToolCallCompletionResult:
        max_attempts = self._max_retries + 1
        for attempt_number in range(1, max_attempts + 1):
            active_model = self._model_for_attempt(attempt_number)
            request_payload: dict[str, object] = {
                "model": active_model,
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
                model=active_model,
                endpoint=f"{self._base_url}/chat/completions",
                attempt=attempt_number,
                max_attempts=max_attempts,
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
            resolved_model = active_model
            try:
                async with self._http_client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=request_payload,
                ) as response:
                    if response.status_code >= 400:
                        response_body = await response.aread()
                        try:
                            payload = json.loads(response_body)
                        except json.JSONDecodeError:
                            payload = {}
                        if not isinstance(payload, dict):
                            payload = {}
                        structured = self._http_status_error(
                            response=response,
                            payload=payload,
                            operation=operation,
                            model=active_model,
                            message_count=len(messages),
                            attempt_number=attempt_number,
                            max_attempts=max_attempts,
                        )
                        self._logger.warning(
                            "provider.call.failed",
                            provider=self.provider_name,
                            model=active_model,
                            operation=operation,
                            code=structured.code,
                            attempt=attempt_number,
                            max_attempts=max_attempts,
                            details=structured.details,
                        )
                        await self._retry_or_raise(
                            structured,
                            attempt_number=attempt_number,
                            max_attempts=max_attempts,
                        )
                        continue
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line.removeprefix("data: ").strip()
                        if not data:
                            continue
                        if data == "[DONE]":
                            break
                        try:
                            payload = cast(dict[str, Any], json.loads(data))
                        except json.JSONDecodeError as exc:
                            structured = self._protocol_error(
                                message="LLM provider stream returned invalid JSON event",
                                code="provider.stream.invalid_json_event",
                                operation=operation,
                                model=active_model,
                                message_count=len(messages),
                                attempt_number=attempt_number,
                                max_attempts=max_attempts,
                                retryable=not content_parts and not tool_call_chunks,
                                exc=exc,
                                details={"event_fragment": data[:500]},
                            )
                            raise structured from exc
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
                tool_calls = _merge_tool_call_chunks(tool_call_chunks)
                content = "".join(content_parts)
                if not tool_calls and not content.strip():
                    structured = self._protocol_error(
                        message="LLM provider stream returned no content or tool calls",
                        code="provider.stream.empty_completion",
                        operation=operation,
                        model=resolved_model,
                        message_count=len(messages),
                        attempt_number=attempt_number,
                        max_attempts=max_attempts,
                    )
                    await self._retry_or_raise(
                        structured,
                        attempt_number=attempt_number,
                        max_attempts=max_attempts,
                    )
                    continue
                self._logger.info(
                    "provider.call.completed",
                    provider=self.provider_name,
                    model=resolved_model,
                    message_count=len(messages),
                    attempt=attempt_number,
                    max_attempts=max_attempts,
                )
                return ToolCallCompletionResult(
                    provider=self.provider_name,
                    model=resolved_model,
                    content=None if tool_calls else content,
                    tool_calls=tool_calls,
                )
            except httpx.HTTPError as exc:
                structured = self._transport_error(
                    exc=exc,
                    operation=operation,
                    model=active_model,
                    message_count=len(messages),
                    attempt_number=attempt_number,
                    max_attempts=max_attempts,
                )
                self._logger.exception(
                    "provider.call.failed",
                    provider=self.provider_name,
                    model=active_model,
                    message_count=len(messages),
                    operation=operation,
                    code=structured.code,
                    attempt=attempt_number,
                    max_attempts=max_attempts,
                )
                await self._retry_or_raise(
                    structured,
                    attempt_number=attempt_number,
                    max_attempts=max_attempts,
                )
                continue
            except AppError as exc:
                await self._retry_or_raise(
                    exc,
                    attempt_number=attempt_number,
                    max_attempts=max_attempts,
                )
                continue
        raise self._protocol_error(
            message="LLM provider retry loop exhausted without terminal state",
            code="provider.retry_loop_exhausted",
            operation=operation,
            model=self._model_for_attempt(max_attempts),
            message_count=len(messages),
            attempt_number=max_attempts,
            max_attempts=max_attempts,
            retryable=False,
        )

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
