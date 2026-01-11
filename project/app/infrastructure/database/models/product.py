"""Product database model."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.product import Product
from app.infrastructure.database.models.base import Base, TimestampMixin


class ProductModel(Base, TimestampMixin):
    """SQLAlchemy model for products table."""

    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Product details for AI context
    key_features: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    pricing_info: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitive_advantages: Mapped[str | None] = mapped_column(Text, nullable=True)
    use_cases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    organization = relationship("OrganizationModel", back_populates="products")
    sales_scripts = relationship("SalesScriptModel", back_populates="product")
    sales_emails = relationship("SalesEmailModel", back_populates="product")

    def to_entity(self) -> Product:
        """Convert to domain entity."""
        return Product(
            id=self.id,
            org_id=self.org_id,
            name=self.name,
            description=self.description,
            category=self.category,
            key_features=self.key_features or [],
            pricing_info=self.pricing_info or {},
            target_audience=self.target_audience,
            competitive_advantages=self.competitive_advantages,
            use_cases=self.use_cases or [],
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: Product) -> "ProductModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            org_id=entity.org_id,
            name=entity.name,
            description=entity.description,
            category=entity.category,
            key_features=entity.key_features,
            pricing_info=entity.pricing_info,
            target_audience=entity.target_audience,
            competitive_advantages=entity.competitive_advantages,
            use_cases=entity.use_cases,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
