from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:  # pragma: no cover - import-time only
    from app.models.user import User


class UserProfile(Base):
    """Structured user profile for personalising coaching.

    Stores role, goal, contexts and freeform notes for a user. This table is
    1:1 with ``users`` (one profile per user).
    """

    __tablename__ = "user_profiles"

    id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    goal: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Speaking context stored as JSON object, e.g. {"title": str, "description": str}.
    # Historically this field stored a list of tags; existing list data is still JSON-compatible
    # and is handled defensively in services when reading.
    contexts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="profile")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure timestamps are set for test instances
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<UserProfile user_id={self.user_id}>"
