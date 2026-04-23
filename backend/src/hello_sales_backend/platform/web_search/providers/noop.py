"""No-op web-search provider used when search is disabled."""

from __future__ import annotations

from hello_sales_backend.platform.web_search.contracts import (
    WebSearchCallContext,
    WebSearchProviderPort,
    WebSearchRequest,
    WebSearchResponse,
)
from hello_sales_backend.shared.errors import app_error


class NoopWebSearchProvider(WebSearchProviderPort):
    """Placeholder provider for environments without web-search credentials."""

    provider_name = "noop"

    async def search(
        self,
        request: WebSearchRequest,
        *,
        context: WebSearchCallContext | None = None,
    ) -> WebSearchResponse:
        raise app_error(
            "No web search provider is configured for this environment",
            code="provider.web_search.not_configured",
            category="provider",
            status_code=503,
            retryable=False,
            details={
                "provider": self.provider_name,
                "query_length": len(request.query),
                "operation": context.operation if context else None,
            },
            operation="provider.web_search.search",
            component="provider",
        )

    def is_configured(self) -> bool:
        return False
