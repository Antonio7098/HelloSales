from __future__ import annotations

from hello_sales_backend.platform.composition.providers import build_provider_registry
from hello_sales_backend.platform.config.settings import Settings


def test_provider_registry_builds_groq_adapter_from_generic_agent_env_contract() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        generic_agent_provider="groq",
        generic_agent_model="openai/gpt-oss-20b",
        groq_api_key="groq-secret",
    )

    registry = build_provider_registry(settings=settings)

    assert registry.llm.provider_name == "groq"
    assert registry.llm.is_configured() is True


def test_provider_registry_builds_tavily_adapter_from_settings() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        web_search_provider="tavily",
        tavily_api_key="tavily-secret",
    )

    registry = build_provider_registry(settings=settings)

    assert registry.web_search.provider_name == "tavily"
    assert registry.web_search.is_configured() is True
    diagnostics = {item.kind: item for item in registry.diagnostics()}
    assert diagnostics["web_search"].available is True
