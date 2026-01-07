"""Interaction model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.observability import ProviderCall
    from app.models.session import Session


class Interaction(Base):
    """Individual message in a conversation."""

    __tablename__ = "interactions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )  # 'user' | 'assistant'
    input_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )  # 'text' | 'voice' (null for assistant)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Links to provider_calls entries for this interaction
    llm_provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    stt_provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )
    tts_provider_call_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("provider_calls.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="interactions")
    llm_provider_call: Mapped["ProviderCall | None"] = relationship(
        "ProviderCall",
        foreign_keys="Interaction.llm_provider_call_id",
    )
    stt_provider_call: Mapped["ProviderCall | None"] = relationship(
        "ProviderCall",
        foreign_keys="Interaction.stt_provider_call_id",
    )
    tts_provider_call: Mapped["ProviderCall | None"] = relationship(
        "ProviderCall",
        foreign_keys="Interaction.tts_provider_call_id",
    )
    provider_calls: Mapped[list["ProviderCall"]] = relationship(
        "ProviderCall",
        back_populates="interaction",
        foreign_keys="ProviderCall.interaction_id",
    )

    def __repr__(self) -> str:
        return f"<Interaction {self.id} role={self.role}>"
