"""Salesbook views — Pydantic request and response DTOs. /Oliviercontribution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ────────────────────────────────────────────────────────────────────────────
# Client contact extension (sibling of company_profile)
# ────────────────────────────────────────────────────────────────────────────


class ClientContactUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_email: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    contact_name: str = Field(min_length=1)
    contact_role: str | None = None
    phone: str | None = None
    company_size: str | None = None
    geography: str | None = None
    status: str = Field(default="active")


class ClientContactView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extension_id: str
    profile_id: str
    primary_email: str
    contact_name: str
    contact_role: str | None
    phone: str | None
    company_size: str | None
    geography: str | None
    status: str
    created_at: datetime
    updated_at: datetime


# ────────────────────────────────────────────────────────────────────────────
# Onboarding
# ────────────────────────────────────────────────────────────────────────────


class OnboardingProgressView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    progress_id: str
    profile_id: str
    current_phase: int
    phase1_pct: Decimal
    phase2_pct: Decimal
    phase3_pct: Decimal
    phase1_completed_at: datetime | None
    phase2_completed_at: datetime | None
    phase3_completed_at: datetime | None
    total_completion_pct: Decimal
    updated_at: datetime


class OnboardingResponseSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: int = Field(ge=1, le=3)
    question_key: str = Field(min_length=1)
    response_value: str | None = None
    response_type: str | None = None
    question_text: str | None = None


class OnboardingBatchSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: int = Field(ge=1, le=3)
    responses: list[OnboardingResponseSubmit]


class OnboardingResponseView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_id: str
    profile_id: str
    phase: int
    question_key: str
    question_text: str | None
    response_value: str | None
    response_type: str | None
    answered_at: datetime | None
    updated_at: datetime


# ────────────────────────────────────────────────────────────────────────────
# Pipeline (deals)
# ────────────────────────────────────────────────────────────────────────────


class PipelineDealCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str = Field(default="new_lead")
    lead_source: str | None = None
    lead_score: int = Field(default=0, ge=0, le=100)
    assigned_agent: str | None = None
    deal_value: Decimal = Field(default=Decimal("0.00"))
    deal_probability: Decimal = Field(default=Decimal("0.00"))
    next_action: str | None = None
    next_action_date: date | None = None


class PipelineDealUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str | None = None
    lead_source: str | None = None
    lead_score: int | None = Field(default=None, ge=0, le=100)
    assigned_agent: str | None = None
    deal_value: Decimal | None = None
    deal_probability: Decimal | None = None
    next_action: str | None = None
    next_action_date: date | None = None
    close_reason: str | None = None


class PipelineDealView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deal_id: str
    profile_id: str
    stage: str
    lead_source: str | None
    lead_score: int
    assigned_agent: str | None
    deal_value: Decimal
    deal_probability: Decimal
    next_action: str | None
    next_action_date: date | None
    stage_entered_at: datetime
    created_at: datetime
    closed_at: datetime | None
    close_reason: str | None


# ────────────────────────────────────────────────────────────────────────────
# Engagement log (sales log)
# ────────────────────────────────────────────────────────────────────────────


class EngagementLogCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    deal_id: str | None = None
    action_type: str
    action_detail: str | None = None
    action_reason: str | None = None
    action_result: str | None = None
    next_step: str | None = None
    channel: str | None = None
    agent_id: str | None = None
    process_version: str | None = None


class EngagementLogView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: str
    profile_id: str
    deal_id: str | None
    action_type: str
    action_detail: str | None
    action_reason: str | None
    action_result: str | None
    next_step: str | None
    channel: str | None
    agent_id: str | None
    process_version: str | None
    timestamp: datetime


# ────────────────────────────────────────────────────────────────────────────
# Team membership
# ────────────────────────────────────────────────────────────────────────────


class TeamMembershipCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_email: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role_level: str = Field(default="user")
    can_invite: bool = False
    can_export: bool = False
    can_edit_onboarding: bool = True


class TeamMembershipView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: str
    profile_id: str
    user_email: str
    role_level: str
    can_invite: bool
    can_export: bool
    can_edit_onboarding: bool
    created_at: datetime


# ────────────────────────────────────────────────────────────────────────────
# Exhaustive view — drives the searchable salesbook viewer in 6.1
# ────────────────────────────────────────────────────────────────────────────


class SalesbookExhaustiveOnboardingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: int
    section: str | None
    question_key: str
    question_text: str | None
    response_value: str | None
    response_type: str | None
    answered_at: datetime | None


class SalesbookExhaustiveProductEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    product_name: str
    product_description: str | None
    target_customer: str | None
    primary_use_case: str | None
    pricing_model: str | None
    list_price: str | None
    sales_cycle: str | None
    deal_size: str | None
    revenue_share: str | None
    is_primary: bool


class SalesbookExhaustiveView(BaseModel):
    """Flat aggregate of everything the system knows about a company. Drives the
    searchable salesbook viewer (frontend uses fuzzy search across these arrays)."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    contact: ClientContactView | None
    progress: OnboardingProgressView | None
    onboarding: list[SalesbookExhaustiveOnboardingEntry]
    products: list[SalesbookExhaustiveProductEntry]
    pipeline: list[PipelineDealView]
    engagement: list[EngagementLogView]
    team: list[TeamMembershipView]
    comments: list[SalesbookCommentView] = Field(default_factory=list)
    pinned: list[SalesbookPinView] = Field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────────
# Moderation — comments + pinned content
# ────────────────────────────────────────────────────────────────────────────


class SalesbookCommentCreateRequest(BaseModel):
    """Rep posts a comment/opinion against a salesbook target (typically an onboarding response)."""

    model_config = ConfigDict(extra="forbid")

    target_type: str = Field(default="onboarding_response")
    target_id: str = Field(min_length=1)
    author_email: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    body: str = Field(min_length=1)


class SalesbookCommentApproveRequest(BaseModel):
    """Admin approves or rejects a pending comment."""

    model_config = ConfigDict(extra="forbid")

    approved_by: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    decision: str = Field(pattern=r"^(approved|rejected)$")


class SalesbookCommentView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment_id: str
    profile_id: str
    target_type: str
    target_id: str
    author_email: str
    body: str
    status: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SalesbookPinRequest(BaseModel):
    """Admin pins (or unpins) a salesbook entry to feature it at the top."""

    model_config = ConfigDict(extra="forbid")

    target_type: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    pinned_by: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SalesbookPinView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin_id: str
    profile_id: str
    target_type: str
    target_id: str
    pinned_by: str
    pinned_at: datetime


@dataclass
class SalesbookDiagnosticsSummary:
    active_count: int
    total_count: int
    recent_runs: list[EngagementLogView]


__all__ = [
    "ClientContactUpsertRequest",
    "ClientContactView",
    "OnboardingProgressView",
    "OnboardingResponseSubmit",
    "OnboardingBatchSubmit",
    "OnboardingResponseView",
    "PipelineDealCreateRequest",
    "PipelineDealUpdateRequest",
    "PipelineDealView",
    "EngagementLogCreateRequest",
    "EngagementLogView",
    "TeamMembershipCreateRequest",
    "TeamMembershipView",
    "SalesbookExhaustiveOnboardingEntry",
    "SalesbookExhaustiveProductEntry",
    "SalesbookExhaustiveView",
    "SalesbookCommentCreateRequest",
    "SalesbookCommentApproveRequest",
    "SalesbookCommentView",
    "SalesbookPinRequest",
    "SalesbookPinView",
    "SalesbookDiagnosticsSummary",
]


# Resolve forward refs for SalesbookExhaustiveView fields
SalesbookExhaustiveView.model_rebuild()
