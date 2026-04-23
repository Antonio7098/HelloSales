"""Application-owned web-search service primitive."""

from __future__ import annotations

from hello_sales_backend.modules.web_search.use_cases.commands import SearchWebCommand
from hello_sales_backend.modules.web_search.use_cases.views import (
    WebSearchResultView,
    WebSearchSourceView,
)
from hello_sales_backend.platform.web_search.contracts import (
    WebSearchCallContext,
    WebSearchProviderPort,
    WebSearchRequest,
)


class WebSearchService:
    """Validate and execute public web search through a neutral provider port."""

    def __init__(
        self,
        *,
        provider: WebSearchProviderPort,
        default_max_results: int,
    ) -> None:
        self._provider = provider
        self._default_max_results = default_max_results

    async def search(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        actor_id: str | None,
        command: SearchWebCommand,
    ) -> WebSearchResultView:
        max_results = command.max_results or self._default_max_results
        provider_response = await self._provider.search(
            WebSearchRequest(
                query=command.query,
                reason=command.reason,
                max_results=max_results,
                search_depth=command.search_depth,
                topic=command.topic,
                time_range=command.time_range,
                include_domains=command.include_domains,
                exclude_domains=command.exclude_domains,
                country=command.country,
                include_raw_content=command.include_raw_content,
            ),
            context=WebSearchCallContext(
                request_id=request_id,
                trace_id=trace_id,
                actor_id=actor_id,
                operation="web_search.search",
            ),
        )
        return WebSearchResultView(
            provider=provider_response.provider,
            query=provider_response.query,
            provider_request_id=provider_response.provider_request_id,
            sources=[
                WebSearchSourceView(
                    title=item.title,
                    url=item.url,
                    snippet=item.snippet,
                    content=item.content,
                    published_at=item.published_at,
                    score=item.score,
                    source_provider=item.source_provider,
                    provider_request_id=item.provider_request_id,
                    metadata=item.raw_metadata,
                )
                for item in provider_response.results
            ],
            metadata={
                **provider_response.raw_metadata,
                "answer_available": provider_response.answer is not None,
            },
        )
