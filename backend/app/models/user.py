"""User model - Enterprise Edition (WorkOS only)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.organization import OrganizationMembership


class User(Base):
    """User model linked to WorkOS authentication."""

    __tablename__ = "users"

    # auth_subject is the WorkOS user ID, unique in the enterprise context
    __table_args__ = (
        UniqueConstraint(
            "auth_subject",
            name="ux_users_auth_subject",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    # Hardcoded to "workos" for enterprise - no Clerk support
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="workos")
    # WorkOS subject ID from the JWT token
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    accepted_legal_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    accepted_legal_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(  # noqa: F821
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    organization_memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User workos:{self.auth_subject}>"
