"""Provider assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.platform.auth.contracts import AuthProviderPort
from hello_sales_backend.platform.auth.providers import (
    DevAuthProvider,
    NoopAuthProvider,
    WorkOSAuthProvider,
)
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.llm.contracts import LLMProviderPort
from hello_sales_backend.platform.llm.providers import NoopLLMProvider, OpenAICompatibleLLMProvider
from hello_sales_backend.platform.voice.contracts import (
    RealtimeVoiceProviderPort,
    STTProviderPort,
    TTSProviderPort,
    TurnDetectionPort,
)
from hello_sales_backend.platform.voice.providers import (
    FakeRealtimeVoiceProvider,
    FakeSTTProvider,
    FakeTTSProvider,
    FakeTurnDetectionProvider,
)
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

    auth: AuthProviderPort
    llm: LLMProviderPort
    web_search: WebSearchProviderPort
    voice_stt: STTProviderPort
    voice_tts: TTSProviderPort
    voice_realtime: RealtimeVoiceProviderPort
    voice_turn_detection: TurnDetectionPort
    auth_required: bool = False
    web_search_required: bool = False
    voice_required: bool = False

    def diagnostics(self) -> list[ProviderStatus]:
        return [
            ProviderStatus(
                name=self.auth.provider_name,
                kind="auth",
                available=self.auth.is_configured(),
                required=self.auth_required,
                degraded=self.auth_required and not self.auth.is_configured(),
            ),
            ProviderStatus(name=self.llm.provider_name, kind="llm", available=self.llm.is_configured()),
            ProviderStatus(
                name=self.web_search.provider_name,
                kind="web_search",
                available=self.web_search.is_configured(),
                required=self.web_search_required,
                degraded=self.web_search_required and not self.web_search.is_configured(),
            ),
            ProviderStatus(
                name=self.voice_stt.provider_name,
                kind="voice_stt",
                available=self.voice_stt.is_configured(),
                required=self.voice_required,
                degraded=self.voice_required and not self.voice_stt.is_configured(),
            ),
            ProviderStatus(
                name=self.voice_tts.provider_name,
                kind="voice_tts",
                available=self.voice_tts.is_configured(),
                required=self.voice_required,
                degraded=self.voice_required and not self.voice_tts.is_configured(),
            ),
            ProviderStatus(
                name=self.voice_realtime.provider_name,
                kind="voice_realtime",
                available=self.voice_realtime.is_configured(),
                required=False,
                degraded=False,
            ),
            ProviderStatus(
                name=self.voice_turn_detection.provider_name,
                kind="voice_turn_detection",
                available=self.voice_turn_detection.is_configured(),
                required=self.voice_required,
                degraded=self.voice_required and not self.voice_turn_detection.is_configured(),
            ),
        ]

    async def aclose(self) -> None:
        for provider in (
            self.auth,
            self.llm,
            self.web_search,
            self.voice_stt,
            self.voice_tts,
            self.voice_realtime,
            self.voice_turn_detection,
        ):
            close = getattr(provider, "aclose", None)
            if callable(close):
                await close()


def build_provider_registry(
    *,
    settings: Settings | None = None,
    auth_provider: AuthProviderPort | None = None,
    llm_provider: LLMProviderPort | None = None,
    web_search_provider: WebSearchProviderPort | None = None,
    voice_stt_provider: STTProviderPort | None = None,
    voice_tts_provider: TTSProviderPort | None = None,
    voice_realtime_provider: RealtimeVoiceProviderPort | None = None,
    voice_turn_detection_provider: TurnDetectionPort | None = None,
) -> ProviderRegistry:
    """Build the shared provider registry."""

    resolved_auth_provider: AuthProviderPort = NoopAuthProvider()
    if settings is not None:
        if settings.resolved_auth_provider == "dev":
            resolved_auth_provider = DevAuthProvider()
        elif settings.resolved_auth_provider == "workos":
            resolved_auth_provider = WorkOSAuthProvider(
                api_key=settings.workos_api_key,
                client_id=settings.workos_client_id,
                cookie_password=settings.workos_cookie_password,
                redirect_uri=settings.workos_redirect_uri,
                logout_return_to=settings.frontend_app_url,
                base_url=settings.workos_base_url or None,
                request_timeout=settings.workos_request_timeout_seconds,
            )
    if auth_provider is not None:
        resolved_auth_provider = auth_provider

    resolved_llm_provider: LLMProviderPort
    if settings is not None and settings.resolved_generic_agent_api_key:
        resolved_llm_provider = OpenAICompatibleLLMProvider(
            provider_name=settings.resolved_generic_agent_provider,
            base_url=settings.resolved_generic_agent_base_url,
            api_key=settings.resolved_generic_agent_api_key,
            model=settings.resolved_generic_agent_model,
            timeout_seconds=settings.generic_agent_timeout_seconds,
            max_retries=settings.generic_agent_provider_max_retries,
            retry_backoff_seconds=settings.generic_agent_provider_retry_backoff_seconds,
            backup_model=settings.generic_agent_backup_model or None,
            backup_model_attempt=settings.generic_agent_backup_model_attempt,
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

    resolved_voice_stt_provider: STTProviderPort = FakeSTTProvider()
    if settings is not None and settings.voice_stt_provider != "fake":
        resolved_voice_stt_provider = _DisabledSTTProvider()
    if voice_stt_provider is not None:
        resolved_voice_stt_provider = voice_stt_provider

    resolved_voice_tts_provider: TTSProviderPort = FakeTTSProvider()
    if settings is not None and settings.voice_tts_provider != "fake":
        resolved_voice_tts_provider = _DisabledTTSProvider()
    if voice_tts_provider is not None:
        resolved_voice_tts_provider = voice_tts_provider

    resolved_voice_realtime_provider: RealtimeVoiceProviderPort = FakeRealtimeVoiceProvider()
    if settings is not None and settings.voice_realtime_provider != "fake":
        resolved_voice_realtime_provider = _DisabledRealtimeVoiceProvider()
    if voice_realtime_provider is not None:
        resolved_voice_realtime_provider = voice_realtime_provider

    resolved_voice_turn_detection_provider: TurnDetectionPort = FakeTurnDetectionProvider()
    if settings is not None and settings.voice_turn_detection_provider != "fake":
        resolved_voice_turn_detection_provider = _DisabledTurnDetectionProvider()
    if voice_turn_detection_provider is not None:
        resolved_voice_turn_detection_provider = voice_turn_detection_provider

    return ProviderRegistry(
        auth=resolved_auth_provider,
        llm=resolved_llm_provider,
        web_search=resolved_web_search_provider,
        voice_stt=resolved_voice_stt_provider,
        voice_tts=resolved_voice_tts_provider,
        voice_realtime=resolved_voice_realtime_provider,
        voice_turn_detection=resolved_voice_turn_detection_provider,
        auth_required=settings.auth_required if settings is not None else False,
        web_search_required=settings.web_search_required if settings is not None else False,
        voice_required=settings.voice_required if settings is not None else False,
    )


class _DisabledSTTProvider(FakeSTTProvider):
    provider_name = "disabled-stt"

    def is_configured(self) -> bool:
        return False


class _DisabledTTSProvider(FakeTTSProvider):
    provider_name = "disabled-tts"

    def is_configured(self) -> bool:
        return False


class _DisabledRealtimeVoiceProvider(FakeRealtimeVoiceProvider):
    provider_name = "disabled-realtime-voice"

    def is_configured(self) -> bool:
        return False


class _DisabledTurnDetectionProvider(FakeTurnDetectionProvider):
    provider_name = "disabled-turn-detection"

    def is_configured(self) -> bool:
        return False
