from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from hello_sales_backend.modules.web_search.use_cases.commands import SearchWebCommand
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.web_search.contracts import (
    WebSearchCallContext,
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResult,
)
from hello_sales_backend.platform.web_search.providers import (
    NoopWebSearchProvider,
    TavilyWebSearchProvider,
)
from hello_sales_backend.shared.errors import AppError


class FakeWebSearchProvider:
    provider_name = "fake-search"

    def __init__(self) -> None:
        self.context: WebSearchCallContext | None = None
        self.request: WebSearchRequest | None = None

    async def search(
        self,
        request: WebSearchRequest,
        *,
        context: WebSearchCallContext | None = None,
    ) -> WebSearchResponse:
        self.request = request
        self.context = context
        return WebSearchResponse(
            provider=self.provider_name,
            query=request.query,
            provider_request_id="provider-request-1",
            results=[
                WebSearchResult(
                    title="Example",
                    url="https://example.com",
                    snippet="Example snippet",
                    source_provider=self.provider_name,
                    provider_request_id="provider-request-1",
                )
            ],
        )

    def is_configured(self) -> bool:
        return True


def test_settings_reject_unknown_web_search_provider() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+aiosqlite:///test.db", web_search_provider="unknown")


@pytest.mark.asyncio
async def test_noop_web_search_provider_reports_disabled_state() -> None:
    provider = NoopWebSearchProvider()

    with pytest.raises(AppError) as exc_info:
        await provider.search(WebSearchRequest(query="latest crm news", reason="Need current public info"))

    assert exc_info.value.code == "provider.web_search.not_configured"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_web_search_service_preserves_context_and_returns_sources() -> None:
    provider = FakeWebSearchProvider()
    service = WebSearchService(provider=provider, default_max_results=4)

    result = await service.search(
        request_id="request-1",
        trace_id="trace-1",
        actor_id="actor-1",
        command=SearchWebCommand(query="latest sales tools", reason="Need current public info"),
    )

    assert provider.request is not None
    assert provider.request.max_results == 4
    assert provider.context is not None
    assert provider.context.request_id == "request-1"
    assert provider.context.trace_id == "trace-1"
    assert result.provider == "fake-search"
    assert result.sources[0].url == "https://example.com"


@pytest.mark.asyncio
async def test_tavily_adapter_normalizes_success_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "api_key" in request.read().decode()
        return httpx.Response(
            200,
            headers={"x-request-id": "provider-request-2"},
            json={
                "query": "hello sales",
                "response_time": 0.12,
                "results": [
                    {
                        "title": "Hello Sales",
                        "url": "https://example.com/sales",
                        "content": "Search snippet",
                        "raw_content": "Long content",
                        "score": 0.91,
                        "published_date": "2026-04-20",
                    }
                ],
            },
        )

    provider = TavilyWebSearchProvider(
        api_key="secret",
        timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    result = await provider.search(WebSearchRequest(query="hello sales", reason="Need source"))

    assert result.provider == "tavily"
    assert result.provider_request_id == "provider-request-2"
    assert result.results[0].title == "Hello Sales"
    assert result.results[0].snippet == "Search snippet"
    await provider.aclose()


@pytest.mark.asyncio
async def test_tavily_adapter_maps_rate_limit() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(429, json={"error": "rate limit"})

    provider = TavilyWebSearchProvider(
        api_key="secret",
        timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(AppError) as exc_info:
        await provider.search(WebSearchRequest(query="hello sales", reason="Need source"))

    assert exc_info.value.code == "provider.web_search.rate_limit"
    assert exc_info.value.retryable is True
    await provider.aclose()


@pytest.mark.asyncio
async def test_tavily_adapter_maps_bad_request_with_provider_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            400,
            headers={"x-request-id": "provider-request-bad"},
            json={"error": "Invalid search_depth", "detail": "search_depth must be basic or advanced"},
        )

    provider = TavilyWebSearchProvider(
        api_key="secret",
        timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(AppError) as exc_info:
        await provider.search(WebSearchRequest(query="hello sales", reason="Need source"))

    assert exc_info.value.code == "provider.web_search.bad_request"
    assert exc_info.value.retryable is False
    assert exc_info.value.status_code == 400
    assert exc_info.value.details["provider_request_id"] == "provider-request-bad"
    assert exc_info.value.details["provider_response"] == {
        "error": "Invalid search_depth",
        "detail": "search_depth must be basic or advanced",
    }
    await provider.aclose()


@pytest.mark.asyncio
async def test_tavily_adapter_maps_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.TimeoutException("Request timed out")

    provider = TavilyWebSearchProvider(
        api_key="secret",
        timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(AppError) as exc_info:
        await provider.search(WebSearchRequest(query="hello sales", reason="Need source"))

    assert exc_info.value.code == "provider.web_search.timeout"
    assert exc_info.value.retryable is True
    assert exc_info.value.status_code == 502
    await provider.aclose()


@pytest.mark.asyncio
async def test_tavily_adapter_maps_authentication_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = TavilyWebSearchProvider(
        api_key="secret",
        timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(AppError) as exc_info:
        await provider.search(WebSearchRequest(query="hello sales", reason="Need source"))

    assert exc_info.value.code == "provider.web_search.authentication_failed"
    assert exc_info.value.retryable is False
    assert exc_info.value.status_code == 401
    await provider.aclose()


@pytest.mark.asyncio
async def test_tavily_adapter_maps_remote_5xx() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(503, json={"error": "service unavailable"})

    provider = TavilyWebSearchProvider(
        api_key="secret",
        timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(AppError) as exc_info:
        await provider.search(WebSearchRequest(query="hello sales", reason="Need source"))

    assert exc_info.value.code == "provider.web_search.remote_5xx"
    assert exc_info.value.retryable is True
    assert exc_info.value.status_code == 503
    await provider.aclose()


@pytest.mark.asyncio
async def test_tavily_adapter_maps_malformed_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, text="not-json")

    provider = TavilyWebSearchProvider(
        api_key="secret",
        timeout_seconds=1,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(AppError) as exc_info:
        await provider.search(WebSearchRequest(query="hello sales", reason="Need source"))

    assert exc_info.value.code == "provider.web_search.malformed_response"
    assert exc_info.value.retryable is False
    assert exc_info.value.status_code == 502
    await provider.aclose()
