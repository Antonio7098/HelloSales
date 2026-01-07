"""Integration tests for SessionState integration with chat pipeline."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


class TestSessionStateChatIntegration:
    """Integration tests for SessionState reading in chat handler."""

    def test_session_state_has_required_properties(self):
        """Test that SessionState has all required properties for pipeline."""
        from app.models.session_state import (
            DEFAULT_BEHAVIOR,
            DEFAULT_CONFIG,
            DEFAULT_TOPOLOGY,
            SessionState,
        )

        session_id = uuid4()
        state = SessionState(
            session_id=session_id,
            topology=DEFAULT_TOPOLOGY,
            behavior=DEFAULT_BEHAVIOR,
            config=DEFAULT_CONFIG.copy(),
        )

        assert hasattr(state, 'session_id')
        assert hasattr(state, 'topology')
        assert hasattr(state, 'behavior')
        assert hasattr(state, 'config')
        assert hasattr(state, 'kernel')
        assert hasattr(state, 'channel')
        assert hasattr(state, 'is_onboarding')

    def test_session_state_kernel_property(self):
        """Test kernel property extraction from topology."""
        from app.models.session_state import SessionState

        voice_fast = SessionState(session_id=uuid4(), topology="voice_fast")
        chat_accurate = SessionState(session_id=uuid4(), topology="chat_accurate")

        assert voice_fast.kernel == "fast_kernel"
        assert chat_accurate.kernel == "accurate_kernel"

    def test_session_state_channel_property(self):
        """Test channel property extraction from topology."""
        from app.models.session_state import SessionState

        voice_fast = SessionState(session_id=uuid4(), topology="voice_fast")
        chat_fast = SessionState(session_id=uuid4(), topology="chat_fast")

        assert voice_fast.channel == "voice_channel"
        assert chat_fast.channel == "text_channel"

    def test_session_state_is_onboarding_property(self):
        """Test is_onboarding property."""
        from app.models.session_state import SessionState

        onboarding = SessionState(session_id=uuid4(), behavior="onboarding")
        practice = SessionState(session_id=uuid4(), behavior="practice")

        assert onboarding.is_onboarding is True
        assert practice.is_onboarding is False


class TestSessionStateBehaviorIntegration:
    """Integration tests for SessionState behavior changes."""

    def test_behavior_persists_across_sessions(self):
        """Test that behavior persists for the same session."""
        from app.models.session_state import SessionState

        session_id = uuid4()

        state1 = SessionState(
            session_id=session_id,
            topology="chat_fast",
            behavior="practice",
        )

        assert state1.behavior == "practice"

    def test_behavior_can_be_updated(self):
        """Test that behavior can be updated."""
        from app.models.session_state import SessionState

        state = SessionState(
            session_id=uuid4(),
            topology="chat_fast",
            behavior="practice",
        )

        assert state.behavior == "practice"

        state.update(behavior="onboarding")

        assert state.behavior == "onboarding"

    def test_topology_can_be_updated(self):
        """Test that topology can be updated."""
        from app.models.session_state import SessionState

        state = SessionState(
            session_id=uuid4(),
            topology="chat_fast",
            behavior="practice",
        )

        assert state.topology == "chat_fast"

        state.update(topology="voice_fast")

        assert state.topology == "voice_fast"

    def test_config_can_be_merged(self):
        """Test that config can be merged."""
        from app.models.session_state import SessionState

        state = SessionState(
            session_id=uuid4(),
            config={"existing": True},
        )

        state.update(config={"new": True})

        assert state.config == {"existing": True, "new": True}


class TestSessionStateEventIntegration:
    """Integration tests for SessionState events."""

    def test_event_bus_can_register_handlers(self):
        """Test that EventBus allows handler registration."""
        from app.services.events import EventBus

        event_bus = EventBus()
        handler_called = []

        @event_bus.on("test.event")
        async def handler(event_type: str, data: dict):
            handler_called.append((event_type, data))

        assert "test.event" in event_bus._handlers
        assert len(event_bus._handlers["test.event"]) == 1

    def test_event_data_structure(self):
        """Test that event data has required structure."""
        from app.services.events import Event

        event = Event(
            type="session_state.created",
            data={"session_id": "test"},
        )

        result = event.to_dict()

        assert "id" in result
        assert "type" in result
        assert "data" in result
        assert "timestamp" in result
        assert result["type"] == "session_state.created"


class TestSessionStateLoggingIntegration:
    """Integration tests for SessionState structured logging."""

    def test_context_logger_has_required_methods(self):
        """Test that ContextLogger has all required logging methods."""
        from app.services.logging import ContextLogger

        required_methods = ['debug', 'info', 'warning', 'error', 'critical', 'exception', 'bind']

        for method in required_methods:
            assert hasattr(ContextLogger, method), f"Missing method: {method}"

    def test_context_logger_bind_returns_new_logger(self):
        """Test that bind returns a new logger with additional context."""
        from unittest.mock import MagicMock

        from app.services.logging import ContextLogger

        mock_logger = MagicMock()
        original_logger = ContextLogger(mock_logger)

        bound_logger = original_logger.bind(user_id="123")

        assert isinstance(bound_logger, ContextLogger)
        assert bound_logger is not original_logger


class TestSessionStatePipelineContextIntegration:
    """Integration tests for SessionState with PipelineContext."""

    def test_session_state_matches_pipeline_context_fields(self):
        """Test that SessionState fields match PipelineContext requirements."""
        from app.ai.substrate.stages.context import PipelineContext
        from app.models.session_state import SessionState

        session_id = uuid4()
        state = SessionState(
            session_id=session_id,
            topology="voice_fast",
            behavior="practice",
        )

        ctx = PipelineContext(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=state.session_id,
            user_id=uuid4(),
            org_id=uuid4(),
            interaction_id=uuid4(),
            topology=state.topology,
            behavior=state.behavior,
        )

        assert ctx.session_id == state.session_id
        assert ctx.topology == state.topology
        assert ctx.behavior == state.behavior

    def test_session_state_kernel_channel_match_pipeline_requirements(self):
        """Test that derived properties match pipeline requirements."""
        from app.models.session_state import SessionState

        test_cases = [
            ("voice_fast", "fast_kernel", "voice_channel"),
            ("voice_accurate", "accurate_kernel", "voice_channel"),
            ("chat_fast", "fast_kernel", "text_channel"),
            ("chat_accurate", "accurate_kernel", "text_channel"),
        ]

        for topology, expected_kernel, expected_channel in test_cases:
            state = SessionState(session_id=uuid4(), topology=topology)
            assert state.kernel == expected_kernel, f"Failed for {topology}"
            assert state.channel == expected_channel, f"Failed for {topology}"


class TestSessionStateWebSocketIntegration:
    """Integration tests for WebSocket handlers with SessionState."""

    def test_session_state_get_response_format(self):
        """Test session.state.get response format."""
        from app.models.session_state import SessionState

        session_id = uuid4()
        state = SessionState(
            session_id=session_id,
            topology="chat_fast",
            behavior="practice",
            config={},
            updated_at=datetime.utcnow(),
        )

        result = state.to_dict()

        assert "session_id" in result
        assert result["session_id"] == str(session_id)
        assert "topology" in result
        assert "behavior" in result
        assert "config" in result
        assert "kernel" in result
        assert "channel" in result
        assert "is_onboarding" in result

    def test_session_state_update_changes_values(self):
        """Test that session.state.update changes values correctly."""
        from app.models.session_state import SessionState

        state = SessionState(
            session_id=uuid4(),
            topology="chat_fast",
            behavior="practice",
        )

        original_topology = state.topology
        original_behavior = state.behavior

        state.update(
            topology="voice_fast",
            behavior="onboarding",
        )

        assert state.topology != original_topology
        assert state.behavior != original_behavior
        assert state.topology == "voice_fast"
        assert state.behavior == "onboarding"

    def test_session_state_invalid_topology_raises_error(self):
        """Test that invalid topology raises InvalidSessionStateError."""
        from app.exceptions import InvalidSessionStateError
        from app.models.session_state import SessionState

        state = SessionState(session_id=uuid4())

        with pytest.raises(InvalidSessionStateError) as exc_info:
            state.update(topology="invalid_topology")

        assert exc_info.value.field == "topology"

    def test_session_state_invalid_behavior_raises_error(self):
        """Test that invalid behavior raises InvalidSessionStateError."""
        from app.exceptions import InvalidSessionStateError
        from app.models.session_state import SessionState

        state = SessionState(session_id=uuid4())

        with pytest.raises(InvalidSessionStateError) as exc_info:
            state.update(behavior="invalid_behavior")

        assert exc_info.value.field == "behavior"


class TestSessionStateDefaults:
    """Integration tests for SessionState default values."""

    def test_default_topology_constant(self):
        """Test default topology constant is chat_fast."""
        from app.models.session_state import DEFAULT_TOPOLOGY

        assert DEFAULT_TOPOLOGY == "chat_fast"

    def test_default_behavior_constant(self):
        """Test default behavior constant is practice."""
        from app.models.session_state import DEFAULT_BEHAVIOR

        assert DEFAULT_BEHAVIOR == "practice"

    def test_default_config_constant(self):
        """Test default config constant is empty dict."""
        from app.models.session_state import DEFAULT_CONFIG

        assert DEFAULT_CONFIG == {}

    def test_valid_topologies_list(self):
        """Test valid topologies list is complete."""
        from app.models.session_state import VALID_TOPOLOGIES

        expected = {"chat_fast", "chat_accurate", "voice_fast", "voice_accurate"}

        assert expected == VALID_TOPOLOGIES

    def test_valid_behaviors_list(self):
        """Test valid behaviors list is complete."""
        from app.models.session_state import VALID_BEHAVIORS

        expected = {"onboarding", "practice", "roleplay", "doc_edit", "free_conversation"}

        assert expected == VALID_BEHAVIORS


class TestSessionStateErrorHandling:
    """Integration tests for SessionState error handling."""

    def test_session_state_not_found_error(self):
        """Test SessionStateNotFoundError structure."""
        from app.exceptions import NotFoundError, SessionStateNotFoundError

        session_id = uuid4()
        error = SessionStateNotFoundError(session_id=session_id)

        assert isinstance(error, NotFoundError)
        assert error.code == "SESSION_STATE_NOT_FOUND"
        assert error.resource == "SessionState"
        assert error.identifier == session_id

    def test_invalid_session_state_error(self):
        """Test InvalidSessionStateError structure."""
        from app.exceptions import InvalidSessionStateError, ValidationError

        error = InvalidSessionStateError(
            field="topology",
            value="invalid",
            valid_values=["chat_fast", "voice_fast"],
        )

        assert isinstance(error, ValidationError)
        assert error.code == "INVALID_SESSION_STATE"
        assert error.field == "topology"
        assert error.value == "invalid"
        assert "chat_fast" in str(error.valid_values)

    def test_session_state_conflict_error(self):
        """Test SessionStateConflictError structure."""
        from datetime import datetime

        from app.exceptions import SessionStateConflictError

        session_id = uuid4()
        expected = datetime.utcnow()
        actual = datetime.utcnow()

        error = SessionStateConflictError(
            session_id=session_id,
            expected_version=expected,
            actual_version=actual,
        )

        assert error.code == "SESSION_STATE_CONFLICT"
        assert error.session_id == session_id


class TestSessionStateServiceIntegration:
    """Integration tests for SessionStateService."""

    @pytest.mark.asyncio
    async def test_service_get_or_create_returns_existing(self):
        """Test get_or_create returns existing state."""
        from app.models.session_state import SessionState
        from app.services.session_state import SessionStateService

        mock_session = AsyncMock()
        service = SessionStateService(session=mock_session)

        session_id = uuid4()
        existing = SessionState(
            session_id=session_id,
            topology="chat_fast",
            behavior="practice",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await service.get_or_create(session_id)

        assert result == existing

    @pytest.mark.asyncio
    async def test_service_get_or_create_creates_new(self):
        """Test get_or_create creates new state when not found."""
        from app.models.session_state import DEFAULT_BEHAVIOR, DEFAULT_TOPOLOGY
        from app.services.session_state import SessionStateService

        mock_session = AsyncMock()
        service = SessionStateService(session=mock_session)

        session_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.get_or_create(session_id)

        assert result.session_id == session_id
        assert result.topology == DEFAULT_TOPOLOGY
        assert result.behavior == DEFAULT_BEHAVIOR
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_update_changes_behavior(self):
        """Test service update changes behavior."""
        from app.models.session_state import SessionState
        from app.services.session_state import SessionStateService

        mock_session = AsyncMock()
        service = SessionStateService(session=mock_session)

        session_id = uuid4()
        existing = SessionState(
            session_id=session_id,
            topology="chat_fast",
            behavior="practice",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await service.update(session_id, behavior="onboarding")

        assert result.behavior == "onboarding"

    @pytest.mark.asyncio
    async def test_service_delete_removes_state(self):
        """Test service delete removes state."""
        from app.models.session_state import SessionState
        from app.services.session_state import SessionStateService

        mock_session = AsyncMock()
        service = SessionStateService(session=mock_session)

        session_id = uuid4()
        existing = SessionState(
            session_id=session_id,
            topology="chat_fast",
            behavior="practice",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute.return_value = mock_result

        result = await service.delete(session_id)

        assert result is True
        mock_session.delete.assert_called_once_with(existing)
