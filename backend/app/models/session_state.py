"""SessionState model for pipeline configuration.

This module provides the SessionState model that stores mutable pipeline
configuration per session. It includes topology, behavior, and an extensible
config blob for future flags.

Design Principles:
- Single source of truth: Load once when session opens, update on change
- Mutable by design: Update in place, no history bloat
- Survives reload: Client reconnects, fetches current state
- Lightweight: One row per session, one read on open

Usage:
    # Load session state when opening session
    state = await session_state_service.get(session_id)
    topology = state.topology  # e.g., "voice_fast"
    behavior = state.behavior  # e.g., "practice"

    # Update behavior via settings
    await session_state_service.update(
        session_id,
        behavior="onboarding",
        emit_event=True
    )

    # Pipeline uses the state
    pipeline_ctx = PipelineContext(
        topology=session_state.topology,
        behavior=session_state.behavior,
        config=session_state.config,
    )
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

if TYPE_CHECKING:
    pass


# Default values for new session states
DEFAULT_TOPOLOGY = "chat_fast"
DEFAULT_BEHAVIOR = "practice"
DEFAULT_CONFIG: dict[str, Any] = {}

# Valid topology values (kernel + channel combinations)
VALID_TOPOLOGIES = frozenset([
    "chat_fast",
    "chat_accurate",
    "voice_fast",
    "voice_accurate",
])

# Valid behavior values
VALID_BEHAVIORS = frozenset([
    "onboarding",
    "practice",
    "roleplay",
    "doc_edit",
    "free_conversation",
])


class SessionState(Base):
    """Session state model for pipeline configuration.

    Stores the mutable configuration that controls how pipelines run
    for a given session. Includes topology, behavior, and extensible config.

    Attributes:
        session_id: Foreign key to the Session (1:1 relationship)
        topology: Pipeline topology (e.g., "voice_fast", "chat_accurate")
        behavior: Session behavior/mode (e.g., "practice", "onboarding")
        config: JSON blob for extensible configuration flags
        updated_at: Timestamp of last modification

    Relationships:
        session: The parent Session this state belongs to

    Examples:
        >>> state = SessionState(
        ...     session_id=UUID("1234-5678"),
        ...     topology="voice_fast",
        ...     behavior="practice"
        ... )
        >>> state.topology
        'voice_fast'
    """

    __tablename__ = "session_state"

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    topology: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_TOPOLOGY,
        nullable=False,
        comment="Pipeline topology (kernel + channel combination)",
    )
    behavior: Mapped[str] = mapped_column(
        String(50),
        default=DEFAULT_BEHAVIOR,
        nullable=False,
        comment="Session behavior/mode (e.g., practice, onboarding)",
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {},
        nullable=False,
        comment="Extensible configuration blob for future flags",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Timestamp of last modification",
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<SessionState session={self.session_id} "
            f"topology={self.topology} behavior={self.behavior}>"
        )

    @property
    def kernel(self) -> str:
        """Extract kernel name from topology.

        Returns:
            Kernel name (e.g., "fast_kernel" from "voice_fast")

        Examples:
            >>> state = SessionState(topology="voice_fast")
            >>> state.kernel
            'fast_kernel'
            >>> state = SessionState(topology="chat_accurate")
            >>> state.kernel
            'accurate_kernel'
        """
        parts = self.topology.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in ("fast", "accurate"):
            return f"{parts[1]}_kernel"
        return "fast_kernel"  # Default fallback

    @property
    def channel(self) -> str:
        """Extract channel name from topology.

        Returns:
            Channel name (e.g., "voice_channel" from "voice_fast")

        Examples:
            >>> state = SessionState(topology="voice_fast")
            >>> state.channel
            'voice_channel'
            >>> state = SessionState(topology="chat_fast")
            >>> state.channel
            'text_channel'
        """
        parts = self.topology.rsplit("_", 1)
        if parts[0] == "voice":
            return "voice_channel"
        return "text_channel"

    @property
    def is_onboarding(self) -> bool:
        """Check if session is in onboarding mode.

        Returns:
            True if behavior is 'onboarding'

        Examples:
            >>> state = SessionState(behavior="onboarding")
            >>> state.is_onboarding
            True
            >>> state = SessionState(behavior="practice")
            >>> state.is_onboarding
            False
        """
        return self.behavior == "onboarding"

    def update(
        self,
        topology: str | None = None,
        behavior: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Update session state values.

        Args:
            topology: New topology value (optional)
            behavior: New behavior value (optional)
            config: New config dict (optional, merged with existing)

        Raises:
            ValueError: If topology or behavior value is invalid

        Examples:
            >>> state = SessionState()
            >>> state.update(behavior="onboarding")
            >>> state.behavior
            'onboarding'
            >>> state.update(config={"flag_enabled": True})
            >>> state.config["flag_enabled"]
            True
        """
        from app.exceptions import InvalidSessionStateError

        if topology is not None and topology not in VALID_TOPOLOGIES:
            raise InvalidSessionStateError(
                field="topology",
                value=topology,
                valid_values=list(VALID_TOPOLOGIES),
            )

        if behavior is not None and behavior not in VALID_BEHAVIORS:
            raise InvalidSessionStateError(
                field="behavior",
                value=behavior,
                valid_values=list(VALID_BEHAVIORS),
            )

        if topology is not None:
            self.topology = topology
        if behavior is not None:
            self.behavior = behavior
        if config is not None:
            # Merge config dicts, new values override existing
            self.config = {**self.config, **config}

        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization

        Examples:
            >>> state = SessionState(
            ...     session_id=UUID("1234-5678"),
            ...     topology="voice_fast",
            ...     behavior="practice"
            ... )
            >>> state.to_dict()["topology"]
            'voice_fast'
        """
        return {
            "session_id": str(self.session_id),
            "topology": self.topology,
            "behavior": self.behavior,
            "config": self.config,
            "updated_at": self.updated_at.isoformat(),
            "kernel": self.kernel,
            "channel": self.channel,
            "is_onboarding": self.is_onboarding,
        }


__all__ = [
    "SessionState",
    "DEFAULT_TOPOLOGY",
    "DEFAULT_BEHAVIOR",
    "DEFAULT_CONFIG",
    "VALID_TOPOLOGIES",
    "VALID_BEHAVIORS",
]
