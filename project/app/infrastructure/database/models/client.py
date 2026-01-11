"""Client database model."""

from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.client import Client
from app.infrastructure.database.models.base import Base, TimestampMixin


class ClientModel(Base, TimestampMixin):
    """SQLAlchemy model for clients table."""

    __tablename__ = "clients"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Client profile for AI context
    pain_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    goals: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    objection_patterns: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_criteria: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    organization = relationship("OrganizationModel", back_populates="clients")
    sales_scripts = relationship("SalesScriptModel", back_populates="client")
    sales_emails = relationship("SalesEmailModel", back_populates="client")

    def to_entity(self) -> Client:
        """Convert to domain entity."""
        return Client(
            id=self.id,
            org_id=self.org_id,
            name=self.name,
            company=self.company,
            title=self.title,
            industry=self.industry,
            email=self.email,
            pain_points=self.pain_points or [],
            goals=self.goals or [],
            objection_patterns=self.objection_patterns or [],
            communication_style=self.communication_style,
            decision_criteria=self.decision_criteria or [],
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: Client) -> "ClientModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            org_id=entity.org_id,
            name=entity.name,
            company=entity.company,
            title=entity.title,
            industry=entity.industry,
            email=entity.email,
            pain_points=entity.pain_points,
            goals=entity.goals,
            objection_patterns=entity.objection_patterns,
            communication_style=entity.communication_style,
            decision_criteria=entity.decision_criteria,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
