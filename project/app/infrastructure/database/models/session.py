"""Session, summary, and summary state database models."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.session import Session, SessionSummary, SummaryState
from app.infrastructure.database.models.base import Base, TimestampMixin


class SessionModel(Base, TimestampMixin):
    """SQLAlchemy model for sessions table."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # State
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metrics
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metadata
    session_type: Mapped[str] = mapped_column(String(50), nullable=False, default="chat")
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    user = relationship("UserModel", back_populates="sessions")
    organization = relationship("OrganizationModel", back_populates="sessions")
    interactions = relationship(
        "InteractionModel", back_populates="session", order_by="InteractionModel.sequence_number"
    )
    summaries = relationship(
        "SessionSummaryModel", back_populates="session", order_by="SessionSummaryModel.version"
    )
    summary_state = relationship("SummaryStateModel", back_populates="session", uselist=False)

    def to_entity(self) -> Session:
        """Convert to domain entity."""
        return Session(
            id=self.id,
            user_id=self.user_id,
            org_id=self.org_id,
            state=self.state,  # type: ignore
            started_at=self.started_at,
            ended_at=self.ended_at,
            interaction_count=self.interaction_count,
            total_cost_cents=self.total_cost_cents,
            duration_ms=self.duration_ms,
            session_type=self.session_type,  # type: ignore
            metadata=self.metadata or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: Session) -> "SessionModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            user_id=entity.user_id,
            org_id=entity.org_id,
            state=entity.state,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            interaction_count=entity.interaction_count,
            total_cost_cents=entity.total_cost_cents,
            duration_ms=entity.duration_ms,
            session_type=entity.session_type,
            metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class SessionSummaryModel(Base):
    """SQLAlchemy model for session_summaries table."""

    __tablename__ = "session_summaries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    cutoff_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    session = relationship("SessionModel", back_populates="summaries")

    __table_args__ = (
        UniqueConstraint("session_id", "version", name="session_summary_version_unique"),
    )

    def to_entity(self) -> SessionSummary:
        """Convert to domain entity."""
        return SessionSummary(
            id=self.id,
            session_id=self.session_id,
            version=self.version,
            summary_text=self.summary_text,
            cutoff_sequence=self.cutoff_sequence,
            token_count=self.token_count,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: SessionSummary) -> "SessionSummaryModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            session_id=entity.session_id,
            version=entity.version,
            summary_text=entity.summary_text,
            cutoff_sequence=entity.cutoff_sequence,
            token_count=entity.token_count,
            created_at=entity.created_at,
        )


class SummaryStateModel(Base):
    """SQLAlchemy model for summary_states table."""

    __tablename__ = "summary_states"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    turns_since_summary: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_cutoff_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_summary_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    session = relationship("SessionModel", back_populates="summary_state")

    def to_entity(self) -> SummaryState:
        """Convert to domain entity."""
        return SummaryState(
            id=self.id,
            session_id=self.session_id,
            turns_since_summary=self.turns_since_summary,
            last_cutoff_sequence=self.last_cutoff_sequence,
            last_summary_at=self.last_summary_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: SummaryState) -> "SummaryStateModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            session_id=entity.session_id,
            turns_since_summary=entity.turns_since_summary,
            last_cutoff_sequence=entity.last_cutoff_sequence,
            last_summary_at=entity.last_summary_at,
            updated_at=entity.updated_at,
        )
