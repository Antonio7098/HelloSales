"""Skill and UserSkill models for the skills system."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Skill(Base):
    """Predefined skill in the catalog (e.g., clarity, persuasiveness)."""

    __tablename__ = "skills"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    levels: Mapped[dict] = mapped_column(JSONB, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user_skills: Mapped[list["UserSkill"]] = relationship(
        "UserSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure id is set for test instances
        if self.id is None:
            self.id = uuid4()

    def __repr__(self) -> str:
        return f"<Skill slug={self.slug} title={self.title}>"


class UserSkill(Base):
    """User's progress and tracking state for a specific skill."""

    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skills_user_skill"),)

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
    skill_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    track_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_tracked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    untracked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_skills",
    )
    skill: Mapped["Skill"] = relationship(
        "Skill",
        back_populates="user_skills",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure id and updated_at are set for test instances
        if self.id is None:
            self.id = uuid4()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<UserSkill user_id={self.user_id} skill_id={self.skill_id} level={self.current_level}>"
