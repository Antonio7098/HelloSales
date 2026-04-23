from __future__ import annotations

from collections.abc import Awaitable
from typing import cast

import pytest

from hello_sales_backend.application.tools.web_search import build_search_web_tool
from hello_sales_backend.modules.web_search.use_cases.commands import SearchWebCommand
from hello_sales_backend.modules.web_search.use_cases.views import (
    WebSearchResultView,
    WebSearchSourceView,
)
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService
from hello_sales_backend.platform.agents.tools import AgentToolExecutionContext
from hello_sales_backend.shared.errors import AppError, app_error


class FlakyWebSearchService:
    """Fake service that can fail before returning one source."""

    def __init__(self, failures: list[AppError]) -> None:
        self.failures = list(failures)
        self.calls: list[SearchWebCommand] = []

    async def search(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: SearchWebCommand,
    ) -> WebSearchResultView:
        del request_id, trace_id, actor_id
        self.calls.append(command)
        if self.failures:
            raise self.failures.pop(0)
        return WebSearchResultView(
            provider="fake-search",
            query=command.query,
            sources=[
                WebSearchSourceView(
                    title="Example",
                    url="https://example.com",
                    snippet="Example snippet",
                    source_provider="fake-search",
                )
            ],
        )


def _context() -> AgentToolExecutionContext:
    return AgentToolExecutionContext(request_id="request-1", trace_id="trace-1", actor_id="actor-1")


@pytest.mark.asyncio
async def test_search_web_tool_retries_retryable_error_then_succeeds() -> None:
    service = FlakyWebSearchService(
        failures=[
            app_error(
                "Temporary provider failure",
                code="provider.web_search.remote_5xx",
                category="provider",
                status_code=503,
                retryable=True,
            )
        ]
    )
    tool = build_search_web_tool(
        web_search_service=cast(WebSearchService, service),
        requires_approval=False,
    )

    result = await cast(
        Awaitable[dict[str, object]],
        tool.execute(
            {
                "query": "latest crm news",
                "reason": "Need current public information",
            },
            _context(),
        ),
    )

    assert len(service.calls) == 2
    assert result["provider"] == "fake-search"
    sources = result["sources"]
    assert isinstance(sources, list)
    assert isinstance(sources[0], dict)
    assert sources[0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_search_web_tool_does_not_retry_non_retryable_error() -> None:
    service = FlakyWebSearchService(
        failures=[
            app_error(
                "Bad provider request",
                code="provider.web_search.bad_request",
                category="provider",
                status_code=400,
                retryable=False,
            )
        ]
    )
    tool = build_search_web_tool(
        web_search_service=cast(WebSearchService, service),
        requires_approval=False,
    )

    with pytest.raises(AppError) as exc_info:
        await cast(
            Awaitable[dict[str, object]],
            tool.execute(
                {
                    "query": "latest crm news",
                    "reason": "Need current public information",
                },
                _context(),
            ),
        )

    assert len(service.calls) == 1
    assert exc_info.value.code == "provider.web_search.bad_request"
