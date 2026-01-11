"""Company profile entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass
class CompanyProfile:
    """Detailed company information for sales context.

    One-to-one relationship with Organization.
    Provides context for AI-generated sales content.
    """

    id: UUID
    org_id: UUID

    # Company basics
    industry: str | None = None
    company_size: str | None = None  # 'startup', '1-10', '10-50', '50-200', '200-1000', '1000+'
    headquarters_city: str | None = None
    headquarters_country: str | None = None
    website: str | None = None

    # Sales operations
    sales_team_size: int | None = None
    average_deal_size_usd: int | None = None
    sales_cycle_days: int | None = None
    target_market: str | None = None
    market_segments: list[str] = field(default_factory=list)  # ['SMB', 'Enterprise', 'Mid-market']

    # Product/service context
    primary_products: list[str] = field(default_factory=list)
    sales_regions: list[str] = field(default_factory=list)
    deal_types: list[str] = field(default_factory=list)  # 'outbound', 'inbound', 'renewal', 'expansion'

    # Sales maturity & process
    sales_methodology: str | None = None  # 'consultative', 'transactional', 'solution-selling'
    sales_stage: str | None = None  # 'early', 'growing', 'mature', 'enterprise'
    typical_buying_cycle: dict[str, Any] = field(default_factory=dict)

    # Competitive context
    main_competitors: list[str] = field(default_factory=list)
    competitive_advantages: list[str] = field(default_factory=list)
    unique_selling_points: list[str] = field(default_factory=list)

    # Additional context
    company_description: str | None = None
    notes: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_context_dict(self) -> dict[str, Any]:
        """Convert to dict for LLM context injection."""
        ctx = {}
        if self.industry:
            ctx["industry"] = self.industry
        if self.company_size:
            ctx["company_size"] = self.company_size
        if self.target_market:
            ctx["target_market"] = self.target_market
        if self.market_segments:
            ctx["market_segments"] = self.market_segments
        if self.sales_methodology:
            ctx["sales_methodology"] = self.sales_methodology
        if self.competitive_advantages:
            ctx["competitive_advantages"] = self.competitive_advantages
        if self.unique_selling_points:
            ctx["unique_selling_points"] = self.unique_selling_points
        if self.company_description:
            ctx["company_description"] = self.company_description
        return ctx
