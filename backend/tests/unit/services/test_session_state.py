"""Unit tests for SessionState model and service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.exceptions import (
    InvalidSessionStateError,
    SessionStateNotFoundError,
)
from app.models.session_state import (
    DEFAULT_BEHAVIOR,
    DEFAULT_CONFIG,
    DEFAULT_TOPOLOGY,
    VALID_BEHAVIORS,
    VALID_TOPOLOGIES,
    SessionState,
)


class TestSessionStateModel:
    """Tests for SessionState model."""

    def test_default_values_with_explicit_defaults(self):
        """Test that model can be created with default values explicitly."""
        session_id = uuid4()
        state = SessionState(
            session_id=session_id,
            topology=DEFAULT_TOPOLOGY,
            behavior=DEFAULT_BEHAVIOR,
            config=DEFAULT_CONFIG.copy(),
        )
        assert state.topology == DEFAULT_TOPOLOGY
        assert state.behavior == DEFAULT_BEHAVIOR
        assert state.config == DEFAULT_CONFIG

    def test_custom_values(self):
        """Test that custom values are set correctly."""
        state = SessionState(
            session_id=uuid4(),
            topology="voice_fast",
            behavior="onboarding",
            config={"flag": True},
        )
        assert state.topology == "voice_fast"
        assert state.behavior == "onboarding"
        assert state.config == {"flag": True}

    def test_kernel_property_fast(self):
        """Test kernel property extraction for fast kernel."""
        state = SessionState(session_id=uuid4(), topology="voice_fast")
        assert state.kernel == "fast_kernel"

    def test_kernel_property_accurate(self):
        """Test kernel property extraction for accurate kernel."""
        state = SessionState(session_id=uuid4(), topology="chat_accurate")
        assert state.kernel == "accurate_kernel"

    def test_kernel_property_unknown(self):
        """Test kernel property returns default for unknown topology."""
        state = SessionState(session_id=uuid4(), topology="unknown")
        assert state.kernel == "fast_kernel"

    def test_channel_property_voice(self):
        """Test channel property extraction for voice."""
        state = SessionState(session_id=uuid4(), topology="voice_fast")
        assert state.channel == "voice_channel"

    def test_channel_property_chat(self):
        """Test channel property extraction for chat."""
        state = SessionState(session_id=uuid4(), topology="chat_fast")
        assert state.channel == "text_channel"

    def test_is_onboarding_true(self):
        """Test is_onboarding returns True for onboarding behavior."""
        state = SessionState(session_id=uuid4(), behavior="onboarding")
        assert state.is_onboarding is True

    def test_is_onboarding_false(self):
        """Test is_onboarding returns False for non-onboarding behavior."""
        state = SessionState(session_id=uuid4(), behavior="practice")
        assert state.is_onboarding is False

    def test_update_topology(self):
        """Test updating topology."""
        state = SessionState(session_id=uuid4(), topology="chat_fast")
        state.update(topology="voice_accurate")
        assert state.topology == "voice_accurate"

    def test_update_behavior(self):
        """Test updating behavior."""
        state = SessionState(session_id=uuid4(), behavior="practice")
        state.update(behavior="onboarding")
        assert state.behavior == "onboarding"

    def test_update_config_merge(self):
        """Test that config updates are merged."""
        state = SessionState(
            session_id=uuid4(),
            config={"existing": True},
        )
        state.update(config={"new": True})
        assert state.config == {"existing": True, "new": True}

    def test_update_config_override(self):
        """Test that new config values override existing ones."""
        state = SessionState(
            session_id=uuid4(),
            config={"key": "old"},
        )
        state.update(config={"key": "new"})
        assert state.config["key"] == "new"

    def test_update_multiple_fields(self):
        """Test updating multiple fields at once."""
        state = SessionState(session_id=uuid4())
        state.update(topology="voice_fast", behavior="onboarding")
        assert state.topology == "voice_fast"
        assert state.behavior == "onboarding"

    def test_update_invalid_topology(self):
        """Test that invalid topology raises error."""
        state = SessionState(session_id=uuid4())
        with pytest.raises(InvalidSessionStateError) as exc_info:
            state.update(topology="invalid_topology")
        assert exc_info.value.field == "topology"
        assert exc_info.value.value == "invalid_topology"

    def test_update_invalid_behavior(self):
        """Test that invalid behavior raises error."""
        state = SessionState(session_id=uuid4())
        with pytest.raises(InvalidSessionStateError) as exc_info:
            state.update(behavior="invalid_behavior")
        assert exc_info.value.field == "behavior"
        assert exc_info.value.value == "invalid_behavior"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        session_id = uuid4()
        now = datetime.utcnow()
        state = SessionState(
            session_id=session_id,
            topology="voice_fast",
            behavior="practice",
            config={"key": "value"},
            updated_at=now,
        )
        result = state.to_dict()
        assert result["session_id"] == str(session_id)
        assert result["topology"] == "voice_fast"
        assert result["behavior"] == "practice"
        assert result["config"] == {"key": "value"}
        assert result["kernel"] == "fast_kernel"
        assert result["channel"] == "voice_channel"
        assert result["is_onboarding"] is False

    def test_repr(self):
        """Test string representation."""
        session_id = uuid4()
        state = SessionState(
            session_id=session_id,
            topology="voice_fast",
            behavior="practice",
        )
        repr_str = repr(state)
        assert "SessionState" in repr_str
        assert str(session_id) in repr_str
        assert "voice_fast" in repr_str
        assert "practice" in repr_str


class TestSessionStateConstants:
    """Tests for SessionState constants."""

    def test_default_topology(self):
        """Test default topology value."""
        assert DEFAULT_TOPOLOGY == "chat_fast"

    def test_default_behavior(self):
        """Test default behavior value."""
        assert DEFAULT_BEHAVIOR == "practice"

    def test_default_config(self):
        """Test default config value."""
        assert DEFAULT_CONFIG == {}

    def test_valid_topologies(self):
        """Test valid topologies set."""
        assert "chat_fast" in VALID_TOPOLOGIES
        assert "chat_accurate" in VALID_TOPOLOGIES
        assert "voice_fast" in VALID_TOPOLOGIES
        assert "voice_accurate" in VALID_TOPOLOGIES
        assert len(VALID_TOPOLOGIES) == 4

    def test_valid_behaviors(self):
        """Test valid behaviors set."""
        assert "onboarding" in VALID_BEHAVIORS
        assert "practice" in VALID_BEHAVIORS
        assert "roleplay" in VALID_BEHAVIORS
        assert "doc_edit" in VALID_BEHAVIORS
        assert "free_conversation" in VALID_BEHAVIORS
        assert len(VALID_BEHAVIORS) == 5


class TestSessionStateService:
    """Tests for SessionStateService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a SessionStateService with mock session."""
        from app.services.session_state import SessionStateService
        return SessionStateService(session=mock_session)

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, service, mock_session):
        """Test get_or_create returns existing state."""
        session_id = uuid4()
        existing_state = SessionState(
            session_id=session_id,
            topology="voice_fast",
            behavior="practice",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_state
        mock_session.execute.return_value = mock_result

        result = await service.get_or_create(session_id)

        assert result == existing_state
        assert result.topology == "voice_fast"

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, service, mock_session):
        """Test get_or_create creates new state when not found."""
        session_id = uuid4()

        mock_not_found = MagicMock()
        mock_not_found.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_not_found

        result = await service.get_or_create(session_id)

        assert result.session_id == session_id
        assert result.topology == DEFAULT_TOPOLOGY
        assert result.behavior == DEFAULT_BEHAVIOR
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_get_not_found(self, service, mock_session):
        """Test get raises error when state not found."""
        session_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(SessionStateNotFoundError):
            await service.get(session_id)

    @pytest.mark.asyncio
    async def test_update_behavior(self, service, mock_session):
        """Test updating behavior."""
        session_id = uuid4()
        state = SessionState(session_id=session_id, behavior="practice")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = state
        mock_session.execute.return_value = mock_result

        result = await service.update(session_id, behavior="onboarding")

        assert result.behavior == "onboarding"

    @pytest.mark.asyncio
    async def test_update_topology(self, service, mock_session):
        """Test updating topology."""
        session_id = uuid4()
        state = SessionState(session_id=session_id, topology="chat_fast")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = state
        mock_session.execute.return_value = mock_result

        result = await service.update(session_id, topology="voice_fast")

        assert result.topology == "voice_fast"

    @pytest.mark.asyncio
    async def test_update_invalid_topology(self, service, mock_session):
        """Test updating with invalid topology raises error."""
        session_id = uuid4()
        state = SessionState(session_id=session_id, topology="chat_fast")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = state
        mock_session.execute.return_value = mock_result

        with pytest.raises(InvalidSessionStateError) as exc_info:
            await service.update(session_id, topology="invalid")

        assert exc_info.value.field == "topology"

    @pytest.mark.asyncio
    async def test_update_invalid_behavior(self, service, mock_session):
        """Test updating with invalid behavior raises error."""
        session_id = uuid4()
        state = SessionState(session_id=session_id, behavior="practice")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = state
        mock_session.execute.return_value = mock_result

        with pytest.raises(InvalidSessionStateError) as exc_info:
            await service.update(session_id, behavior="invalid")

        assert exc_info.value.field == "behavior"

    @pytest.mark.asyncio
    async def test_delete(self, service, mock_session):
        """Test deleting session state."""
        session_id = uuid4()
        state = SessionState(session_id=session_id, topology="voice_fast", behavior="practice")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = state
        mock_session.execute.return_value = mock_result

        result = await service.delete(session_id)

        assert result is True
        mock_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_behavior(self, service, mock_session):
        """Test listing states by behavior."""
        states = [
            SessionState(session_id=uuid4(), behavior="practice"),
            SessionState(session_id=uuid4(), behavior="practice"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = states
        mock_session.execute.return_value = mock_result

        result = await service.list_by_behavior("practice")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_by_behavior_invalid(self, service, _mock_session):
        """Test listing by invalid behavior raises error."""
        with pytest.raises(InvalidSessionStateError):
            await service.list_by_behavior("invalid_behavior")

    @pytest.mark.asyncio
    async def test_list_by_topology(self, service, mock_session):
        """Test listing states by topology."""
        states = [
            SessionState(session_id=uuid4(), topology="voice_fast"),
            SessionState(session_id=uuid4(), topology="voice_fast"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = states
        mock_session.execute.return_value = mock_result

        result = await service.list_by_topology("voice_fast")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_by_topology_invalid(self, service, _mock_session):
        """Test listing by invalid topology raises error."""
        with pytest.raises(InvalidSessionStateError):
            await service.list_by_topology("invalid_topology")

    @pytest.mark.asyncio
    async def test_create_raises_if_exists(self, service, mock_session):
        """Test create raises error if state already exists."""
        session_id = uuid4()
        existing_state = SessionState(
            session_id=session_id,
            topology="voice_fast",
            behavior="practice",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_state
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc_info:
            await service.create(session_id)

        assert "already exists" in str(exc_info.value)
