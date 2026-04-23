"""Provider-neutral public web-search substrate."""

from hello_sales_backend.platform.web_search.contracts import (
    WebSearchCallContext,
    WebSearchProviderPort,
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResult,
)

__all__ = [
    "WebSearchCallContext",
    "WebSearchProviderPort",
    "WebSearchRequest",
    "WebSearchResponse",
    "WebSearchResult",
]
