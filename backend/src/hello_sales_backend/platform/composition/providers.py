"""Provider assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.llm.contracts import LLMProviderPort
from hello_sales_backend.platform.llm.providers import NoopLLMProvider, OpenAICompatibleLLMProvider
from hello_sales_backend.platform.web_search.contracts import WebSearchProviderPort
from hello_sales_backend.platform.web_search.providers import (
    NoopWebSearchProvider,
    TavilyWebSearchProvider,
)


@dataclass(slots=True, frozen=True)
class ProviderStatus:
    """Provider diagnostics summary."""

    name: str
    available: bool
    kind: str = "provider"
    required: bool = False
    degraded: bool = False


@dataclass(slots=True)
class ProviderRegistry:
    """Shared provider registry."""

    llm: LLMProviderPort
    web_search: WebSearchProviderPort
    web_search_required: bool = False

    def diagnostics(self) -> list[ProviderStatus]:
        return [
            ProviderStatus(name=self.llm.provider_name, kind="llm", available=self.llm.is_configured()),
            ProviderStatus(
                name=self.web_search.provider_name,
                kind="web_search",
                available=self.web_search.is_configured(),
                required=self.web_search_required,
                degraded=self.web_search_required and not self.web_search.is_configured(),
            ),
        ]

    async def aclose(self) -> None:
        for provider in (self.llm, self.web_search):
            close = getattr(provider, "aclose", None)
            if callable(close):
                await close()


def build_provider_registry(
    *,
    settings: Settings | None = None,
    llm_provider: LLMProviderPort | None = None,
    web_search_provider: WebSearchProviderPort | None = None,
) -> ProviderRegistry:
    """Build the shared provider registry."""

    resolved_llm_provider: LLMProviderPort
    if settings is not None and settings.resolved_generic_agent_api_key:
        resolved_llm_provider = OpenAICompatibleLLMProvider(
            provider_name=settings.resolved_generic_agent_provider,
            base_url=settings.resolved_generic_agent_base_url,
            api_key=settings.resolved_generic_agent_api_key,
            model=settings.resolved_generic_agent_model,
            timeout_seconds=settings.generic_agent_timeout_seconds,
        )
    else:
        resolved_llm_provider = NoopLLMProvider()
    if llm_provider is not None:
        resolved_llm_provider = llm_provider

    resolved_web_search_provider: WebSearchProviderPort = NoopWebSearchProvider()
    if (
        settings is not None
        and settings.resolved_web_search_provider == "tavily"
        and settings.resolved_web_search_api_key
    ):
        resolved_web_search_provider = TavilyWebSearchProvider(
            api_key=settings.resolved_web_search_api_key,
            timeout_seconds=settings.web_search_timeout_seconds,
        )
    if web_search_provider is not None:
        resolved_web_search_provider = web_search_provider
    return ProviderRegistry(
        llm=resolved_llm_provider,
        web_search=resolved_web_search_provider,
        web_search_required=settings.web_search_required if settings is not None else False,
    )
