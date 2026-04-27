"""Salesbook ORM Records. /Oliviercontribution.

These tables are owned by the salesbook module but registered with the central
``Base.metadata`` so Alembic autogenerate discovers them. Registration happens
via the 1-line ``from ...persistence import *`` added in
``platform/db/migrations.py``.

Conventions match ``platform/db/models.py``:
- String(64) primary keys (uuid4().hex stored as string)
- DateTime(timezone=True) timestamps with ``_utc_now`` default
- String(32) for enum-like fields (validation in Pydantic, not the DB)
- Numeric for decimal money + percentages
- ForeignKey targets ``company_profiles.profile_id`` for the company-level link
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from hello_sales_backend.platform.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SalesbookClientContactExtensionRecord(Base):
    """Sibling of company_profiles — adds primary contact fields not in the base profile."""

    __tablename__ = "salesbook_client_contact_extensions"

    extension_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("company_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    primary_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[str] = mapped_column(Text, nullable=False)
    contact_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    geography: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class SalesbookOnboardingProgressRecord(Base):
    """One row per company tracking 3-phase onboarding completion."""

    __tablename__ = "salesbook_onboarding_progress"

    progress_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("company_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    current_phase: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    phase1_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    phase2_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    phase3_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    phase1_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    phase2_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    phase3_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_completion_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class SalesbookOnboardingResponseRecord(Base):
    """One key-value answer to one of the 114 onboarding questions."""

    __tablename__ = "salesbook_onboarding_responses"
    __table_args__ = (
        UniqueConstraint("profile_id", "question_key", name="uq_salesbook_response_profile_question"),
    )

    response_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("company_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase: Mapped[int] = mapped_column(Integer, nullable=False)
    question_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class SalesbookPipelineDealRecord(Base):
    """One deal in the company's sales pipeline."""

    __tablename__ = "salesbook_pipeline_deals"

    deal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("company_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="new_lead")
    lead_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lead_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assigned_agent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    deal_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    deal_probability: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalesbookEngagementLogRecord(Base):
    """One rep-activity log row — captures WHAT/WHY/RESULT/NEXT."""

    __tablename__ = "salesbook_engagement_logs"

    log_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("company_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("salesbook_pipeline_deals.deal_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    process_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, index=True)


class SalesbookTeamMembershipRecord(Base):
    """One per-org team member with role + capability flags."""

    __tablename__ = "salesbook_team_memberships"

    membership_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("company_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_level: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    can_invite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_export: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_edit_onboarding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


__all__ = [
    "SalesbookClientContactExtensionRecord",
    "SalesbookOnboardingProgressRecord",
    "SalesbookOnboardingResponseRecord",
    "SalesbookPipelineDealRecord",
    "SalesbookEngagementLogRecord",
    "SalesbookTeamMembershipRecord",
]
