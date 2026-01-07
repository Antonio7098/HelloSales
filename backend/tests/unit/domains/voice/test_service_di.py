"""Tests for VoiceService DI integration."""

from unittest.mock import MagicMock

import pytest

from app.core.di import get_container, reset_container
from app.domains.voice.service import VoiceService


class TestVoiceServiceDI:
    """Test VoiceService uses DI container correctly."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Reset container after each test."""
        reset_container()

    def test_voice_service_uses_container_for_stt_provider(self):
        """Test that VoiceService uses container for STT provider when not provided."""
        mock_stt = MagicMock()
        mock_stt.name = "mock_stt"

        container = get_container()
        container.override_stt_provider(mock_stt)

        service = VoiceService(db=None)

        assert service.stt is mock_stt

    def test_voice_service_uses_container_for_tts_provider(self):
        """Test that VoiceService uses container for TTS provider when not provided."""
        mock_tts = MagicMock()
        mock_tts.name = "mock_tts"

        container = get_container()
        container.override_tts_provider(mock_tts)

        service = VoiceService(db=None)

        assert service.tts is mock_tts

    def test_voice_service_accepts_explicit_providers(self):
        """Test that VoiceService uses explicitly provided providers."""
        mock_stt = MagicMock()
        mock_stt.name = "explicit_stt"
        mock_tts = MagicMock()
        mock_tts.name = "explicit_tts"

        service = VoiceService(
            db=None,
            stt_provider=mock_stt,
            tts_provider=mock_tts,
        )

        assert service.stt is mock_stt
        assert service.tts is mock_tts

    def test_explicit_provider_overrides_container(self):
        """Test that explicit provider takes precedence over container."""
        container_stt = MagicMock()
        container_stt.name = "container_stt"
        explicit_stt = MagicMock()
        explicit_stt.name = "explicit_stt"

        container = get_container()
        container.override_stt_provider(container_stt)

        service = VoiceService(db=None, stt_provider=explicit_stt)

        assert service.stt is explicit_stt
        assert service.stt is not container_stt


class TestChatServiceDI:
    """Test ChatService DI integration."""

    def setup_method(self):
        """Reset container before each test."""
        reset_container()

    def teardown_method(self):
        """Reset container after each test."""
        reset_container()

    def test_chat_service_requires_llm_provider(self):
        """Test that ChatService requires llm_provider in constructor."""
        from app.domains.chat.service import ChatService

        # ChatService should raise if llm_provider is None
        with pytest.raises(ValueError, match="llm_provider is required"):
            ChatService(db=MagicMock(), llm_provider=None)

    def test_chat_service_accepts_explicit_provider(self):
        """Test that ChatService uses explicitly provided LLM provider."""
        from app.domains.chat.service import ChatService

        mock_provider = MagicMock()
        mock_provider.name = "explicit_llm"

        service = ChatService(db=MagicMock(), llm_provider=mock_provider)

        assert service.llm is mock_provider

    def test_create_chat_service_factory(self):
        """Test DI container create_chat_service factory method."""
        from app.domains.chat.service import ChatService

        mock_db = MagicMock()
        mock_provider = MagicMock()
        mock_provider.name = "factory_llm"

        container = get_container()
        container.override_llm_provider(mock_provider)

        service = container.create_chat_service(db=mock_db)

        assert isinstance(service, ChatService)
        assert service.llm is mock_provider
        assert service.db is mock_db
