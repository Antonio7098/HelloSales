"""Session summary model for context compression."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SessionSummary(Base):
    """Immutable summary records for conversation context compression.

    Each summary captures the conversation up to a certain point,
    allowing older messages to be dropped while retaining context.
    Version numbers increment per session as new summaries are created.
    """

    __tablename__ = "session_summaries"
    __table_args__ = (
        UniqueConstraint("session_id", "version", name="uq_session_summaries_session_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Incrementing version per session",
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The compressed summary text",
    )
    cutoff_idx: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Interaction index this summary covers up to",
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Token count of this summary",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    session: Mapped["Session"] = relationship(  # noqa: F821
        back_populates="summaries",
    )

    def __repr__(self) -> str:
        return (
            f"<SessionSummary(id={self.id}, session_id={self.session_id}, version={self.version})>"
        )
