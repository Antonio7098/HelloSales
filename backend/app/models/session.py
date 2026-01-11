"""Session model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.interaction import Interaction
    from app.models.observability import SummaryState
    from app.models.summary import SessionSummary
    from app.models.user import User


class Session(Base):
    """Conversation session model."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_cost_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    is_onboarding: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    interactions: Mapped[list["Interaction"]] = relationship(
        "Interaction",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Interaction.created_at",
    )
    summary_state: Mapped["SummaryState | None"] = relationship(
        "SummaryState",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    summaries: Mapped[list["SessionSummary"]] = relationship(
        "SessionSummary",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionSummary.version",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure defaults are set for test instances
        if self.id is None:
            self.id = uuid4()
        if self.interaction_count is None:
            self.interaction_count = 0
        if self.total_cost_cents is None:
            self.total_cost_cents = 0
        if self.state is None:
            self.state = "active"

    def __repr__(self) -> str:
        return f"<Session {self.id} user={self.user_id} state={self.state}>"

    def end_session(self) -> None:
        """Mark session as ended."""
        self.state = "ended"
        self.ended_at = datetime.utcnow()
        if self.started_at:
            self.duration_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)
