"""Application configuration using pydantic-settings - Enterprise Edition (WorkOS only)."""

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("config")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Environment
    # ==========================================================================
    environment: Literal["development", "staging", "production"] = "development"

    # ==========================================================================
    # Database
    # ==========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://hellosales:hellosales_dev@localhost:5434/hellosales",
        description="PostgreSQL connection URL (async)",
    )
    database_disable_pooling: bool = Field(
        default=False,
        description=(
            "Disable SQLAlchemy connection pooling. "
            "Useful for tests that spawn multiple event loops (e.g., FastAPI TestClient)."
        ),
    )

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # ==========================================================================
    # WorkOS Authentication (Enterprise)
    # ==========================================================================
    workos_client_id: str = Field(
        default="",
        description="WorkOS client ID (used to derive JWKS URL)",
    )
    workos_api_key: str = Field(
        default="",
        description="WorkOS API key (server-side only)",
    )
    workos_issuer: str = Field(
        default="https://api.workos.com/",
        description="Expected issuer for WorkOS AuthKit tokens",
    )
    workos_audience: str = Field(
        default="",
        description="Optional WorkOS token audience (aud) to enforce",
    )

    # ==========================================================================
    # Provider API Keys
    # ==========================================================================
    groq_api_key: str = Field(
        default="",
        description="Groq API key for LLM",
    )
    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key for LLM",
    )
    openrouter_http_referer: str = Field(
        default="",
        description="OpenRouter HTTP Referer",
    )
    openrouter_x_title: str = Field(
        default="",
        description="OpenRouter X-Title",
    )
    deepgram_api_key: str = Field(
        default="",
        description="Deepgram API key for STT",
    )
    google_api_key: str = Field(
        default="",
        description="Google Cloud API key for TTS",
    )
    google_application_credentials: str = Field(
        default="",
        description="Google Cloud service account credentials (path or JSON)",
    )

    # ==========================================================================
    # STT Configuration
    # ==========================================================================
    stt_provider: Literal["deepgram", "deepgram_flux", "groq_whisper", "google", "stub"] = (
        "groq_whisper"
    )
    stt_model: str = "whisper-large-v3"

    tts_provider: Literal["google", "gemini_flash", "stub"] = Field(
        default="google",
        description="Text-to-speech provider backend (google, gemini_flash, or stub)",
    )

    # ==========================================================================
    # TTS pricing configuration (provider selection for cost estimation only)
    # ==========================================================================
    tts_pricing_model: Literal["google_neural2", "gemini_flash"] = Field(
        default="google_neural2",
        description=(
            "Which TTS pricing tier to use for cost estimation: "
            "'google_neural2' = Google Cloud TTS Neural2 pricing, "
            "'gemini_flash' = Gemini 2.5 Flash TTS pricing."
        ),
    )

    # ==========================================================================
    # Logging
    # ==========================================================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_debug_namespaces: str = Field(
        default="",
        description="Comma-separated list of namespaces to enable debug logging",
    )

    prometheus_metrics_enabled: bool = Field(
        default=True,
        description="Expose Prometheus /metrics endpoint",
    )

    provider_timeout_llm_seconds: int = Field(
        default=60,
        description="Timeout in seconds for non-streaming LLM calls (generate)",
    )
    provider_timeout_llm_stream_ttft_seconds: int = Field(
        default=20,
        description="Timeout in seconds to wait for first token from LLM stream (TTFT)",
    )
    provider_timeout_stt_seconds: int = Field(
        default=90,
        description="Timeout in seconds for STT transcribe calls",
    )
    provider_timeout_tts_seconds: int = Field(
        default=90,
        description="Timeout in seconds for TTS synthesize calls",
    )

    circuit_breaker_failure_threshold: int = Field(
        default=3,
        description="Failures within the window required to open the circuit (observe-only)",
    )
    circuit_breaker_failure_window_seconds: int = Field(
        default=60,
        description="Sliding time window (seconds) for circuit breaker failure counting",
    )
    circuit_breaker_open_seconds: int = Field(
        default=60,
        description="Seconds to keep breaker open before transitioning to half-open (observe-only)",
    )
    circuit_breaker_half_open_probe_count: int = Field(
        default=1,
        description="Successful probe calls in half-open required to close breaker (observe-only)",
    )
    circuit_breaker_observe_only: bool = Field(
        default=True,
        description="When true, circuit breaker tracks failures but doesn't block calls (observe-only mode)",
    )

    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_allow_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins",
    )
    cors_allow_origin_regex: str = Field(
        default="",
        description="Optional CORS allow_origin_regex (Python regex)",
    )

    # ==========================================================================
    # Enterprise App
    # ==========================================================================
    mobile_enterprise_origin: str = Field(
        default="http://localhost:8082",
        description="Origin URL for the enterprise mobile app (WorkOS)",
    )

    # ==========================================================================
    # Features / Flags
    # ==========================================================================
    assessment_enabled: bool = Field(
        default=False,
        description="Globally enable assessment engine (triage + assessment)",
    )
    pipeline_mode: Literal["fast", "accurate", "accurate_filler"] = Field(
        default="fast",
        description=(
            "Voice pipeline mode: "
            "'fast' = triage/assess runs in background (no latency impact), "
            "'accurate' = wait for triage+assess before LLM (assessment in context), "
            "'accurate_filler' = same as accurate but plays filler audio while waiting"
        ),
    )

    context_enricher_meta_summary_enabled: bool = Field(
        default=True,
        description="Enable meta summary enrichment during context build",
    )
    context_enricher_summary_enabled: bool = Field(
        default=True,
        description="Enable session summary enrichment during context build",
    )
    context_enricher_profile_enabled: bool = Field(
        default=True,
        description="Enable profile enrichment during context build",
    )
    context_enricher_skills_enabled: bool = Field(
        default=True,
        description="Enable skills enrichment during context build",
    )

    policy_gateway_enabled: bool = Field(
        default=True,
        description="Enable PolicyGateway checks (A1 safety foundations)",
    )
    policy_allowlist_enabled: bool = Field(
        default=True,
        description="Enable deterministic allowlists by intent at policy checkpoints",
    )
    policy_allowlist_pre_llm: str = Field(
        default="chat,voice",
        description="Comma-separated list of allowed intents at pre-LLM checkpoint",
    )
    policy_allowlist_pre_action: str = Field(
        default="chat,voice",
        description="Comma-separated list of allowed intents at pre-action checkpoint",
    )
    policy_allowlist_pre_persist: str = Field(
        default="chat,voice",
        description="Comma-separated list of allowed intents at pre-persist checkpoint",
    )

    policy_intent_rules_json: str = Field(
        default="",
        description=(
            "Optional JSON mapping of high-level intent -> escalation rules. "
            'Example: {"chat": {"action_types": [], "artifact_types": ["ui.chart"]}}'
        ),
    )
    policy_max_prompt_tokens: int | None = Field(
        default=None,
        description="Optional max estimated prompt tokens before LLM call (budget)",
    )
    policy_max_runs_per_minute: int | None = Field(
        default=None,
        description="Optional per-user quota: max pipeline runs per minute",
    )
    policy_llm_max_tokens: int | None = Field(
        default=None,
        description="Optional max_tokens passed to LLM providers",
    )

    policy_max_artifacts: int | None = Field(
        default=20,
        description="Optional max artifacts allowed in a single AgentOutput",
    )
    policy_max_artifact_payload_bytes: int | None = Field(
        default=50_000,
        description="Optional max JSON-serialized bytes allowed per artifact payload",
    )

    guardrails_enabled: bool = Field(
        default=True,
        description="Enable GuardrailsStage checks (A1 safety foundations)",
    )
    guardrails_force_checkpoint: Literal["pre_llm", "pre_action", "pre_persist"] | None = Field(
        default=None,
        description="Force a guardrails decision at the given checkpoint (testing only)",
    )
    guardrails_force_decision: Literal["allow", "block"] | None = Field(
        default=None,
        description="Force the guardrails decision (testing only)",
    )
    guardrails_force_reason: str = Field(
        default="forced",
        description="Reason string for forced guardrails decisions (testing only)",
    )
    policy_force_checkpoint: Literal["pre_llm", "pre_action", "pre_persist"] | None = Field(
        default=None,
        description="Force a policy decision at the given checkpoint (testing only)",
    )
    policy_force_decision: Literal["allow", "block", "require_approval"] | None = Field(
        default=None,
        description="Force the policy decision (testing only)",
    )
    policy_force_reason: str = Field(
        default="forced",
        description="Reason string for forced policy decisions (testing only)",
    )

    # Model choice for A/B testing (model1 vs model2)
    llm_model_choice: Literal["model1", "model2"] = Field(
        default="model1",
        description="Default LLM model choice for all operations (model1 or model2)",
    )

    llm_provider: Literal["groq", "gemini", "openrouter", "stub"] = "groq"

    summary_llm_provider: Literal["groq", "gemini", "openrouter", "stub"] = Field(
        default="groq",
        description="LLM provider to use for session summary generation",
    )
    summary_llm_model_id: str = Field(
        default="",
        description=(
            "Optional model ID override for session summary generation. "
            "If empty, uses llm_model_choice -> llm_model1_id/llm_model2_id."
        ),
    )

    meta_summary_llm_provider: Literal["groq", "gemini", "openrouter", "stub"] = Field(
        default="groq",
        description="LLM provider to use for meta summary merges",
    )
    meta_summary_llm_model_id: str = Field(
        default="",
        description=(
            "Optional model ID override for meta summary merges. "
            "If empty, uses llm_model_choice -> llm_model1_id/llm_model2_id."
        ),
    )
    llm_model1_id: str = Field(
        default="llama-3.1-8b-instant",
        description="Groq model ID for 'model1' (shown as 'Model 1' in UI)",
    )
    llm_model2_id: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model ID for 'model2' (shown as 'Model 2' in UI)",
    )
    triage_model_id: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model ID to use specifically for triage classification",
    )
    beta_mode_enabled: bool = Field(
        default=False,
        description=(
            "Beta mode: all skills are automatically tracked for assessment, "
            "and untracking is disabled."
        ),
    )
    chat_prompt_version: Literal["v1", "v2"] = Field(
        default="v1",
        description="System prompt variant for chat coach (v1 = classic, v2 = friend tone)",
    )

    # LLM fallback providers
    llm_backup_provider: Literal["gemini", "groq", "openrouter", "stub", ""] = Field(
        default="gemini",
        description=(
            "Backup LLM provider for chat/summary when primary fails (rate limit, etc.). "
            "Set to empty string to disable fallback."
        ),
    )
    assessment_backup_provider: Literal["gemini", "groq", "openrouter", "stub", ""] = Field(
        default="gemini",
        description=(
            "Backup LLM provider for assessment when primary fails (rate limit, parse error). "
            "Set to empty string to disable fallback."
        ),
    )

    # ==========================================================================
    # WebSocket
    # ==========================================================================
    ws_ping_interval: int = Field(
        default=30,
        description="WebSocket ping interval in seconds",
    )
    ws_ping_timeout: int = Field(
        default=60,
        description="WebSocket ping timeout in seconds",
    )

    legal_version: str = Field(
        default="2025-12-14",
        description=(
            "Current legal document bundle version identifier used for "
            "terms/privacy acceptance tracking"
        ),
    )
    terms_url: str = Field(
        default="",
        description="Public URL to the Terms of Service document",
    )
    privacy_url: str = Field(
        default="",
        description="Public URL to the Privacy Policy document",
    )
    dpa_url: str = Field(
        default="",
        description="Public URL to the Data Processing Agreement document",
    )

    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @computed_field
    @property
    def debug_namespaces(self) -> list[str]:
        """Parse debug namespaces into a list."""
        if not self.log_debug_namespaces:
            return []
        return [ns.strip() for ns in self.log_debug_namespaces.split(",") if ns.strip()]

    @computed_field
    @property
    def cors_allow_origins_list(self) -> list[str]:
        """Parse cors_allow_origins into a list."""
        if not self.cors_allow_origins:
            return []
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    def log_config_summary(self) -> None:
        """Log a summary of the configuration (redacting secrets)."""
        logger.info(
            "Enterprise configuration loaded",
            extra={
                "service": "config",
                "environment": self.environment,
                "database": self._redact_url(self.database_url),
                "redis": self._redact_url(self.redis_url),
                "workos_configured": bool(self.workos_client_id) and bool(self.workos_api_key),
                "groq_configured": bool(self.groq_api_key),
                "openrouter_configured": bool(self.openrouter_api_key),
                "deepgram_configured": bool(self.deepgram_api_key),
                "google_api_key_configured": bool(self.google_api_key),
                "google_credentials_configured": bool(self.google_application_credentials),
                "log_level": self.log_level,
                "debug_namespaces": self.debug_namespaces,
                "assessment_enabled": self.assessment_enabled,
                "pipeline_mode": self.pipeline_mode,
                "llm_model_choice": self.llm_model_choice,
                "llm_provider": self.llm_provider,
                "llm_model1_id": self.llm_model1_id,
                "llm_model2_id": self.llm_model2_id,
                "triage_model_id": self.triage_model_id,
                "beta_mode_enabled": self.beta_mode_enabled,
                "llm_backup_provider": self.llm_backup_provider,
                "assessment_backup_provider": self.assessment_backup_provider,
            },
        )

    @staticmethod
    def _redact_url(url: str) -> str:
        """Redact password from database URL."""
        if "@" in url and "://" in url:
            protocol_end = url.index("://") + 3
            at_pos = url.index("@")
            return url[:protocol_end] + "***:***" + url[at_pos:]
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    return settings
