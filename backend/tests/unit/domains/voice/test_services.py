"""Tests for extracted voice service classes (SRP compliance)."""

from unittest.mock import MagicMock
from uuid import uuid4


class TestRecordingManager:
    """Tests for RecordingManager."""

    def test_initialization(self):
        """Test recording manager initializes empty."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()

        assert manager.recording_count == 0
        assert len(manager.active_user_ids) == 0

    def test_start_recording(self):
        """Test starting a new recording."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        session_id = uuid4()
        user_id = uuid4()

        manager.start_recording(
            session_id=session_id,
            user_id=user_id,
            audio_format="webm",
        )

        assert manager.recording_count == 1
        assert manager.has_active_recording(user_id)

        state = manager.get_recording_state(user_id)
        assert state.session_id == session_id
        assert state.user_id == user_id
        assert state.format == "webm"

    def test_start_recording_replaces_existing(self):
        """Test starting a recording replaces existing one for same user."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id = uuid4()
        session_id1 = uuid4()
        session_id2 = uuid4()

        manager.start_recording(session_id=session_id1, user_id=user_id)
        manager.start_recording(session_id=session_id2, user_id=user_id)

        assert manager.recording_count == 1
        state = manager.get_recording_state(user_id)
        assert state.session_id == session_id2

    def test_add_chunk_to_active_recording(self):
        """Test adding chunks to an active recording."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id = uuid4()

        manager.start_recording(session_id=uuid4(), user_id=user_id)
        result = manager.add_chunk(user_id, b"chunk1")

        assert result is True
        chunks = manager.get_audio_chunks(user_id)
        assert len(chunks) == 1
        assert chunks[0] == b"chunk1"

    def test_add_chunk_buffers_before_recording(self):
        """Test that chunks are buffered before recording starts."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id = uuid4()

        # Add chunk before recording starts
        result = manager.add_chunk(user_id, b"pending_chunk")

        assert result is False
        pending = manager.get_pending_chunks(user_id)
        assert pending == [b"pending_chunk"]

    def test_add_chunk_flushes_pending_on_start(self):
        """Test pending chunks are flushed when recording starts."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id = uuid4()

        # Add chunks before recording
        manager.add_chunk(user_id, b"pending1")
        manager.add_chunk(user_id, b"pending2")

        # Start recording
        manager.start_recording(session_id=uuid4(), user_id=user_id)

        # Pending chunks should be in recording
        chunks = manager.get_audio_chunks(user_id)
        assert len(chunks) == 2
        assert chunks[0] == b"pending1"
        assert chunks[1] == b"pending2"

    def test_cancel_recording(self):
        """Test cancelling a recording."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id = uuid4()

        manager.start_recording(session_id=uuid4(), user_id=user_id)
        result = manager.cancel_recording(user_id)

        assert result is True
        assert manager.recording_count == 0
        assert not manager.has_active_recording(user_id)

    def test_cancel_non_existent_recording(self):
        """Test cancelling a non-existent recording returns False."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()

        result = manager.cancel_recording(uuid4())

        assert result is False

    def test_get_recording_state_missing(self):
        """Test getting state for non-existent recording returns None."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()

        result = manager.get_recording_state(uuid4())

        assert result is None

    def test_clear_all_recordings(self):
        """Test clearing all recordings."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id1 = uuid4()
        user_id2 = uuid4()

        manager.start_recording(session_id=uuid4(), user_id=user_id1)
        manager.start_recording(session_id=uuid4(), user_id=user_id2)

        assert manager.recording_count == 2

        manager.clear_all_recordings()

        assert manager.recording_count == 0

    def test_active_user_ids_property(self):
        """Test active_user_ids returns list of user IDs."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id1 = uuid4()
        user_id2 = uuid4()

        manager.start_recording(session_id=uuid4(), user_id=user_id1)
        manager.start_recording(session_id=uuid4(), user_id=user_id2)

        active_ids = manager.active_user_ids
        assert len(active_ids) == 2
        assert user_id1 in active_ids
        assert user_id2 in active_ids

    def test_recording_with_skill_ids(self):
        """Test recording with skill IDs."""
        from app.domains.voice.services import RecordingManager

        manager = RecordingManager()
        user_id = uuid4()
        skill_ids = [uuid4(), uuid4()]

        manager.start_recording(
            session_id=uuid4(),
            user_id=user_id,
            skill_ids=skill_ids,
        )

        state = manager.get_recording_state(user_id)
        assert state.skill_ids == skill_ids


class TestVoicePipelineOrchestrator:
    """Tests for VoicePipelineOrchestrator."""

    def test_initialization(self):
        """Test orchestrator initializes with dependencies."""
        from app.domains.voice.services import VoicePipelineOrchestrator

        mock_db = MagicMock()
        mock_stt = MagicMock()
        mock_stt.name = "deepgram"
        mock_tts = MagicMock()
        mock_tts.name = "google"
        mock_chat = MagicMock()

        orchestrator = VoicePipelineOrchestrator(
            db=mock_db,
            stt_provider=mock_stt,
            tts_provider=mock_tts,
            chat_service=mock_chat,
        )

        assert orchestrator.db is mock_db
        assert orchestrator.stt is mock_stt
        assert orchestrator.tts is mock_tts
        assert orchestrator.chat is mock_chat

    def test_has_cancel_pipeline_method(self):
        """Test orchestrator has cancel_pipeline method."""
        from app.domains.voice.services import VoicePipelineOrchestrator

        mock_db = MagicMock()
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        mock_chat = MagicMock()

        orchestrator = VoicePipelineOrchestrator(
            db=mock_db,
            stt_provider=mock_stt,
            tts_provider=mock_tts,
            chat_service=mock_chat,
        )

        assert hasattr(orchestrator, 'cancel_pipeline')
        assert callable(orchestrator.cancel_pipeline)

    def test_has_process_recording_method(self):
        """Test orchestrator has process_recording method."""
        from app.domains.voice.services import VoicePipelineOrchestrator

        mock_db = MagicMock()
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        mock_chat = MagicMock()

        orchestrator = VoicePipelineOrchestrator(
            db=mock_db,
            stt_provider=mock_stt,
            tts_provider=mock_tts,
            chat_service=mock_chat,
        )

        assert hasattr(orchestrator, 'process_recording')
        assert callable(orchestrator.process_recording)


class TestVoiceServicesModule:
    """Tests for the voice services module exports."""

    def test_exports(self):
        """Test module exports are correct."""
        from app.domains.voice import services

        assert hasattr(services, "RecordingManager")
        assert hasattr(services, "VoicePipelineOrchestrator")

    def test_all_exports_match(self):
        """Test __all__ matches available exports."""
        from app.domains.voice import services

        for name in services.__all__:
            assert hasattr(services, name)

    def test_import_from_domain(self):
        """Test services can be imported from domain."""
        from app.domains.voice import (
            RecordingManager,
            VoicePipelineOrchestrator,
        )

        assert RecordingManager is not None
        assert VoicePipelineOrchestrator is not None


class TestVoicePipelineResult:
    """Tests for VoicePipelineResult dataclass."""

    def test_total_cost(self):
        """Test total_cost property sums all costs."""
        from app.domains.voice.services.orchestrator import VoicePipelineResult

        result = VoicePipelineResult(
            transcript="Hello",
            transcript_confidence=0.9,
            audio_duration_ms=1000,
            response_text="Hi there!",
            llm_latency_ms=150,
            audio_data=b"audio",
            audio_format="pcm",
            tts_duration_ms=500,
            user_message_id=uuid4(),
            assistant_message_id=uuid4(),
            stt_cost=10,
            llm_cost=20,
            tts_cost=30,
        )

        assert result.total_cost == 60

    def test_pipeline_result_creation(self):
        """Test creating a pipeline result."""
        from app.domains.voice.services.orchestrator import VoicePipelineResult

        user_msg_id = uuid4()
        asst_msg_id = uuid4()

        result = VoicePipelineResult(
            transcript="Test transcript",
            transcript_confidence=0.95,
            audio_duration_ms=500,
            response_text="Test response",
            llm_latency_ms=100,
            audio_data=b"test_audio",
            audio_format="pcm",
            tts_duration_ms=300,
            user_message_id=user_msg_id,
            assistant_message_id=asst_msg_id,
            stt_cost=5,
            llm_cost=10,
            tts_cost=15,
        )

        assert result.transcript == "Test transcript"
        assert result.response_text == "Test response"
        assert result.stt_cost == 5
        assert result.total_cost == 30
