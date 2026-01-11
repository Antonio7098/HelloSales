"""User database model."""

from uuid import UUID, uuid4

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.user import User
from app.infrastructure.database.models.base import Base, TimestampMixin


class UserModel(Base, TimestampMixin):
    """SQLAlchemy model for users table."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="workos")
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    memberships = relationship("OrganizationMembershipModel", back_populates="user")
    sessions = relationship("SessionModel", back_populates="user")

    __table_args__ = (
        UniqueConstraint("auth_provider", "auth_subject", name="users_auth_unique"),
    )

    def to_entity(self) -> User:
        """Convert to domain entity."""
        return User(
            id=self.id,
            auth_provider=self.auth_provider,
            auth_subject=self.auth_subject,
            email=self.email,
            display_name=self.display_name,
            avatar_url=self.avatar_url,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: User) -> "UserModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            auth_provider=entity.auth_provider,
            auth_subject=entity.auth_subject,
            email=entity.email,
            display_name=entity.display_name,
            avatar_url=entity.avatar_url,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
