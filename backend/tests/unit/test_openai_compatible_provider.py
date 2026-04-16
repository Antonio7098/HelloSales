from __future__ import annotations

import httpx
import pytest

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
