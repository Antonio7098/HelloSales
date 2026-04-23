from __future__ import annotations

import json

import httpx
import pytest

from hello_sales_backend.platform.llm import (
    JSONSchemaHint,
    ProviderToolDefinition,
)
from hello_sales_backend.platform.providers.llm import ChatMessage, OpenAICompatibleChatModel
from hello_sales_backend.shared.errors import AppError


async def test_openai_compatible_provider_parses_chat_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        payload = {
            "model": "test-model",
            "choices": [
                {
                    "message": {
                        "content": "OK",
                    }
                }
            ],
        }
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    result = await provider.generate([ChatMessage(role="user", content="hello")])

    assert result.provider == "test-provider"
    assert result.model == "test-model"
    assert result.output_text == "OK"
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_timeout_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    with pytest.raises(AppError) as exc_info:
        await provider.generate([ChatMessage(role="user", content="hello")])

    assert exc_info.value.code == "provider.timeout"
    assert exc_info.value.retryable is True
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_authentication_failures() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "unauthorized"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    with pytest.raises(AppError) as exc_info:
        await provider.generate([ChatMessage(role="user", content="hello")])

    assert exc_info.value.code == "provider.authentication_failed"
    assert exc_info.value.retryable is False
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_rate_limit_failures() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limit"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    with pytest.raises(AppError) as exc_info:
        await provider.generate([ChatMessage(role="user", content="hello")])

    assert exc_info.value.code == "provider.rate_limit"
    assert exc_info.value.retryable is True
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_remote_5xx_failures() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "unavailable"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    with pytest.raises(AppError) as exc_info:
        await provider.generate([ChatMessage(role="user", content="hello")])

    assert exc_info.value.code == "provider.remote_5xx"
    assert exc_info.value.retryable is True
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_requests_json_object_mode() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode()
        assert '"response_format":{"type":"json_object"}' in payload
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"message": {"content": '{"brief":"ok","key_points":["one"],"priority":"medium"}'}}],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    result = await provider.generate_json([ChatMessage(role="user", content="hello")])

    assert result.output_json == {"brief": "ok", "key_points": ["one"], "priority": "medium"}
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_uses_non_strict_json_schema_for_non_openai_providers() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode()
        assert '"type":"json_schema"' in payload
        assert '"strict":false' in payload
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"message": {"content": '{"brief":"ok","key_points":["one"],"priority":"medium"}'}}],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="groq",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    result = await provider.generate_json(
        [ChatMessage(role="user", content="hello")],
        schema_hint=JSONSchemaHint(
            name="structured_brief_result",
            schema={
                "type": "object",
                "properties": {"brief": {"type": "string"}},
                "required": ["brief"],
            },
        ),
    )

    assert result.output_json == {"brief": "ok", "key_points": ["one"], "priority": "medium"}
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_sends_native_tools_and_parses_tool_calls() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read().decode())
        assert payload["tools"] == [
            {
                "type": "function",
                "function": {
                    "name": "get_runtime_status",
                    "description": "Return runtime status.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            }
        ]
        assert payload["parallel_tool_calls"] is False
        return httpx.Response(
            200,
            text=(
                'data: {"model":"test-model","choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-1","type":"function","function":{"name":"get_runtime_status","arguments":"{"}}]}}]}\n\n'
                'data: {"model":"test-model","choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"}"}}]}}]}\n\n'
                "data: [DONE]\n\n"
            ),
            headers={"content-type": "text/event-stream"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )

    result = await provider.complete_with_tools(
        [{"role": "user", "content": "show runtime status"}],
        tools=[
            ProviderToolDefinition(
                name="get_runtime_status",
                description="Return runtime status.",
                parameters={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            )
        ],
    )

    assert result.content is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].call_id == "call-1"
    assert result.tool_calls[0].tool_name == "get_runtime_status"
    assert result.tool_calls[0].arguments == {}
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_compatible_provider_streams_text_deltas_to_callback() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                'data: {"model":"test-model","choices":[{"delta":{"content":"Hello"}}]}\n\n'
                'data: {"model":"test-model","choices":[{"delta":{"content":" world"}}]}\n\n'
                "data: [DONE]\n\n"
            ),
            headers={"content-type": "text/event-stream"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleChatModel(
        provider_name="test-provider",
        base_url="https://example.test/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=5.0,
        http_client=client,
    )
    deltas: list[str] = []

    result = await provider.complete_with_tools(
        [{"role": "user", "content": "hello"}],
        tools=[],
        on_text_delta=lambda delta: _record_delta(deltas, delta),
    )

    assert deltas == ["Hello", " world"]
    assert result.content == "Hello world"
    assert result.tool_calls == []
    await client.aclose()


async def _record_delta(buffer: list[str], delta: str) -> None:
    buffer.append(delta)
