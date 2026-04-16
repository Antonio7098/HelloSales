"""Provider assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.providers.llm.contracts import ChatModelPort
from hello_sales_backend.platform.providers.llm.noop import NoopChatModel
from hello_sales_backend.platform.providers.llm.openai_compatible import OpenAICompatibleChatModel


@dataclass(slots=True, frozen=True)
class ProviderStatus:
    """Provider diagnostics summary."""

    name: str
    available: bool


@dataclass(slots=True)
class ProviderRegistry:
    """Shared provider registry."""

    llm: ChatModelPort

    def diagnostics(self) -> list[ProviderStatus]:
        return [
            ProviderStatus(name=self.llm.provider_name, available=self.llm.is_configured()),
        ]

    async def aclose(self) -> None:
        close = getattr(self.llm, "aclose", None)
        if callable(close):
            await close()


def build_provider_registry(
    *,
    settings: Settings | None = None,
    llm_provider: ChatModelPort | None = None,
) -> ProviderRegistry:
    """Build the shared provider registry."""

    if llm_provider is not None:
        return ProviderRegistry(llm=llm_provider)
    if settings is not None and settings.resolved_generic_agent_api_key:
        return ProviderRegistry(
            llm=OpenAICompatibleChatModel(
                provider_name=settings.resolved_generic_agent_provider,
                base_url=settings.resolved_generic_agent_base_url,
                api_key=settings.resolved_generic_agent_api_key,
                model=settings.resolved_generic_agent_model,
                timeout_seconds=settings.generic_agent_timeout_seconds,
            )
        )
    return ProviderRegistry(llm=NoopChatModel())
