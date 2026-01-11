"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    version: str = "0.1.0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/hellosales",
        description="PostgreSQL connection URL with asyncpg driver",
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # Auth (WorkOS)
    workos_client_id: str = ""
    workos_api_key: str = ""
    workos_issuer: str = "https://api.workos.com"
    workos_audience: str = ""
    jwt_algorithm: str = "RS256"

    # AI Providers
    groq_api_key: str = ""
    google_api_key: str = ""
    default_llm_provider: Literal["groq", "google"] = "groq"
    default_llm_model: str = "llama-3.1-8b-instant"

    # Observability
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    otel_enabled: bool = False
    otlp_endpoint: str = ""  # OTLP collector endpoint (e.g., http://localhost:4317)
    otel_service_name: str = "hellosales-backend"
    prometheus_enabled: bool = True

    # Stageflow settings
    stage_timeout_ms: int = 30000
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_open_seconds: int = 60

    # Summary settings
    summary_enabled: bool = True
    summary_threshold: int = 8
    always_include_last_n: int = 6

    # Guardrails
    guardrails_enabled: bool = True

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.database_url.replace("postgresql+asyncpg", "postgresql")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
