"""Web-search provider adapters."""

from hello_sales_backend.platform.web_search.providers.noop import NoopWebSearchProvider
from hello_sales_backend.platform.web_search.providers.tavily import TavilyWebSearchProvider

__all__ = ["NoopWebSearchProvider", "TavilyWebSearchProvider"]
