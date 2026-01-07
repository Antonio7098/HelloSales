"""Unit tests for ChatService."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.providers.base import LLMMessage
from app.domains.chat.service import (
    ALWAYS_INCLUDE_LAST_N,
    SUMMARY_THRESHOLD,
    SYSTEM_PROMPT,
    ChatContext,
    ChatService,
)
from app.prompts.onboarding import ONBOARDING_PROMPT


class TestChatService:
    """Tests for ChatService."""

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
    def mock_llm(self):
        """Create a mock LLM provider."""
        llm = AsyncMock()
        llm.name = "mock"
        # resolve_model is a sync classmethod, not async
        llm.resolve_model = MagicMock(return_value="mock-model")
        return llm

    @pytest.fixture
    def chat_service(self, mock_db, mock_llm):
        """Create a ChatService with mocked dependencies."""
        return ChatService(db=mock_db, llm_provider=mock_llm)

    async def test_build_context_empty_session(self, chat_service, mock_db):
        """Test building context for an empty session."""
        session_id = uuid.uuid4()

        # Mock: no summary exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        context = await chat_service.build_context(session_id)

        # Should have system prompt
        assert len(context.messages) >= 1
        assert context.messages[0].role == "system"
        assert chat_service.system_prompt in context.messages[0].content
        assert context.summary_text is None
        assert context.cutoff_at is None

    async def test_build_context_onboarding_replaces_system_prompt(self, chat_service, mock_db):
        """Onboarding sessions should use the onboarding prompt instead of the coaching prompt."""
        session_id = uuid.uuid4()

        def mock_execute(query):
            result = MagicMock()
            text = str(query).lower()

            # Session.is_onboarding lookup - be more flexible with matching
            if "sessions" in text and "is_onboarding" in text:
                result.scalar_one_or_none.return_value = True
                return result

            # No meta summary for this test
            if "user_meta_summaries" in text:
                result.scalar_one_or_none.return_value = None
                return result

            # No summary
            if "session_summaries" in text:
                result.scalar_one_or_none.return_value = None
                return result

            # No interactions
            if "interactions" in text:
                result.scalars.return_value.all.return_value = []
                return result

            # Anything else (e.g. profile lookups) => empty
            result.scalar_one_or_none.return_value = None
            result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        context = await chat_service.build_context(session_id=session_id, platform="native")

        # First system message should be the onboarding prompt
        assert len(context.messages) >= 1
        assert context.messages[0].role == "system"
        assert context.messages[0].content == ONBOARDING_PROMPT

        # Coaching system prompt should not be present anywhere in onboarding context
        assert not any(
            (m.role == "system" and chat_service.system_prompt in m.content)
            for m in context.messages
        )

    async def test_build_context_with_summary(self, chat_service, mock_db):
        """Test building context when a summary exists."""
        from datetime import datetime

        session_id = uuid.uuid4()

        # Mock summary
        mock_summary = MagicMock()
        mock_summary.text = "User discussed presentation skills."
        mock_summary.created_at = datetime.utcnow()

        # Mock interactions
        mock_interaction = MagicMock()
        mock_interaction.role = "user"
        mock_interaction.content = "How can I improve?"

        # Set up mock returns
        def mock_execute(query):
            result = MagicMock()
            # First call: get summary
            if "session_summaries" in str(query):
                result.scalar_one_or_none.return_value = mock_summary
            # Second call: get interactions
            else:
                result.scalars.return_value.all.return_value = [mock_interaction]
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        context = await chat_service.build_context(session_id)

        # Should have system prompt + summary context + interaction
        assert context.summary_text == "User discussed presentation skills."
        assert context.cutoff_at == mock_summary.created_at

    async def test_handle_message_streams_response(self, chat_service, mock_db, mock_llm):
        """Test that handle_message streams tokens."""
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        content = "Hello!"

        # Mock build_context to return minimal context
        chat_service.build_context = AsyncMock(
            return_value=ChatContext(
                messages=[LLMMessage(role="system", content=SYSTEM_PROMPT)],
            )
        )

        # Mock LLM streaming
        async def mock_stream(*_args, **_kwargs):
            for token in ["Hello", " ", "there", "!"]:
                yield token

        mock_llm.stream = mock_stream

        # Mock database operations
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Track tokens
        received_tokens = []
        status_updates = []

        async def track_token(token):
            received_tokens.append(token)

        async def track_status(service, status, _metadata):
            status_updates.append((service, status))

        response, msg_id = await chat_service.handle_message(
            session_id=session_id,
            user_id=user_id,
            content=content,
            send_status=track_status,
            send_token=track_token,
        )

        assert response == "Hello there!"
        assert received_tokens == ["Hello", " ", "there", "!"]
        assert ("llm", "started") in status_updates
        assert ("llm", "streaming") in status_updates
        assert ("llm", "complete") in status_updates


class TestChatContext:
    """Tests for ChatContext dataclass."""

    def test_context_with_messages(self):
        """Test creating a context with messages."""
        messages = [
            LLMMessage(role="system", content="System prompt"),
            LLMMessage(role="user", content="Hello"),
        ]

        context = ChatContext(messages=messages)

        assert len(context.messages) == 2
        assert context.summary_text is None
        assert context.cutoff_at is None

    def test_context_with_summary(self):
        """Test creating a context with summary."""
        from datetime import datetime

        cutoff = datetime.utcnow()
        context = ChatContext(
            messages=[LLMMessage(role="system", content="System")],
            summary_text="Previous conversation summary",
            cutoff_at=cutoff,
        )

        assert context.summary_text == "Previous conversation summary"
        assert context.cutoff_at == cutoff


class TestChatServiceConstants:
    """Tests for chat service constants."""

    def test_always_include_last_n_value(self):
        """Test ALWAYS_INCLUDE_LAST_N is set correctly."""
        assert ALWAYS_INCLUDE_LAST_N == 6

    def test_summary_threshold_value(self):
        """Test SUMMARY_THRESHOLD is set correctly."""
        assert SUMMARY_THRESHOLD == 8  # 8 messages = 4 turn pairs


class TestChatServiceMetrics:
    """Tests for ChatService metrics tracking."""

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
    def mock_llm(self):
        """Create a mock LLM provider."""
        llm = AsyncMock()
        llm.name = "mock"
        return llm

    @pytest.fixture
    def chat_service(self, mock_db, mock_llm):
        """Create a ChatService with mocked dependencies."""
        return ChatService(db=mock_db, llm_provider=mock_llm)

    async def test_save_interaction_with_metrics(self, chat_service):
        """Test that _save_interaction correctly saves metrics."""
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()

        # Mock the Interaction model
        with patch("app.domains.chat.service.Interaction") as MockInteraction:
            mock_instance = MagicMock()
            MockInteraction.return_value = mock_instance

            await chat_service._save_interaction(
                session_id=session_id,
                role="assistant",
                content="Hello!",
                message_id=message_id,
                latency_ms=500,
                tokens_in=100,
                tokens_out=50,
                llm_cost_cents=1,
            )

            # Verify the Interaction was created, but metrics are no longer
            # stored on the Interaction itself (they live in ProviderCall).
            MockInteraction.assert_called_once()
            call_kwargs = MockInteraction.call_args[1]
            assert call_kwargs == {
                "id": message_id,
                "session_id": session_id,
                "message_id": message_id,
                "role": "assistant",
                "content": "Hello!",
                "input_type": None,
            }


class TestBuildContextWithLastN:
    """Tests for build_context with always-include-last-N behavior."""

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
    def mock_llm(self):
        """Create a mock LLM provider."""
        llm = AsyncMock()
        llm.name = "mock"
        return llm

    @pytest.fixture
    def chat_service(self, mock_db, mock_llm):
        """Create a ChatService with mocked dependencies."""
        return ChatService(db=mock_db, llm_provider=mock_llm)

    def _create_mock_interaction(self, _idx: int, role: str, content: str, created_at: datetime):
        """Helper to create a mock interaction."""
        mock = MagicMock()
        mock.id = uuid.uuid4()
        mock.role = role
        mock.content = content
        mock.created_at = created_at
        return mock

    async def test_build_context_includes_last_n_after_summary(self, chat_service, mock_db):
        """Test that build_context always includes last N messages even after summary."""
        session_id = uuid.uuid4()
        base_time = datetime.utcnow()

        # Create mock summary that was created after messages 1-4
        mock_summary = MagicMock()
        mock_summary.text = "User discussed presentation skills."
        mock_summary.created_at = base_time - timedelta(minutes=5)  # Summary created 5 min ago

        # Create messages - 2 before summary cutoff, 2 after
        # The "last 4" would include the 2 before + 2 after
        messages_before_summary = [
            self._create_mock_interaction(
                1, "user", "Message before summary 1", base_time - timedelta(minutes=10)
            ),
            self._create_mock_interaction(
                2, "assistant", "Response before summary 1", base_time - timedelta(minutes=9)
            ),
        ]

        messages_after_summary = [
            self._create_mock_interaction(
                3, "user", "Message after summary", base_time - timedelta(minutes=2)
            ),
            self._create_mock_interaction(
                4, "assistant", "Response after summary", base_time - timedelta(minutes=1)
            ),
        ]

        all_messages = messages_before_summary + messages_after_summary

        interactions_call_count = 0

        def mock_execute(query):
            nonlocal interactions_call_count
            result = MagicMock()
            text = str(query)

            if "session_summaries" in text:
                # Latest summary
                result.scalar_one_or_none.return_value = mock_summary
            elif "FROM interactions" in text:
                # Only count interaction queries; profile/session lookups are ignored
                if interactions_call_count == 0:
                    # After-cutoff interactions
                    result.scalars.return_value.all.return_value = messages_after_summary
                elif interactions_call_count == 1:
                    # Last-N interactions
                    result.scalars.return_value.all.return_value = all_messages[-4:]
                else:
                    result.scalars.return_value.all.return_value = []
                interactions_call_count += 1
            else:
                # Queries from _build_profile_context etc - just return "no result"
                result.scalar_one_or_none.return_value = None
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        context = await chat_service.build_context(session_id)

        # Should have: system + summary + merged messages
        # The merged messages should include both before and after summary
        assert context.summary_text == "User discussed presentation skills."

        # Check that we have more than just after-summary messages
        # (system + summary + 4 messages)
        user_assistant_messages = [m for m in context.messages if m.role in ("user", "assistant")]
        assert len(user_assistant_messages) == 4

    async def test_build_context_deduplicates_overlapping_messages(self, chat_service, mock_db):
        """Test that overlapping messages from after_summary and last_n are deduped."""
        session_id = uuid.uuid4()
        base_time = datetime.utcnow()

        # No summary - both queries return same messages
        shared_messages = [
            self._create_mock_interaction(1, "user", "Hello", base_time - timedelta(minutes=2)),
            self._create_mock_interaction(
                2, "assistant", "Hi there", base_time - timedelta(minutes=1)
            ),
        ]

        interactions_call_count = 0

        def mock_execute(query):
            nonlocal interactions_call_count
            result = MagicMock()
            text = str(query)

            if "session_summaries" in text:
                result.scalar_one_or_none.return_value = None
            elif "FROM interactions" in text:
                if interactions_call_count == 0:
                    # After-cutoff
                    result.scalars.return_value.all.return_value = shared_messages
                elif interactions_call_count == 1:
                    # Last-N (same messages)
                    result.scalars.return_value.all.return_value = shared_messages
                else:
                    result.scalars.return_value.all.return_value = []
                interactions_call_count += 1
            else:
                # Ignore other queries (e.g. profile-related)
                result.scalar_one_or_none.return_value = None
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        context = await chat_service.build_context(session_id)

        # Should NOT have duplicates - only 2 user/assistant messages
        user_assistant_messages = [m for m in context.messages if m.role in ("user", "assistant")]
        assert len(user_assistant_messages) == 2

    async def test_build_context_maintains_chronological_order(self, chat_service, mock_db):
        """Test that merged messages are in chronological order."""
        session_id = uuid.uuid4()
        base_time = datetime.utcnow()

        # Create messages with specific timestamps
        msg1 = self._create_mock_interaction(1, "user", "First", base_time - timedelta(minutes=4))
        msg2 = self._create_mock_interaction(
            2, "assistant", "Second", base_time - timedelta(minutes=3)
        )
        msg3 = self._create_mock_interaction(3, "user", "Third", base_time - timedelta(minutes=2))
        msg4 = self._create_mock_interaction(
            4, "assistant", "Fourth", base_time - timedelta(minutes=1)
        )

        interactions_call_count = 0

        def mock_execute(query):
            nonlocal interactions_call_count
            result = MagicMock()
            text = str(query)

            if "session_summaries" in text:
                result.scalar_one_or_none.return_value = None
            elif "FROM interactions" in text:
                if interactions_call_count == 0:
                    # After-cutoff - deliberately out of order
                    result.scalars.return_value.all.return_value = [msg3, msg1, msg4, msg2]
                elif interactions_call_count == 1:
                    # Last N
                    result.scalars.return_value.all.return_value = [msg2, msg4]
                else:
                    result.scalars.return_value.all.return_value = []
                interactions_call_count += 1
            else:
                # Non-interaction queries (profile/session lookups)
                result.scalar_one_or_none.return_value = None
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        context = await chat_service.build_context(session_id)

        # Extract user/assistant messages
        user_assistant_messages = [m for m in context.messages if m.role in ("user", "assistant")]

        # Should be in order: First, Second, Third, Fourth
        assert user_assistant_messages[0].content == "First"
        assert user_assistant_messages[1].content == "Second"
        assert user_assistant_messages[2].content == "Third"
        assert user_assistant_messages[3].content == "Fourth"


class TestAssessmentContextInjection:
    """Tests for assessment injection into LLM context."""

    @pytest.fixture
    def chat_service(self):
        """Create a ChatService with mocked dependencies."""
        db = AsyncMock()
        llm = AsyncMock()
        llm.name = "mock"
        return ChatService(db=db, llm_provider=llm)

    def test_format_assessment_context_empty(self, chat_service):
        """Test that empty assessments return None."""
        result = chat_service._format_assessment_context([])
        assert result is None

    def test_format_assessment_context_with_data(self, chat_service):
        """Test formatting a skill assessment into context."""
        # Create mock skill assessment
        mock_skill = MagicMock()
        mock_skill.title = "Clarity"

        mock_sa = MagicMock()
        mock_sa.skill = mock_skill
        mock_sa.level = 7
        mock_sa.confidence = 0.85
        mock_sa.summary = "Good structure and clear explanation."
        mock_sa.feedback = {"next_level_criteria": "Add more concrete examples"}

        result = chat_service._format_assessment_context([mock_sa])

        assert result is not None
        assert "[Prior assessment of user's response:]" in result
        assert "Clarity: Level 7/10" in result
        assert "(conf: 85%)" in result
        assert "Good structure and clear explanation." in result
        assert "Focus: Add more concrete examples" in result

    def test_format_assessment_context_truncates_long_summary(self, chat_service):
        """Test that long summaries are truncated."""
        mock_skill = MagicMock()
        mock_skill.title = "Fluency"

        mock_sa = MagicMock()
        mock_sa.skill = mock_skill
        mock_sa.level = 5
        mock_sa.confidence = None  # No confidence
        mock_sa.summary = "A" * 200  # Very long summary
        mock_sa.feedback = {}

        result = chat_service._format_assessment_context([mock_sa])

        assert result is not None
        assert "..." in result  # Should be truncated
        assert len(result) < 400  # Should be reasonably short

    async def test_get_assessments_for_interactions_empty(self, chat_service):
        """Test batch fetch with no interaction IDs returns empty dict."""
        result = await chat_service._get_assessments_for_interactions([])
        assert result == {}
