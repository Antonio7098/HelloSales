"""Company profile database model."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.company_profile import CompanyProfile
from app.infrastructure.database.models.base import Base, TimestampMixin


class CompanyProfileModel(Base, TimestampMixin):
    """SQLAlchemy model for company_profiles table."""

    __tablename__ = "company_profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Company basics
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)
    headquarters_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    headquarters_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sales operations
    sales_team_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_deal_size_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sales_cycle_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_market: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_segments: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Product/service context
    primary_products: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    sales_regions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    deal_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Sales maturity & process
    sales_methodology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sales_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    typical_buying_cycle: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Competitive context
    main_competitors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    competitive_advantages: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    unique_selling_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Additional context
    company_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization = relationship("OrganizationModel", back_populates="company_profile")

    def to_entity(self) -> CompanyProfile:
        """Convert to domain entity."""
        return CompanyProfile(
            id=self.id,
            org_id=self.org_id,
            industry=self.industry,
            company_size=self.company_size,
            headquarters_city=self.headquarters_city,
            headquarters_country=self.headquarters_country,
            website=self.website,
            sales_team_size=self.sales_team_size,
            average_deal_size_usd=self.average_deal_size_usd,
            sales_cycle_days=self.sales_cycle_days,
            target_market=self.target_market,
            market_segments=self.market_segments or [],
            primary_products=self.primary_products or [],
            sales_regions=self.sales_regions or [],
            deal_types=self.deal_types or [],
            sales_methodology=self.sales_methodology,
            sales_stage=self.sales_stage,
            typical_buying_cycle=self.typical_buying_cycle or {},
            main_competitors=self.main_competitors or [],
            competitive_advantages=self.competitive_advantages or [],
            unique_selling_points=self.unique_selling_points or [],
            company_description=self.company_description,
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: CompanyProfile) -> "CompanyProfileModel":
        """Create from domain entity."""
        return cls(
            id=entity.id,
            org_id=entity.org_id,
            industry=entity.industry,
            company_size=entity.company_size,
            headquarters_city=entity.headquarters_city,
            headquarters_country=entity.headquarters_country,
            website=entity.website,
            sales_team_size=entity.sales_team_size,
            average_deal_size_usd=entity.average_deal_size_usd,
            sales_cycle_days=entity.sales_cycle_days,
            target_market=entity.target_market,
            market_segments=entity.market_segments,
            primary_products=entity.primary_products,
            sales_regions=entity.sales_regions,
            deal_types=entity.deal_types,
            sales_methodology=entity.sales_methodology,
            sales_stage=entity.sales_stage,
            typical_buying_cycle=entity.typical_buying_cycle,
            main_competitors=entity.main_competitors,
            competitive_advantages=entity.competitive_advantages,
            unique_selling_points=entity.unique_selling_points,
            company_description=entity.company_description,
            notes=entity.notes,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
