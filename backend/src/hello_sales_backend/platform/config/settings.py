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
    SUPPORTED_OBSERVABILITY_METRICS_EXPORTERS: ClassVar[set[str]] = {"prometheus"}
    SUPPORTED_OBSERVABILITY_TRACING_EXPORTERS: ClassVar[set[str]] = {"console", "none", "otlp"}

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
    observability_service_name: str = ""
    observability_service_version: str = ""
    observability_metrics_enabled: bool = False
    observability_metrics_exporter: str = "prometheus"
    observability_metrics_endpoint_enabled: bool = False
    observability_metrics_endpoint_path: str = "/metrics"
    observability_metrics_http_enabled: bool = True
    observability_metrics_health_enabled: bool = True
    observability_metrics_background_tasks_enabled: bool = True
    observability_metrics_agents_enabled: bool = True
    observability_metrics_workers_enabled: bool = True
    observability_tracing_enabled: bool = False
    observability_tracing_exporter: str = "console"
    observability_tracing_otlp_endpoint: str = ""
    observability_tracing_otlp_headers: str = ""
    observability_tracing_otlp_timeout_seconds: float = Field(default=10.0, gt=0)
    observability_tracing_http_enabled: bool = True
    observability_tracing_background_tasks_enabled: bool = True
    observability_tracing_agents_enabled: bool = True
    observability_tracing_workers_enabled: bool = True
    generic_agent_provider: str = ""
    generic_agent_model: str = ""
    generic_agent_base_url: str = ""
    generic_agent_timeout_seconds: float = Field(default=30.0, gt=0)
    analytics_query_catalog_dir: str = "backend/catalogs/analytics"
    analytics_query_statement_timeout_ms: int = Field(default=5000, ge=100, le=60000)
    analytics_query_default_max_rows: int = Field(default=25, ge=1, le=200)
    analytics_query_max_cell_length: int = Field(default=200, ge=32, le=4000)
    session_summary_turn_interval: int = Field(default=8, ge=1)
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    openai_api_key: str = ""

    @field_validator(
        "app_name",
        "app_version",
        "environment",
        "api_prefix",
        "log_level",
        "database_url",
        "observability_service_name",
        "observability_service_version",
        "observability_metrics_exporter",
        "observability_metrics_endpoint_path",
        "observability_tracing_exporter",
        "observability_tracing_otlp_endpoint",
        "observability_tracing_otlp_headers",
        "generic_agent_provider",
        "generic_agent_model",
        "generic_agent_base_url",
        "analytics_query_catalog_dir",
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

    @field_validator("observability_metrics_endpoint_path")
    @classmethod
    def validate_metrics_endpoint_path(cls, value: str) -> str:
        """Ensure the operational metrics path is rooted at the app."""

        if not value.startswith("/"):
            raise ValueError("observability_metrics_endpoint_path must start with '/'")
        return value

    @field_validator("observability_metrics_exporter")
    @classmethod
    def validate_metrics_exporter(cls, value: str) -> str:
        """Restrict metrics exporters to the supported scaffold-stage set."""

        if value not in cls.SUPPORTED_OBSERVABILITY_METRICS_EXPORTERS:
            supported = ", ".join(sorted(cls.SUPPORTED_OBSERVABILITY_METRICS_EXPORTERS))
            raise ValueError(f"observability_metrics_exporter must be one of: {supported}")
        return value

    @field_validator("observability_tracing_exporter")
    @classmethod
    def validate_tracing_exporter(cls, value: str) -> str:
        """Restrict tracing exporters to the supported scaffold-stage set."""

        if value not in cls.SUPPORTED_OBSERVABILITY_TRACING_EXPORTERS:
            supported = ", ".join(sorted(cls.SUPPORTED_OBSERVABILITY_TRACING_EXPORTERS))
            raise ValueError(f"observability_tracing_exporter must be one of: {supported}")
        return value

    @field_validator("observability_tracing_otlp_endpoint")
    @classmethod
    def validate_tracing_otlp_endpoint(cls, value: str) -> str:
        """Allow empty OTLP endpoint but validate configured values."""

        if not value:
            return value
        if value.startswith(("http://", "https://")):
            return value
        raise ValueError("observability_tracing_otlp_endpoint must start with 'http://' or 'https://'")

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

    @property
    def resolved_observability_service_name(self) -> str:
        """Return the effective service name used for telemetry resources."""

        return self.observability_service_name or self.app_name

    @property
    def resolved_observability_service_version(self) -> str:
        """Return the effective service version used for telemetry resources."""

        return self.observability_service_version or self.app_version

    @property
    def resolved_observability_tracing_otlp_headers(self) -> dict[str, str]:
        """Parse OTLP headers from a comma-separated key=value string."""

        if not self.observability_tracing_otlp_headers:
            return {}
        headers: dict[str, str] = {}
        for item in self.observability_tracing_otlp_headers.split(","):
            key, separator, value = item.partition("=")
            normalized_key = key.strip()
            normalized_value = value.strip()
            if separator != "=" or not normalized_key or not normalized_value:
                raise ValueError(
                    "observability_tracing_otlp_headers must be a comma-separated list of key=value pairs"
                )
            headers[normalized_key] = normalized_value
        return headers


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""

    return Settings()
