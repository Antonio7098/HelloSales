"""Interaction database model."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.interaction import Interaction
from app.infrastructure.database.models.base import Base


class InteractionModel(Base):
    """SQLAlchemy model for interactions table."""

    __tablename__ = "interactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Content
    input_type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audio
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Provider call references
    llm_provider_call_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    stt_provider_call_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    tts_provider_call_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Ordering
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    session = relationship("SessionModel", back_populates="interactions")

    def to_entity(self) -> Interaction:
        """Convert to domain entity."""
        return Interaction(
            id=self.id,
            session_id=self.session_id,
            role=self.role,  # type: ignore
            sequence_number=self.sequence_number,
            content=self.content,
            input_type=self.input_type,  # type: ignore
            transcript=self.transcript,
            audio_url=self.audio_url,
            audio_duration_ms=self.audio_duration_ms,
            llm_provider_call_id=self.llm_provider_call_id,
            stt_provider_call_id=self.stt_provider_call_id,
            tts_provider_call_id=self.tts_provider_call_id,
            message_id=self.message_id,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: Interaction) -> "InteractionModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            session_id=entity.session_id,
            role=entity.role,
            sequence_number=entity.sequence_number,
            content=entity.content,
            input_type=entity.input_type,
            transcript=entity.transcript,
            audio_url=entity.audio_url,
            audio_duration_ms=entity.audio_duration_ms,
            llm_provider_call_id=entity.llm_provider_call_id,
            stt_provider_call_id=entity.stt_provider_call_id,
            tts_provider_call_id=entity.tts_provider_call_id,
            message_id=entity.message_id,
            created_at=entity.created_at,
        )
