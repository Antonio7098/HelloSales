from __future__ import annotations

from hello_sales_backend.platform.config.settings import Settings


def test_generic_agent_groq_settings_resolve_to_groq_runtime_config() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        generic_agent_provider="groq",
        generic_agent_model="openai/gpt-oss-20b",
        groq_api_key="groq-secret",
    )

    assert settings.resolved_generic_agent_provider == "groq"
    assert settings.resolved_generic_agent_model == "openai/gpt-oss-20b"
    assert settings.resolved_generic_agent_api_key == "groq-secret"
    assert settings.resolved_generic_agent_base_url == "https://api.groq.com/openai/v1"


def test_openai_compatible_provider_requires_generic_agent_base_url() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        generic_agent_provider="openai-compatible",
        generic_agent_base_url="https://example.test/v1",
        generic_agent_model="legacy-model",
    )

    assert settings.resolved_generic_agent_provider == "openai-compatible"
    assert settings.resolved_generic_agent_model == "legacy-model"
    assert settings.resolved_generic_agent_base_url == "https://example.test/v1"


def test_generic_agent_provider_retry_settings_are_explicit() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///test.db",
        generic_agent_provider_max_retries=3,
        generic_agent_provider_retry_backoff_seconds=0.5,
        generic_agent_backup_model="backup-model",
        generic_agent_backup_model_attempt=2,
    )

    assert settings.generic_agent_provider_max_retries == 3
    assert settings.generic_agent_provider_retry_backoff_seconds == 0.5
    assert settings.generic_agent_backup_model == "backup-model"
    assert settings.generic_agent_backup_model_attempt == 2
