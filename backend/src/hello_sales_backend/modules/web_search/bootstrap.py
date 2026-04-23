"""Web-search module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.web_search.contracts import WebSearchProviderPort


@dataclass(slots=True)
class WebSearchModule:
    """Resolved web-search module bundle."""

    service: WebSearchService


def build_web_search_module(
    *,
    settings: Settings,
    provider: WebSearchProviderPort,
) -> WebSearchModule:
    """Build the web-search module."""

    return WebSearchModule(
        service=WebSearchService(
            provider=provider,
            default_max_results=settings.web_search_default_max_results,
        )
    )
