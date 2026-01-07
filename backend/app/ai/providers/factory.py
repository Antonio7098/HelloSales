"""Factory functions for creating provider instances.

This module uses the provider registry pattern. Providers self-register
at import time, so this factory doesn't need to know about specific providers.
Just add a new provider file and it will be automatically discovered.
"""

import logging
from functools import lru_cache

from app.ai.providers.base import LLMProvider, STTProvider, TTSProvider
from app.ai.providers.llm.stub import StubLLMProvider, StubSTTProvider, StubTTSProvider
from app.ai.providers.registry import (
    ProviderNotFoundError,
    _llm_registry,
    _stt_registry,
    _tts_registry,
)
from app.config import get_settings

logger = logging.getLogger("providers")


def _get_provider_class(
    registry: dict[str, type],
    provider_name: str,
    provider_type: str,
) -> type:
    """Look up a provider class from the registry.

    Args:
        registry: The registry dict to look up in
        provider_name: Name of the provider to find
        provider_type: Type name for error messages (e.g., 'LLM', 'STT', 'TTS')

    Returns:
        The provider class

    Raises:
        ProviderNotFoundError: If provider is not registered
    """
    if provider_name not in registry:
        registered = ", ".join(sorted(registry.keys())) or "(none)"
        raise ProviderNotFoundError(
            f"Unknown {provider_type} provider: '{provider_name}'. "
            f"Registered providers: {registered}"
        )
    return registry[provider_name]


@lru_cache
def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """Get an LLM provider instance.

    Providers are looked up from the registry by name. Adding a new provider
    only requires creating the class and decorating it with @register_llm_provider.

    Args:
        provider: Provider name (e.g., 'groq', 'gemini', 'openrouter', 'stub').
            If None, uses settings.llm_provider.

    Returns:
        LLMProvider instance

    Raises:
        ProviderNotFoundError: If provider is not registered
    """
    settings = get_settings()

    if provider is None:
        provider = settings.llm_provider

    provider = (provider or "").lower().strip() or "groq"

    # Get provider class from registry
    provider_class = _get_provider_class(_llm_registry, provider, "LLM")

    # Handle stub provider specially
    if provider == "stub":
        logger.warning(
            "Using stub LLM provider (explicitly requested)",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "explicit_request",
            },
        )
        return provider_class()

    # Check for missing API key and fall back to stub
    api_key = _get_api_key_for_provider(provider)
    if api_key is None:
        env_var = _get_env_var_for_provider(provider)
        logger.warning(
            f"Using stub LLM provider - {env_var} not configured",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "missing_api_key",
                "expected_env_var": env_var,
                "requested_provider": provider,
            },
        )
        return StubLLMProvider()

    # Try to instantiate the provider
    try:
        instance = provider_class(api_key=api_key)
        logger.info(
            "LLM provider initialized",
            extra={
                "service": "providers",
                "provider": provider,
                "api_key_present": bool(api_key),
            },
        )
        return instance
    except Exception as e:
        logger.warning(
            f"Using stub LLM provider - failed to initialize {provider}: {e}",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "initialization_error",
                "requested_provider": provider,
                "error": str(e),
            },
        )
        return StubLLMProvider()


