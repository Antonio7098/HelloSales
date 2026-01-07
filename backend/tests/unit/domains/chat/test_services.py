"""Tests for extracted chat service classes (SRP compliance)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


class TestChatPersistenceService:
    """Tests for ChatPersistenceService."""

    def test_initialization(self):
        """Test persistence service initializes with db."""
        from app.domains.chat.services import ChatPersistenceService

        mock_db = MagicMock()
        service = ChatPersistenceService(db=mock_db)

        assert service.db is mock_db

    @pytest.mark.asyncio
    async def test_save_interaction_creates_record(self):
        """Test save_interaction creates an Interaction record."""
        from app.domains.chat.services import ChatPersistenceService

        mock_db = MagicMock()
        mock_db.flush = AsyncMock()

        service = ChatPersistenceService(db=mock_db)

        session_id = uuid4()
        message_id = uuid4()

        await service.save_interaction(
            session_id=session_id,
            role="user",
            content="Hello",
            message_id=message_id,
        )

        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.session_id == session_id
        assert added.role == "user"
        assert added.content == "Hello"

    @pytest.mark.asyncio
    async def test_save_assistant_interaction(self):
        """Test saving assistant message."""
        from app.domains.chat.services import ChatPersistenceService

        mock_db = MagicMock()
        mock_db.flush = AsyncMock()

        service = ChatPersistenceService(db=mock_db)

        await service.save_interaction(
            session_id=uuid4(),
            role="assistant",
            content="Hello! How can I help?",
            message_id=uuid4(),
        )

        added = mock_db.add.call_args[0][0]
        assert added.role == "assistant"

    @pytest.mark.asyncio
    async def test_complete_onboarding_when_not_onboarding(self):
        """Test onboarding completion returns False for non-onboarding session."""
        from app.domains.chat.services import ChatPersistenceService

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=False)
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ChatPersistenceService(db=mock_db)

        result = await service.complete_onboarding(
            session_id=uuid4(),
            user_id=uuid4(),
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_interaction_found(self):
        """Test retrieving an interaction when it exists."""
        from app.domains.chat.services import ChatPersistenceService

        mock_db = MagicMock()
        interaction_id = uuid4()
        mock_interaction = MagicMock()
        mock_interaction.id = interaction_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_interaction)
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ChatPersistenceService(db=mock_db)

        result = await service.get_interaction(interaction_id)

        assert result is mock_interaction

    @pytest.mark.asyncio
    async def test_get_interaction_not_found(self):
        """Test retrieving a non-existent interaction."""
        from app.domains.chat.services import ChatPersistenceService

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ChatPersistenceService(db=mock_db)

        result = await service.get_interaction(uuid4())

        assert result is None


class TestChatContextService:
    """Tests for ChatContextService."""

    def test_initialization(self):
        """Test context service initializes with system prompt."""
        from app.domains.chat.services import ChatContextService

        mock_db = MagicMock()
        system_prompt = "You are a helpful assistant."

        service = ChatContextService(db=mock_db, system_prompt=system_prompt)

        assert service.system_prompt == system_prompt
        assert service.db is mock_db

    def test_prefetched_enrichers_dataclass(self):
        """Test PrefetchedEnrichers dataclass."""
        from app.domains.chat.services.context import PrefetchedEnrichers

        enrichers = PrefetchedEnrichers(
            is_onboarding=True,
            meta_summary_text="Test summary",
            summary=None,
            profile_text="Test profile",
            last_n=[],
        )

        assert enrichers.is_onboarding is True
        assert enrichers.meta_summary_text == "Test summary"
        assert enrichers.summary is None

    def test_chat_context_dataclass(self):
        """Test ChatContext dataclass."""
        from app.ai.providers.base import LLMMessage
        from app.domains.chat.services.context import ChatContext

        messages = [LLMMessage(role="user", content="Hi")]
        context = ChatContext(
            messages=messages,
            summary_text="Earlier conversation",
        )

        assert len(context.messages) == 1
        assert context.summary_text == "Earlier conversation"


class TestChatStreamingService:
    """Tests for ChatStreamingService."""

    def test_initialization(self):
        """Test streaming service initializes with LLM provider."""
        from app.domains.chat.services import ChatStreamingService

        mock_db = MagicMock()
        mock_provider = MagicMock()
        mock_provider.name = "test"

        service = ChatStreamingService(db=mock_db, llm_provider=mock_provider)

        assert service.db is mock_db
        assert service.llm is mock_provider

    def test_has_stream_with_fallback_method(self):
        """Test streaming service has stream_with_fallback method."""
        from app.domains.chat.services import ChatStreamingService

        mock_db = MagicMock()
        mock_provider = MagicMock()

        service = ChatStreamingService(db=mock_db, llm_provider=mock_provider)

        assert hasattr(service, 'stream_with_fallback')
        assert callable(service.stream_with_fallback)


class TestChatServicesModule:
    """Tests for the chat services module exports."""

    def test_exports(self):
        """Test module exports are correct."""
        from app.domains.chat import services

        assert hasattr(services, "ChatPersistenceService")
        assert hasattr(services, "ChatContextService")
        assert hasattr(services, "ChatStreamingService")

    def test_all_exports_match(self):
        """Test __all__ matches available exports."""
        from app.domains.chat import services

        for name in services.__all__:
            assert hasattr(services, name)

    def test_import_from_domain(self):
        """Test services can be imported from domain."""
        from app.domains.chat import (
            ChatContextService,
            ChatPersistenceService,
            ChatStreamingService,
        )

        assert ChatPersistenceService is not None
        assert ChatContextService is not None
        assert ChatStreamingService is not None
