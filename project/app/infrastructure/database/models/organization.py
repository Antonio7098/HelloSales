"""Organization and membership database models."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.organization import Organization, OrganizationMembership
from app.infrastructure.database.models.base import Base, TimestampMixin


class OrganizationModel(Base, TimestampMixin):
    """SQLAlchemy model for organizations table."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    memberships = relationship("OrganizationMembershipModel", back_populates="organization")
    company_profile = relationship(
        "CompanyProfileModel", back_populates="organization", uselist=False
    )
    sessions = relationship("SessionModel", back_populates="organization")
    products = relationship("ProductModel", back_populates="organization")
    clients = relationship("ClientModel", back_populates="organization")
    sales_scripts = relationship("SalesScriptModel", back_populates="organization")
    sales_emails = relationship("SalesEmailModel", back_populates="organization")

    def to_entity(self) -> Organization:
        """Convert to domain entity."""
        return Organization(
            id=self.id,
            external_id=self.external_id,
            name=self.name,
            slug=self.slug,
            settings=self.settings or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: Organization) -> "OrganizationModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            external_id=entity.external_id,
            name=entity.name,
            slug=entity.slug,
            settings=entity.settings,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


class OrganizationMembershipModel(Base, TimestampMixin):
    """SQLAlchemy model for organization_memberships table."""

    __tablename__ = "organization_memberships"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    permissions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    user = relationship("UserModel", back_populates="memberships")
    organization = relationship("OrganizationModel", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="org_membership_unique"),
    )

    def to_entity(self) -> OrganizationMembership:
        """Convert to domain entity."""
        return OrganizationMembership(
            id=self.id,
            user_id=self.user_id,
            organization_id=self.organization_id,
            role=self.role,
            permissions=self.permissions or {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: OrganizationMembership) -> "OrganizationMembershipModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            user_id=entity.user_id,
            organization_id=entity.organization_id,
            role=entity.role,
            permissions=entity.permissions,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
