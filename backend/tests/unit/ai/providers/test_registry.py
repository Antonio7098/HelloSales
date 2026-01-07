"""Tests for the provider registry system."""

import pytest

from app.ai.providers.base import LLMProvider, STTProvider, TTSProvider
from app.ai.providers.registry import (
    DuplicateProviderError,
    ProviderNotFoundError,
    ProviderRegistryError,
    get_registered_llm_providers,
    get_registered_stt_providers,
    get_registered_tts_providers,
    is_llm_provider_registered,
    is_stt_provider_registered,
    is_tts_provider_registered,
    register_llm_provider,
    register_stt_provider,
    register_tts_provider,
)


class TestProviderRegistry:
    """Test provider registry functionality."""

    def test_llm_providers_are_registered(self):
        """Test that expected LLM providers are registered."""
        providers = get_registered_llm_providers()
        assert "stub" in providers
        assert "groq" in providers
        assert "gemini" in providers
        assert "openrouter" in providers

    def test_stt_providers_are_registered(self):
        """Test that expected STT providers are registered."""
        providers = get_registered_stt_providers()
        assert "stub" in providers
        assert "deepgram" in providers
        assert "groq_whisper" in providers
        assert "google" in providers

    def test_tts_providers_are_registered(self):
        """Test that expected TTS providers are registered."""
        providers = get_registered_tts_providers()
        assert "stub" in providers
        assert "google" in providers
        assert "gemini_tts" in providers

    def test_is_llm_provider_registered(self):
        """Test is_llm_provider_registered helper."""
        assert is_llm_provider_registered("stub") is True
        assert is_llm_provider_registered("groq") is True
        assert is_llm_provider_registered("nonexistent") is False

    def test_is_stt_provider_registered(self):
        """Test is_stt_provider_registered helper."""
        assert is_stt_provider_registered("stub") is True
        assert is_stt_provider_registered("deepgram") is True
        assert is_stt_provider_registered("nonexistent") is False

    def test_is_tts_provider_registered(self):
        """Test is_tts_provider_registered helper."""
        assert is_tts_provider_registered("stub") is True
        assert is_tts_provider_registered("google") is True
        assert is_tts_provider_registered("nonexistent") is False


class TestRegisterLLMProviderDecorator:
    """Test the @register_llm_provider decorator."""

    def test_register_new_provider(self):
        """Test registering a new LLM provider."""

        # Create a test provider class
        @register_llm_provider
        class TestLLMProvider(LLMProvider):
            @property
            def name(self) -> str:
                return "test_llm"

            async def generate(self, _messages, **_kwargs):
                pass

            async def stream(self, _messages, **_kwargs):
                yield ""

        try:
            # Verify it's registered
            providers = get_registered_llm_providers()
            assert "test_llm" in providers
            assert providers["test_llm"] is TestLLMProvider
        finally:
            # Clean up - remove from registry
            from app.ai.providers import registry
            registry._llm_registry.pop("test_llm", None)

    def test_register_duplicate_raises_error(self):
        """Test that registering a duplicate provider raises an error."""

        # Create a new class with the same name as an existing one
        class DuplicateStubProvider(LLMProvider):
            @property
            def name(self) -> str:
                return "stub"

            async def generate(self, _messages, **_kwargs):
                pass

            async def stream(self, _messages, **_kwargs):
                yield ""

        with pytest.raises(DuplicateProviderError):
            register_llm_provider(DuplicateStubProvider)

    def test_register_without_name_raises_error(self):
        """Test that registering a provider without a name raises an error."""

        # Create a class that doesn't have a name property (not inheriting from LLMProvider)
        class NamelessProvider:
            async def generate(self, _messages, **_kwargs):
                pass

            async def stream(self, _messages, **_kwargs):
                yield ""

        with pytest.raises(ProviderRegistryError):
            register_llm_provider(NamelessProvider)


class TestRegisterSTTProviderDecorator:
    """Test the @register_stt_provider decorator."""

    def test_register_new_provider(self):
        """Test registering a new STT provider."""

        @register_stt_provider
        class TestSTTProvider(STTProvider):
            @property
            def name(self) -> str:
                return "test_stt"

            async def transcribe(self, audio_data, **kwargs):
                pass

        try:
            providers = get_registered_stt_providers()
            assert "test_stt" in providers
            assert providers["test_stt"] is TestSTTProvider
        finally:
            from app.ai.providers import registry
            registry._stt_registry.pop("test_stt", None)


class TestRegisterTTSProviderDecorator:
    """Test the @register_tts_provider decorator."""

    def test_register_new_provider(self):
        """Test registering a new TTS provider."""

        @register_tts_provider
        class TestTTSProvider(TTSProvider):
            @property
            def name(self) -> str:
                return "test_tts"

            async def synthesize(self, text, **kwargs):
                pass

        try:
            providers = get_registered_tts_providers()
            assert "test_tts" in providers
            assert providers["test_tts"] is TestTTSProvider
        finally:
            from app.ai.providers import registry
            registry._tts_registry.pop("test_tts", None)


class TestProviderRegistryError:
    """Test provider registry error classes."""

    def test_provider_not_found_error(self):
        """Test ProviderNotFoundError."""
        error = ProviderNotFoundError("Unknown provider: test")
        assert "Unknown provider: test" in str(error)
        assert isinstance(error, ProviderRegistryError)

    def test_duplicate_provider_error(self):
        """Test DuplicateProviderError."""
        error = DuplicateProviderError("Provider 'test' already registered")
        assert "Provider 'test' already registered" in str(error)
        assert isinstance(error, ProviderRegistryError)


class TestRegistryReturnsCopies:
    """Test that registry getters return copies, not references."""

    def test_get_registered_llm_providers_returns_copy(self):
        """Test that get_registered_llm_providers returns a copy."""
        providers1 = get_registered_llm_providers()
        providers2 = get_registered_llm_providers()

        # Should be equal in content
        assert providers1.keys() == providers2.keys()

        # But not the same object
        assert providers1 is not providers2

        # Modifying one shouldn't affect the other
        providers1["__test_key__"] = None
        providers3 = get_registered_llm_providers()
        assert "__test_key__" not in providers3
