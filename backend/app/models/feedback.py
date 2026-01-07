"""Feedback-related models for message flags and reports.

Matches the schema defined in SPR-006 (feedback_events table).
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:  # pragma: no cover - import-time only
    from app.models.interaction import Interaction
    from app.models.session import Session
    from app.models.user import User


class FeedbackEvent(Base):
    """User feedback on interactions and assistant behaviour.

    Represents both per-message flags (typically on assistant messages) and
    higher-level reports (bug, improvement, "liked it").
    """

    __tablename__ = "feedback_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    interaction_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("interactions.id"),
        nullable=True,
    )
    role: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # 'assistant' | 'user' | None for global reports
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # 'bad_assistant', 'bug', 'improvement', 'like', ...
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )  # Short title / name for the feedback item
    short_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )  # Optional brief explanation
    time_bucket: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # 'just_now', 'earlier_today', 'earlier_this_week', ...
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships (unidirectional for now; backrefs can be added later)
    user: Mapped["User"] = relationship("User")
    session: Mapped["Session | None"] = relationship("Session")
    interaction: Mapped["Interaction | None"] = relationship("Interaction")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure id is set for test instances
        if self.id is None:
            self.id = uuid4()

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return (
            f"<FeedbackEvent id={self.id} user={self.user_id} "
            f"session={self.session_id} category={self.category}>"
        )
