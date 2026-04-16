"""Application settings."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration."""

    PROVIDER_BASE_URLS: ClassVar[dict[str, str]] = {
        "groq": "https://api.groq.com/openai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "openai": "https://api.openai.com/v1",
        "openai-compatible": "",
    }

    model_config = SettingsConfigDict(
        env_prefix="HELLO_SALES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "HelloSales API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://hello_sales:hello_sales@localhost:5432/hello_sales"
    cors_allowed_origins: tuple[str, ...] = ("http://localhost:3000", "http://localhost:5173")
    stageflow_required: bool = False
    stageflow_event_queue_size: int = Field(default=500, ge=1)
    generic_agent_provider: str = Field(default="", validation_alias="GENERIC_AGENT_PROVIDER")
    generic_agent_model: str = Field(default="", validation_alias="GENERIC_AGENT_MODEL")
    generic_agent_base_url: str = Field(default="", validation_alias="GENERIC_AGENT_BASE_URL")
    generic_agent_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias="GENERIC_AGENT_TIMEOUT_SECONDS",
    )
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")

    @field_validator(
        "app_name",
        "app_version",
        "environment",
        "api_prefix",
        "log_level",
        "database_url",
        "generic_agent_provider",
        "generic_agent_model",
        "generic_agent_base_url",
        "groq_api_key",
        "openrouter_api_key",
        "openai_api_key",
        mode="before",
    )
    @classmethod
    def strip_string_values(cls, value: object) -> object:
        """Normalize string settings aggressively to avoid hidden whitespace bugs."""

        if isinstance(value, str):
            return value.strip()
        return value

    @property
    def resolved_generic_agent_provider(self) -> str:
        """Return the effective provider name for generic-agent model calls."""

        return self.generic_agent_provider

    @property
    def resolved_generic_agent_model(self) -> str:
        """Return the effective model name for generic-agent model calls."""

        return self.generic_agent_model

    @property
    def resolved_generic_agent_base_url(self) -> str:
        """Return the effective base URL for the configured provider."""

        if self.generic_agent_provider == "openai-compatible":
            return self.generic_agent_base_url
        if self.generic_agent_base_url:
            return self.generic_agent_base_url
        return self.PROVIDER_BASE_URLS.get(self.generic_agent_provider, "")

    @property
    def resolved_generic_agent_api_key(self) -> str:
        """Return the effective API key for the configured provider."""

        provider = self.resolved_generic_agent_provider
        if provider == "groq":
            return self.groq_api_key
        if provider == "openrouter":
            return self.openrouter_api_key
        if provider == "openai":
            return self.openai_api_key
        return ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""

    return Settings()