@lru_cache
def get_stt_provider(provider: str | None = None) -> STTProvider:
    """Get an STT provider instance.

    Providers are looked up from the registry by name. Adding a new provider
    only requires creating the class and decorating it with @register_stt_provider.

    Args:
        provider: Provider name (e.g., 'deepgram', 'groq_whisper', 'stub').
            If None, uses settings.stt_provider.

    Returns:
        STTProvider instance

    Raises:
        ProviderNotFoundError: If provider is not registered
    """
    settings = get_settings()

    if provider is None:
        provider = settings.stt_provider

    # Get provider class from registry
    provider_class = _get_provider_class(_stt_registry, provider, "STT")

    # Handle stub provider specially
    if provider == "stub":
        logger.warning(
            "Using stub STT provider (explicitly requested)",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "explicit_request",
            },
        )
        return provider_class()

    # Resolve model for provider
    raw_model = (settings.stt_model or "").strip() if settings.stt_model is not None else ""
    resolved_model = provider_class.resolve_model(raw_model)

    # Check for missing API key and fall back to stub
    api_key = _get_api_key_for_provider(provider)
    if api_key is None:
        env_var = _get_env_var_for_provider(provider)
        logger.warning(
            f"Using stub STT provider - {env_var} not configured",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "missing_api_key",
                "expected_env_var": env_var,
                "requested_provider": provider,
            },
        )
        return StubSTTProvider()

    # Try to instantiate the provider
    try:
        instance = provider_class(api_key=api_key, model=resolved_model)
        logger.info(
            "STT provider initialized",
            extra={
                "service": "providers",
                "provider": provider,
                "api_key_present": bool(api_key),
                "model": resolved_model,
            },
        )
        return instance
    except Exception as e:
        logger.warning(
            f"Using stub STT provider - failed to initialize {provider}: {e}",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "initialization_error",
                "requested_provider": provider,
                "error": str(e),
            },
        )
        return StubSTTProvider()


@lru_cache
def get_tts_provider(provider: str | None = None) -> TTSProvider:
    """Get a TTS provider instance.

    Providers are looked up from the registry by name. Adding a new provider
    only requires creating the class and decorating it with @register_tts_provider.

    Args:
        provider: Provider name. If None, uses settings.tts_provider.

    Returns:
        TTSProvider instance

    Raises:
        ProviderNotFoundError: If provider is not registered
    """
    settings = get_settings()

    if provider is None:
        provider = getattr(settings, "tts_provider", "google")

    # Get provider class from registry
    provider_class = _get_provider_class(_tts_registry, provider, "TTS")

    # Handle stub provider specially
    if provider == "stub":
        logger.warning(
            "Using stub TTS provider (explicitly requested)",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "explicit_request",
            },
        )
        return provider_class()

    # Check for missing API key and fall back to stub
    api_key = _get_api_key_for_provider(provider)
    if api_key is None:
        env_var = _get_env_var_for_provider(provider)
        logger.warning(
            f"Using stub TTS provider - {env_var} not configured",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "missing_api_key",
                "expected_env_var": env_var,
                "requested_provider": provider,
            },
        )
        return StubTTSProvider()

    # Try to instantiate the provider
    try:
        instance = provider_class(api_key=api_key)
        logger.info(
            "TTS provider initialized",
            extra={
                "service": "providers",
                "provider": provider,
                "api_key_present": bool(api_key),
            },
        )
        return instance
    except Exception as e:
        logger.warning(
            f"Using stub TTS provider - failed to initialize {provider}: {e}",
            extra={
                "service": "providers",
                "provider": "stub",
                "reason": "initialization_error",
                "requested_provider": provider,
                "error": str(e),
            },
        )
        return StubTTSProvider()


def _get_api_key_for_provider(provider: str) -> str | None:
    """Get API key for a provider from settings.

    Args:
        provider: Provider name

    Returns:
        API key string or None if not configured
    """
    settings = get_settings()

    provider_key_mapping = {
        "groq": settings.groq_api_key,
        "gemini": settings.google_api_key,
        "openrouter": settings.openrouter_api_key,
        "deepgram": settings.deepgram_api_key,
        "deepgram_flux": settings.deepgram_api_key,
        "groq_whisper": settings.groq_api_key,
        "whisper": settings.groq_api_key,
        "google": settings.google_api_key,
    }

    return provider_key_mapping.get(provider)


def _get_env_var_for_provider(provider: str) -> str:
    """Get expected environment variable for a provider.

    Args:
        provider: Provider name

    Returns:
        Environment variable name
    """
    provider_env_mapping = {
        "groq": "GROQ_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "deepgram": "DEEPGRAM_API_KEY",
        "deepgram_flux": "DEEPGRAM_API_KEY",
        "groq_whisper": "GROQ_API_KEY",
        "whisper": "GROQ_API_KEY",
        "google": "GOOGLE_API_KEY",
        "gemini_flash": "GOOGLE_API_KEY",
    }

    return provider_env_mapping.get(provider, f"{provider.upper()}_API_KEY")
