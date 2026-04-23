from __future__ import annotations

import httpx
import pytest

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.agents.tools import AgentToolExecutionContext
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.web_search.contracts import (
    WebSearchCallContext,
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResult,
)


class FakeWebSearchProvider:
    provider_name = "fake-search"

    async def search(
        self,
        request: WebSearchRequest,
        *,
        context: WebSearchCallContext | None = None,
    ) -> WebSearchResponse:
        del context
        return WebSearchResponse(
            provider=self.provider_name,
            query=request.query,
            results=[
                WebSearchResult(
                    title="Current result",
                    url="https://example.com/current",
                    snippet="A current public result",
                    source_provider=self.provider_name,
                )
            ],
        )

    def is_configured(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_web_search_tool_is_registered_and_executes_through_catalog(tmp_path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        web_search_requires_approval=True,
    )
    app = create_app(settings, overrides=AppOverrides(web_search_provider=FakeWebSearchProvider()))
    catalog = app.state.container.agent_runtime.agents.require("generic").tools
    tool = catalog.require("search_web")

    result = await catalog.execute(
        name="search_web",
        arguments={
            "query": "latest CRM platform news",
            "reason": "Need current public information",
            "max_results": 2,
        },
        context=AgentToolExecutionContext(
            request_id="request-1",
            trace_id="trace-1",
            actor_id="actor-1",
        ),
    )

    assert tool.requires_approval is True
    assert result["provider"] == "fake-search"
    assert result["sources"][0]["url"] == "https://example.com/current"


@pytest.mark.asyncio
async def test_system_diagnostics_include_web_search_provider(tmp_path) -> None:
    settings = Settings(
        environment="test",
        api_prefix="/api",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
    )
    app = create_app(settings, overrides=AppOverrides(web_search_provider=FakeWebSearchProvider()))

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/system/diagnostics")

    response.raise_for_status()
    providers = response.json()["data"]["providers"]
    web_search = next(item for item in providers if item["kind"] == "web_search")
    assert web_search["name"] == "fake-search"
    assert web_search["available"] is True
