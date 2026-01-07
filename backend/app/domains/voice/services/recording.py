"""RecordingManager for SRP compliance.

Handles audio recording state management for voice conversations.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.voice.service import RecordingState

logger = logging.getLogger("voice")


@dataclass
class RecordingState:
    """State for an active recording."""

    session_id: uuid.UUID
    user_id: uuid.UUID
    format: str = "webm"
    chunks: list[bytes] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    # Optional skill IDs supplied by frontend for this recording
    skill_ids: list[uuid.UUID] | None = None
    # Optional background task for enricher prefetch (to reduce latency)
    enricher_prefetch_task: asyncio.Task | None = None


class RecordingManager:
    """Service for managing audio recording state.

    Responsibilities:
    - Start and cancel recordings
    - Add audio chunks to recordings
    - Buffer chunks before recording starts
    - Retrieve recording state

    This service is stateless - it only manages the recording state dictionaries.
    """

    # Threshold for forcing TTS even without sentence-ending punctuation
    # (kept for compatibility, though typically used by TTS logic)
    EARLY_TTS_CHAR_THRESHOLD = 80

    def __init__(self) -> None:
        """Initialize recording manager."""
        # Active recordings by user_id
        self._recordings: dict[uuid.UUID, RecordingState] = {}
        # Pending chunks buffered before recording starts
        self._pending_chunks: dict[uuid.UUID, list[bytes]] = {}

    def start_recording(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        audio_format: str = "webm",
        skill_ids: list[uuid.UUID] | None = None,
        enricher_prefetch_task: asyncio.Task | None = None,
    ) -> None:
        """Start a new recording for a user.

        Args:
            session_id: Session ID
            user_id: User ID
            audio_format: Audio format (webm, wav, mp3, m4a)
            skill_ids: Optional skill IDs for this recording
            enricher_prefetch_task: Optional background task for enricher prefetch
        """
        # Cancel any existing recording for this user
        if user_id in self._recordings:
            logger.warning(
                "Replacing existing recording",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "old_session_id": str(self._recordings[user_id].session_id),
                    "new_session_id": str(session_id),
                },
            )

        self._recordings[user_id] = RecordingState(
            session_id=session_id,
            user_id=user_id,
            format=audio_format,
            skill_ids=skill_ids,
            enricher_prefetch_task=enricher_prefetch_task,
        )

        # Flush any chunks that arrived before start_recording completed
        pending = self._pending_chunks.pop(user_id, None)
        if pending:
            self._recordings[user_id].chunks.extend(pending)

        logger.info(
            "Recording started",
            extra={
                "service": "voice",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "format": audio_format,
            },
        )

    def add_chunk(self, user_id: uuid.UUID, chunk_data: bytes) -> bool:
        """Add an audio chunk to the current recording.

        Args:
            user_id: User ID
            chunk_data: Raw audio bytes

        Returns:
            True if chunk was added, False if no active recording
        """
        if user_id not in self._recordings:
            # Buffer chunks until start_recording finishes
            if user_id not in self._pending_chunks:
                self._pending_chunks[user_id] = []
            self._pending_chunks[user_id].append(chunk_data)
            logger.info(
                "Chunk buffered (no active recording yet)",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "chunk_size": len(chunk_data),
                    "pending_count": len(self._pending_chunks[user_id]),
                },
            )
            return False

        self._recordings[user_id].chunks.append(chunk_data)

        logger.debug(
            "Audio chunk added",
            extra={
                "service": "voice",
                "user_id": str(user_id),
                "chunk_size": len(chunk_data),
                "total_chunks": len(self._recordings[user_id].chunks),
            },
        )

        return True

    def cancel_recording(self, user_id: uuid.UUID) -> bool:
        """Cancel the current recording for a user.

        Args:
            user_id: User ID

        Returns:
            True if recording was cancelled, False if none active
        """
        if user_id not in self._recordings:
            return False

        recording = self._recordings.pop(user_id)

        logger.info(
            "Recording cancelled",
            extra={
                "service": "voice",
                "user_id": str(user_id),
                "session_id": str(recording.session_id),
                "chunks_discarded": len(recording.chunks),
            },
        )

        return True

    def get_recording_state(self, user_id: uuid.UUID) -> RecordingState | None:
        """Get the current recording state for a user.

        Args:
            user_id: User ID

        Returns:
            RecordingState if recording exists, None otherwise
        """
        return self._recordings.get(user_id)

    def get_audio_chunks(self, user_id: uuid.UUID) -> list[bytes] | None:
        """Get the audio chunks for a user's recording.

        Args:
            user_id: User ID

        Returns:
            List of audio chunks if recording exists, None otherwise
        """
        recording = self._recordings.get(user_id)
        if recording:
            return recording.chunks
        return None

    def get_pending_chunks(self, user_id: uuid.UUID) -> list[bytes] | None:
        """Get pending chunks buffered before recording started.

        Args:
            user_id: User ID

        Returns:
            List of pending chunks if any, None otherwise
        """
        return self._pending_chunks.get(user_id)

    def has_active_recording(self, user_id: uuid.UUID) -> bool:
        """Check if user has an active recording.

        Args:
            user_id: User ID

        Returns:
            True if recording exists, False otherwise
        """
        return user_id in self._recordings

    def clear_all_recordings(self) -> None:
        """Clear all recordings (useful for testing/cleanup)."""
        count = len(self._recordings)
        self._recordings.clear()
        self._pending_chunks.clear()
        logger.info(
            f"Cleared {count} recordings",
            extra={"service": "voice", "count": count},
        )

    @property
    def active_user_ids(self) -> list[uuid.UUID]:
        """Get list of user IDs with active recordings."""
        return list(self._recordings.keys())

    @property
    def recording_count(self) -> int:
        """Get the number of active recordings."""
        return len(self._recordings)
