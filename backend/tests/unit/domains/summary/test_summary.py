"""Unit tests for SummaryService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.providers.base import LLMResponse
from app.domains.assessment.summary import DEFAULT_SUMMARY_THRESHOLD, SummaryService


class TestSummaryService:
    """Tests for SummaryService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def summary_service(self, mock_db):
        """Create a SummaryService with mocked dependencies."""
        with MagicMock() as mock_llm:
            mock_llm.name = "mock"
            service = SummaryService(db=mock_db, summary_threshold=5)
            service.llm = mock_llm
            return service

    async def test_check_and_trigger_below_threshold(self, summary_service, mock_db):
        """Test that summary is not generated below threshold."""
        session_id = uuid.uuid4()

        # Mock summary state with 4 turns (below threshold of 5)
        mock_state = MagicMock()
        mock_state.turns_since = 8  # 4 turn pairs

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state
        mock_db.execute.return_value = mock_result

        result = await summary_service.check_and_trigger(session_id)

        assert result is None

    async def test_check_and_trigger_at_threshold(self, summary_service, mock_db):
        """Test that summary is generated at threshold."""
        session_id = uuid.uuid4()

        # Mock summary state at threshold (5 turn pairs = 10 messages)
        mock_state = MagicMock()
        mock_state.turns_since = 10

        # Set up mock to return state, then interactions
        call_count = 0

        def mock_execute(_query):
            nonlocal call_count
            result = MagicMock()

            if call_count == 0:
                # First: get summary state
                result.scalar_one_or_none.return_value = mock_state
            elif call_count == 1:
                # Second: get latest summary (none)
                result.scalar_one_or_none.return_value = None
            elif call_count == 2:
                # Third: get interactions
                mock_interaction = MagicMock()
                mock_interaction.role = "user"
                mock_interaction.content = "Hello"
                mock_interaction.idx = 0
                result.scalars.return_value.all.return_value = [mock_interaction]
            elif call_count == 3:
                # Fourth: get max version
                result.scalar.return_value = None
            else:
                result.scalar_one_or_none.return_value = mock_state

            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        # Mock LLM response
        summary_service.llm.generate = AsyncMock(
            return_value=LLMResponse(
                content="This is a summary of the conversation.",
                model="mock",
                tokens_in=100,
                tokens_out=20,
            )
        )

        status_updates = []

        async def track_status(service, status, _metadata):
            status_updates.append((service, status))

        result = await summary_service.check_and_trigger(session_id, track_status)

        # Should have generated a summary
        assert result is not None
        assert ("summary", "started") in status_updates
        assert ("summary", "complete") in status_updates

    async def test_check_and_trigger_no_state(self, summary_service, mock_db):
        """Test handling when no summary state exists."""
        session_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await summary_service.check_and_trigger(session_id)

        assert result is None

    def test_format_conversation(self, summary_service):
        """Test conversation formatting for summary prompt."""
        mock_interactions = [
            MagicMock(role="user", content="Hello, I need help with my presentation."),
            MagicMock(
                role="assistant",
                content="I'd be happy to help! What aspect would you like to work on?",
            ),
            MagicMock(role="user", content="I want to sound more confident."),
        ]

        result = summary_service._format_conversation(mock_interactions)

        assert "User: Hello, I need help with my presentation." in result
        assert "Coach: I'd be happy to help!" in result
        assert "User: I want to sound more confident." in result

    def test_default_summary_threshold(self):
        """Test default summary threshold value."""
        assert DEFAULT_SUMMARY_THRESHOLD == 4  # 4 turn pairs = 8 messages
