"""Views and requests for company profile data."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyProfileUpsertRequest(BaseModel):
    """Request body for replacing the company profile."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1)
    industry: str | None = None
    target_customer: str | None = None
    pricing_model: str | None = None
    sales_team_size: int | None = Field(default=None, ge=0)
    crm_tool: str | None = None
    average_deal_size: str | None = None
    average_sales_cycle: str | None = None
    primary_sales_constraint: str | None = None
    quarterly_sales_focus: str | None = None


class CompanyProfileView(CompanyProfileUpsertRequest):
    """Company profile response."""

    profile_id: str
    created_at: datetime
    updated_at: datetime


class ProductCreateRequest(BaseModel):
    """Request body for creating a product."""

    model_config = ConfigDict(extra="forbid")

    product_name: str = Field(min_length=1)
    product_description: str | None = None
    target_customer: str | None = None
    primary_use_case: str | None = None
    pricing_model: str | None = None
    list_price: str | None = None
    sales_cycle: str | None = None
    deal_size: str | None = None
    revenue_share: str | None = None
    is_primary: bool = False


class ProductUpdateRequest(BaseModel):
    """Request body for partially updating a product."""

    model_config = ConfigDict(extra="forbid")

    product_name: str | None = Field(default=None, min_length=1)
    product_description: str | None = None
    target_customer: str | None = None
    primary_use_case: str | None = None
    pricing_model: str | None = None
    list_price: str | None = None
    sales_cycle: str | None = None
    deal_size: str | None = None
    revenue_share: str | None = None
    is_primary: bool | None = None


class ProductView(ProductCreateRequest):
    """Product response."""

    product_id: str
    company_profile_id: str
    created_at: datetime
    updated_at: datetime


class CompanyContextView(BaseModel):
    """Combined company context response."""

    model_config = ConfigDict(extra="forbid")

    company_profile: CompanyProfileView | None
    products: list[ProductView] = Field(default_factory=list)
