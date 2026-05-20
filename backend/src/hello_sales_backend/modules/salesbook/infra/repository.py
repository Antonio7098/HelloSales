"""SqlAlchemy salesbook repositories. /Oliviercontribution.

Each repository implements a Port from use_cases/ports.py, talks to its ORM
Record class from infra/persistence.py, and converts to/from the Pydantic
Views in use_cases/views.py. Mirrors the pattern in
modules/company_profile/infra/repository.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import delete, select

if TYPE_CHECKING:
    from hello_sales_backend.modules.company_profile import CompanyProfileService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.modules.salesbook.infra.persistence import (
    SalesbookClientContactExtensionRecord,
    SalesbookCommentRecord,
    SalesbookEngagementLogRecord,
    SalesbookOnboardingProgressRecord,
    SalesbookOnboardingResponseRecord,
    SalesbookPinnedRecord,
    SalesbookPipelineDealRecord,
    SalesbookTeamMembershipRecord,
)
from hello_sales_backend.modules.salesbook.use_cases.ports import (
    SalesbookClientContactRepositoryPort,
    SalesbookCommentRepositoryPort,
    SalesbookEngagementRepositoryPort,
    SalesbookOnboardingRepositoryPort,
    SalesbookPinRepositoryPort,
    SalesbookPipelineRepositoryPort,
    SalesbookProductReadPort,
    SalesbookTeamMembershipRepositoryPort,
)
from hello_sales_backend.modules.salesbook.use_cases.views import (
    ClientContactUpsertRequest,
    ClientContactView,
    EngagementLogCreateRequest,
    EngagementLogView,
    OnboardingProgressView,
    OnboardingResponseSubmit,
    OnboardingResponseView,
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
    PipelineDealView,
    SalesbookCommentCreateRequest,
    SalesbookCommentView,
    SalesbookExhaustiveProductEntry,
    SalesbookPinRequest,
    SalesbookPinView,
    TeamMembershipCreateRequest,
    TeamMembershipView,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid4().hex


# ────────────────────────────────────────────────────────────────────────────
# View converters
# ────────────────────────────────────────────────────────────────────────────


def _contact_view(r: SalesbookClientContactExtensionRecord) -> ClientContactView:
    return ClientContactView(
        extension_id=r.extension_id,
        profile_id=r.profile_id,
        primary_email=r.primary_email,
        contact_name=r.contact_name,
        contact_role=r.contact_role,
        phone=r.phone,
        company_size=r.company_size,
        geography=r.geography,
        status=r.status,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _progress_view(r: SalesbookOnboardingProgressRecord) -> OnboardingProgressView:
    return OnboardingProgressView(
        progress_id=r.progress_id,
        profile_id=r.profile_id,
        current_phase=r.current_phase,
        phase1_pct=r.phase1_pct,
        phase2_pct=r.phase2_pct,
        phase3_pct=r.phase3_pct,
        phase1_completed_at=r.phase1_completed_at,
        phase2_completed_at=r.phase2_completed_at,
        phase3_completed_at=r.phase3_completed_at,
        total_completion_pct=r.total_completion_pct,
        updated_at=r.updated_at,
    )


def _response_view(r: SalesbookOnboardingResponseRecord) -> OnboardingResponseView:
    return OnboardingResponseView(
        response_id=r.response_id,
        profile_id=r.profile_id,
        phase=r.phase,
        question_key=r.question_key,
        question_text=r.question_text,
        response_value=r.response_value,
        response_type=r.response_type,
        answered_at=r.answered_at,
        updated_at=r.updated_at,
    )


def _deal_view(r: SalesbookPipelineDealRecord) -> PipelineDealView:
    return PipelineDealView(
        deal_id=r.deal_id,
        profile_id=r.profile_id,
        stage=r.stage,
        lead_source=r.lead_source,
        lead_score=r.lead_score,
        assigned_agent=r.assigned_agent,
        deal_value=r.deal_value,
        deal_probability=r.deal_probability,
        next_action=r.next_action,
        next_action_date=r.next_action_date,
        stage_entered_at=r.stage_entered_at,
        created_at=r.created_at,
        closed_at=r.closed_at,
        close_reason=r.close_reason,
    )


def _engagement_view(r: SalesbookEngagementLogRecord) -> EngagementLogView:
    return EngagementLogView(
        log_id=r.log_id,
        profile_id=r.profile_id,
        deal_id=r.deal_id,
        action_type=r.action_type,
        action_detail=r.action_detail,
        action_reason=r.action_reason,
        action_result=r.action_result,
        next_step=r.next_step,
        channel=r.channel,
        agent_id=r.agent_id,
        process_version=r.process_version,
        timestamp=r.timestamp,
    )


def _team_view(r: SalesbookTeamMembershipRecord) -> TeamMembershipView:
    return TeamMembershipView(
        membership_id=r.membership_id,
        profile_id=r.profile_id,
        user_email=r.user_email,
        role_level=r.role_level,
        can_invite=r.can_invite,
        can_export=r.can_export,
        can_edit_onboarding=r.can_edit_onboarding,
        created_at=r.created_at,
    )


# ────────────────────────────────────────────────────────────────────────────
# Repositories
# ────────────────────────────────────────────────────────────────────────────


class SqlAlchemySalesbookClientContactRepository(SalesbookClientContactRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def get(self, profile_id: str) -> ClientContactView | None:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookClientContactExtensionRecord).where(
                    SalesbookClientContactExtensionRecord.profile_id == profile_id
                )
            )
            return _contact_view(r) if r else None

    async def upsert(self, profile_id: str, request: ClientContactUpsertRequest) -> ClientContactView:
        async with self._sf() as session:
            now = _now()
            r = await session.scalar(
                select(SalesbookClientContactExtensionRecord).where(
                    SalesbookClientContactExtensionRecord.profile_id == profile_id
                )
            )
            if r is None:
                r = SalesbookClientContactExtensionRecord(
                    extension_id=_new_id(),
                    profile_id=profile_id,
                    primary_email=request.primary_email,
                    contact_name=request.contact_name,
                    contact_role=request.contact_role,
                    phone=request.phone,
                    company_size=request.company_size,
                    geography=request.geography,
                    status=request.status,
                    created_at=now,
                    updated_at=now,
                )
                session.add(r)
            else:
                r.primary_email = request.primary_email
                r.contact_name = request.contact_name
                r.contact_role = request.contact_role
                r.phone = request.phone
                r.company_size = request.company_size
                r.geography = request.geography
                r.status = request.status
                r.updated_at = now
            await session.commit()
            await session.refresh(r)
            return _contact_view(r)


class SqlAlchemySalesbookOnboardingRepository(SalesbookOnboardingRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def get_progress(self, profile_id: str) -> OnboardingProgressView:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookOnboardingProgressRecord).where(
                    SalesbookOnboardingProgressRecord.profile_id == profile_id
                )
            )
            if r is None:
                now = _now()
                r = SalesbookOnboardingProgressRecord(
                    progress_id=_new_id(),
                    profile_id=profile_id,
                    current_phase=1,
                    phase1_pct=Decimal("0.00"),
                    phase2_pct=Decimal("0.00"),
                    phase3_pct=Decimal("0.00"),
                    total_completion_pct=Decimal("0.00"),
                    updated_at=now,
                )
                session.add(r)
                await session.commit()
                await session.refresh(r)
            return _progress_view(r)

    async def upsert_progress(
        self, profile_id: str, *, current_phase: int,
        phase1_pct: float, phase2_pct: float, phase3_pct: float, total_pct: float,
        phase1_completed_at_iso: str | None,
        phase2_completed_at_iso: str | None,
        phase3_completed_at_iso: str | None,
    ) -> OnboardingProgressView:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookOnboardingProgressRecord).where(
                    SalesbookOnboardingProgressRecord.profile_id == profile_id
                )
            )
            if r is None:
                r = SalesbookOnboardingProgressRecord(
                    progress_id=_new_id(),
                    profile_id=profile_id,
                )
                session.add(r)
            r.current_phase = current_phase
            r.phase1_pct = Decimal(str(phase1_pct))
            r.phase2_pct = Decimal(str(phase2_pct))
            r.phase3_pct = Decimal(str(phase3_pct))
            r.total_completion_pct = Decimal(str(total_pct))
            r.phase1_completed_at = datetime.fromisoformat(phase1_completed_at_iso) if phase1_completed_at_iso else None
            r.phase2_completed_at = datetime.fromisoformat(phase2_completed_at_iso) if phase2_completed_at_iso else None
            r.phase3_completed_at = datetime.fromisoformat(phase3_completed_at_iso) if phase3_completed_at_iso else None
            r.updated_at = _now()
            await session.commit()
            await session.refresh(r)
            return _progress_view(r)

    async def list_responses(
        self, profile_id: str, phase: int | None = None
    ) -> list[OnboardingResponseView]:
        async with self._sf() as session:
            q = select(SalesbookOnboardingResponseRecord).where(
                SalesbookOnboardingResponseRecord.profile_id == profile_id
            )
            if phase is not None:
                q = q.where(SalesbookOnboardingResponseRecord.phase == phase)
            rows = list(await session.scalars(q.order_by(
                SalesbookOnboardingResponseRecord.phase,
                SalesbookOnboardingResponseRecord.question_key,
            )))
            return [_response_view(r) for r in rows]

    async def upsert_response(
        self, profile_id: str, request: OnboardingResponseSubmit
    ) -> OnboardingResponseView:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookOnboardingResponseRecord).where(
                    SalesbookOnboardingResponseRecord.profile_id == profile_id,
                    SalesbookOnboardingResponseRecord.question_key == request.question_key,
                )
            )
            now = _now()
            if r is None:
                r = SalesbookOnboardingResponseRecord(
                    response_id=_new_id(),
                    profile_id=profile_id,
                    phase=request.phase,
                    question_key=request.question_key,
                    question_text=request.question_text,
                    response_value=request.response_value,
                    response_type=request.response_type,
                    answered_at=now,
                    updated_at=now,
                )
                session.add(r)
            else:
                r.phase = request.phase
                r.question_text = request.question_text
                r.response_value = request.response_value
                r.response_type = request.response_type
                r.updated_at = now
            await session.commit()
            await session.refresh(r)
            return _response_view(r)

    async def count_answered_by_phase(self, profile_id: str) -> dict[int, int]:
        async with self._sf() as session:
            rows = list(await session.scalars(
                select(SalesbookOnboardingResponseRecord).where(
                    SalesbookOnboardingResponseRecord.profile_id == profile_id,
                )
            ))
            out = {1: 0, 2: 0, 3: 0}
            for r in rows:
                if r.response_value not in (None, ""):
                    out[r.phase] = out.get(r.phase, 0) + 1
            return out


class SqlAlchemySalesbookPipelineRepository(SalesbookPipelineRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def list_deals(self, profile_id: str) -> list[PipelineDealView]:
        async with self._sf() as session:
            rows = list(await session.scalars(
                select(SalesbookPipelineDealRecord)
                .where(SalesbookPipelineDealRecord.profile_id == profile_id)
                .order_by(SalesbookPipelineDealRecord.created_at.desc())
            ))
            return [_deal_view(r) for r in rows]

    async def get_deal(self, deal_id: str) -> PipelineDealView | None:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookPipelineDealRecord).where(SalesbookPipelineDealRecord.deal_id == deal_id)
            )
            return _deal_view(r) if r else None

    async def create_deal(
        self, profile_id: str, request: PipelineDealCreateRequest
    ) -> PipelineDealView:
        async with self._sf() as session:
            now = _now()
            r = SalesbookPipelineDealRecord(
                deal_id=_new_id(),
                profile_id=profile_id,
                stage=request.stage,
                lead_source=request.lead_source,
                lead_score=request.lead_score,
                assigned_agent=request.assigned_agent,
                deal_value=request.deal_value,
                deal_probability=request.deal_probability,
                next_action=request.next_action,
                next_action_date=request.next_action_date,
                stage_entered_at=now,
                created_at=now,
            )
            session.add(r)
            await session.commit()
            await session.refresh(r)
            return _deal_view(r)

    async def update_deal(
        self, deal_id: str, request: PipelineDealUpdateRequest
    ) -> PipelineDealView:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookPipelineDealRecord).where(SalesbookPipelineDealRecord.deal_id == deal_id)
            )
            if r is None:
                raise KeyError(f"deal not found: {deal_id}")
            now = _now()
            old_stage = r.stage
            if request.stage is not None:
                r.stage = request.stage
                if request.stage != old_stage:
                    r.stage_entered_at = now
                if request.stage in ("closed_won", "closed_lost") and r.closed_at is None:
                    r.closed_at = now
            if request.lead_source is not None:
                r.lead_source = request.lead_source
            if request.lead_score is not None:
                r.lead_score = request.lead_score
            if request.assigned_agent is not None:
                r.assigned_agent = request.assigned_agent
            if request.deal_value is not None:
                r.deal_value = request.deal_value
            if request.deal_probability is not None:
                r.deal_probability = request.deal_probability
            if request.next_action is not None:
                r.next_action = request.next_action
            if request.next_action_date is not None:
                r.next_action_date = request.next_action_date
            if request.close_reason is not None:
                r.close_reason = request.close_reason
            await session.commit()
            await session.refresh(r)
            return _deal_view(r)


class SqlAlchemySalesbookEngagementRepository(SalesbookEngagementRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create(self, request: EngagementLogCreateRequest) -> EngagementLogView:
        async with self._sf() as session:
            r = SalesbookEngagementLogRecord(
                log_id=_new_id(),
                profile_id=request.profile_id,
                deal_id=request.deal_id,
                action_type=request.action_type,
                action_detail=request.action_detail,
                action_reason=request.action_reason,
                action_result=request.action_result,
                next_step=request.next_step,
                channel=request.channel,
                agent_id=request.agent_id,
                process_version=request.process_version,
                timestamp=_now(),
            )
            session.add(r)
            await session.commit()
            await session.refresh(r)
            return _engagement_view(r)

    async def list_for_profile(
        self, profile_id: str, deal_id: str | None = None, limit: int = 100
    ) -> list[EngagementLogView]:
        async with self._sf() as session:
            q = select(SalesbookEngagementLogRecord).where(
                SalesbookEngagementLogRecord.profile_id == profile_id
            )
            if deal_id is not None:
                q = q.where(SalesbookEngagementLogRecord.deal_id == deal_id)
            rows = list(await session.scalars(
                q.order_by(SalesbookEngagementLogRecord.timestamp.desc()).limit(limit)
            ))
            return [_engagement_view(r) for r in rows]

    async def list_all(self, limit: int = 200) -> list[EngagementLogView]:
        async with self._sf() as session:
            rows = list(await session.scalars(
                select(SalesbookEngagementLogRecord)
                .order_by(SalesbookEngagementLogRecord.timestamp.desc())
                .limit(limit)
            ))
            return [_engagement_view(r) for r in rows]


class SqlAlchemySalesbookTeamMembershipRepository(SalesbookTeamMembershipRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def list_team(self, profile_id: str) -> list[TeamMembershipView]:
        async with self._sf() as session:
            rows = list(await session.scalars(
                select(SalesbookTeamMembershipRecord)
                .where(SalesbookTeamMembershipRecord.profile_id == profile_id)
                .order_by(SalesbookTeamMembershipRecord.created_at)
            ))
            return [_team_view(r) for r in rows]

    async def add(self, profile_id: str, request: TeamMembershipCreateRequest) -> TeamMembershipView:
        async with self._sf() as session:
            r = SalesbookTeamMembershipRecord(
                membership_id=_new_id(),
                profile_id=profile_id,
                user_email=request.user_email,
                role_level=request.role_level,
                can_invite=request.can_invite,
                can_export=request.can_export,
                can_edit_onboarding=request.can_edit_onboarding,
                created_at=_now(),
            )
            session.add(r)
            await session.commit()
            await session.refresh(r)
            return _team_view(r)

    async def remove(self, membership_id: str) -> None:
        async with self._sf() as session:
            await session.execute(
                delete(SalesbookTeamMembershipRecord).where(
                    SalesbookTeamMembershipRecord.membership_id == membership_id
                )
            )
            await session.commit()


# ────────────────────────────────────────────────────────────────────────────
# Product read adapter — wraps CompanyProfileService for the exhaustive view
# ────────────────────────────────────────────────────────────────────────────


class CompanyProfileProductReadAdapter(SalesbookProductReadPort):
    """Adapts modules.company_profile.CompanyProfileService.list_products() to the salesbook port."""

    def __init__(self, company_profile_service: CompanyProfileService) -> None:
        self._svc = company_profile_service

    async def list_products_for_profile(self, profile_id: str) -> list[SalesbookExhaustiveProductEntry]:
        # company_profile is a singleton-per-deployment in the existing code; list_products()
        # returns products bound to whatever profile exists. The salesbook treats this as
        # "products for the active profile". If that ever changes, swap this adapter.
        products = await self._svc.list_products()
        return [
            SalesbookExhaustiveProductEntry(
                product_id=p.product_id,
                product_name=p.product_name,
                product_description=p.product_description,
                target_customer=p.target_customer,
                primary_use_case=p.primary_use_case,
                pricing_model=p.pricing_model,
                list_price=p.list_price,
                sales_cycle=p.sales_cycle,
                deal_size=p.deal_size,
                revenue_share=p.revenue_share,
                is_primary=p.is_primary,
            )
            for p in products
        ]


def _comment_view(r: SalesbookCommentRecord) -> SalesbookCommentView:
    return SalesbookCommentView(
        comment_id=r.comment_id,
        profile_id=r.profile_id,
        target_type=r.target_type,
        target_id=r.target_id,
        author_email=r.author_email,
        body=r.body,
        status=r.status,
        approved_by=r.approved_by,
        approved_at=r.approved_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _pin_view(r: SalesbookPinnedRecord) -> SalesbookPinView:
    return SalesbookPinView(
        pin_id=r.pin_id,
        profile_id=r.profile_id,
        target_type=r.target_type,
        target_id=r.target_id,
        pinned_by=r.pinned_by,
        pinned_at=r.pinned_at,
    )


class SqlAlchemySalesbookCommentRepository(SalesbookCommentRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def create(
        self, profile_id: str, request: SalesbookCommentCreateRequest
    ) -> SalesbookCommentView:
        async with self._sf() as session:
            now = _now()
            r = SalesbookCommentRecord(
                comment_id=_new_id(),
                profile_id=profile_id,
                target_type=request.target_type,
                target_id=request.target_id,
                author_email=request.author_email,
                body=request.body,
                status="pending",
                created_at=now,
                updated_at=now,
            )
            session.add(r)
            await session.commit()
            await session.refresh(r)
            return _comment_view(r)

    async def list_for_profile(
        self, profile_id: str, status: str | None = None,
        target_id: str | None = None,
    ) -> list[SalesbookCommentView]:
        async with self._sf() as session:
            q = select(SalesbookCommentRecord).where(SalesbookCommentRecord.profile_id == profile_id)
            if status is not None:
                q = q.where(SalesbookCommentRecord.status == status)
            if target_id is not None:
                q = q.where(SalesbookCommentRecord.target_id == target_id)
            rows = list(await session.scalars(q.order_by(SalesbookCommentRecord.created_at.desc())))
            return [_comment_view(r) for r in rows]

    async def get(self, comment_id: str) -> SalesbookCommentView | None:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookCommentRecord).where(SalesbookCommentRecord.comment_id == comment_id)
            )
            return _comment_view(r) if r else None

    async def update_status(
        self, comment_id: str, *, status: str, approved_by: str | None,
    ) -> SalesbookCommentView:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookCommentRecord).where(SalesbookCommentRecord.comment_id == comment_id)
            )
            if r is None:
                raise KeyError(f"comment not found: {comment_id}")
            r.status = status
            r.approved_by = approved_by
            r.approved_at = _now() if status == "approved" else None
            r.updated_at = _now()
            await session.commit()
            await session.refresh(r)
            return _comment_view(r)


class SqlAlchemySalesbookPinRepository(SalesbookPinRepositoryPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def list_for_profile(self, profile_id: str) -> list[SalesbookPinView]:
        async with self._sf() as session:
            rows = list(await session.scalars(
                select(SalesbookPinnedRecord)
                .where(SalesbookPinnedRecord.profile_id == profile_id)
                .order_by(SalesbookPinnedRecord.pinned_at.desc())
            ))
            return [_pin_view(r) for r in rows]

    async def upsert(
        self, profile_id: str, request: SalesbookPinRequest
    ) -> SalesbookPinView:
        async with self._sf() as session:
            r = await session.scalar(
                select(SalesbookPinnedRecord).where(
                    SalesbookPinnedRecord.profile_id == profile_id,
                    SalesbookPinnedRecord.target_type == request.target_type,
                    SalesbookPinnedRecord.target_id == request.target_id,
                )
            )
            if r is None:
                r = SalesbookPinnedRecord(
                    pin_id=_new_id(),
                    profile_id=profile_id,
                    target_type=request.target_type,
                    target_id=request.target_id,
                    pinned_by=request.pinned_by,
                    pinned_at=_now(),
                )
                session.add(r)
            else:
                r.pinned_by = request.pinned_by
            await session.commit()
            await session.refresh(r)
            return _pin_view(r)

    async def remove(
        self, profile_id: str, target_type: str, target_id: str
    ) -> None:
        async with self._sf() as session:
            await session.execute(
                delete(SalesbookPinnedRecord).where(
                    SalesbookPinnedRecord.profile_id == profile_id,
                    SalesbookPinnedRecord.target_type == target_type,
                    SalesbookPinnedRecord.target_id == target_id,
                )
            )
            await session.commit()


__all__ = [
    "SqlAlchemySalesbookClientContactRepository",
    "SqlAlchemySalesbookOnboardingRepository",
    "SqlAlchemySalesbookPipelineRepository",
    "SqlAlchemySalesbookEngagementRepository",
    "SqlAlchemySalesbookTeamMembershipRepository",
    "SqlAlchemySalesbookCommentRepository",
    "SqlAlchemySalesbookPinRepository",
    "CompanyProfileProductReadAdapter",
]
