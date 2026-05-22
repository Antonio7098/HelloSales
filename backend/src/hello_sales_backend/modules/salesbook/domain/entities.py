"""Salesbook domain entities. /Oliviercontribution.

Pure dataclasses with no SQLAlchemy / Pydantic imports. These represent the
domain concepts; persistence shape lives in infra/persistence.py and transport
shape lives in use_cases/views.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from hello_sales_backend.modules.salesbook.domain.value_objects import (
    ActionType,
    ClientStatus,
    PipelineStage,
    RoleLevel,
)


@dataclass(slots=True, frozen=True)
class ClientContact:
    """Extension fields for a company_profile (the "client" in Phase 4 spec)."""

    extension_id: str
    profile_id: str
    primary_email: str
    contact_name: str
    contact_role: str | None
    phone: str | None
    company_size: str | None
    geography: str | None
    status: ClientStatus
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True, frozen=True)
class OnboardingProgress:
    """Per-company completion tracker for the 3-phase onboarding."""

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


@dataclass(slots=True, frozen=True)
class OnboardingResponse:
    """One key-value answer to one of the 114 onboarding questions."""

    response_id: str
    profile_id: str
    phase: int
    question_key: str
    question_text: str | None
    response_value: str | None
    response_type: str | None
    answered_at: datetime | None
    updated_at: datetime | None


@dataclass(slots=True, frozen=True)
class PipelineDeal:
    """One deal in the company's pipeline."""

    deal_id: str
    profile_id: str
    stage: PipelineStage
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


@dataclass(slots=True, frozen=True)
class EngagementEntry:
    """One sales-log row — captures WHAT, WHY, RESULT, NEXT."""

    log_id: str
    profile_id: str
    deal_id: str | None
    action_type: ActionType
    action_detail: str | None
    action_reason: str | None
    action_result: str | None
    next_step: str | None
    channel: str | None
    agent_id: str | None
    process_version: str | None
    timestamp: datetime


@dataclass(slots=True, frozen=True)
class TeamMember:
    """One per-org team member with role + capability flags."""

    membership_id: str
    profile_id: str
    user_email: str
    role_level: RoleLevel
    can_invite: bool
    can_export: bool
    can_edit_onboarding: bool
    created_at: datetime


__all__ = [
    "ClientContact",
    "OnboardingProgress",
    "OnboardingResponse",
    "PipelineDeal",
    "EngagementEntry",
    "TeamMember",
]
