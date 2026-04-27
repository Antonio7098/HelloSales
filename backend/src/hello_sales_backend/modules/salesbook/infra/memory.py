"""In-memory salesbook repositories for tests + scaffold-stage. /Oliviercontribution.

These mirror the SqlAlchemy repos in repository.py and implement the same Ports
defined in use_cases/ports.py. Used when the configured database URL starts with
``sqlite+aiosqlite`` (matching the InMemoryAgentStore convention) and in tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

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


class InMemorySalesbookClientContactRepository(SalesbookClientContactRepositoryPort):
    def __init__(self) -> None:
        self._by_profile: dict[str, ClientContactView] = {}

    async def get(self, profile_id: str) -> ClientContactView | None:
        return self._by_profile.get(profile_id)

    async def upsert(self, profile_id: str, request: ClientContactUpsertRequest) -> ClientContactView:
        now = _now()
        existing = self._by_profile.get(profile_id)
        view = ClientContactView(
            extension_id=existing.extension_id if existing else _new_id(),
            profile_id=profile_id,
            primary_email=request.primary_email,
            contact_name=request.contact_name,
            contact_role=request.contact_role,
            phone=request.phone,
            company_size=request.company_size,
            geography=request.geography,
            status=request.status,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._by_profile[profile_id] = view
        return view


# ────────────────────────────────────────────────────────────────────────────


class InMemorySalesbookOnboardingRepository(SalesbookOnboardingRepositoryPort):
    def __init__(self) -> None:
        self._progress: dict[str, OnboardingProgressView] = {}
        # responses keyed by (profile_id, question_key)
        self._responses: dict[tuple[str, str], OnboardingResponseView] = {}

    async def get_progress(self, profile_id: str) -> OnboardingProgressView:
        existing = self._progress.get(profile_id)
        if existing:
            return existing
        now = _now()
        view = OnboardingProgressView(
            progress_id=_new_id(),
            profile_id=profile_id,
            current_phase=1,
            phase1_pct=Decimal("0.00"),
            phase2_pct=Decimal("0.00"),
            phase3_pct=Decimal("0.00"),
            phase1_completed_at=None,
            phase2_completed_at=None,
            phase3_completed_at=None,
            total_completion_pct=Decimal("0.00"),
            updated_at=now,
        )
        self._progress[profile_id] = view
        return view

    async def upsert_progress(
        self, profile_id: str, *, current_phase: int,
        phase1_pct: float, phase2_pct: float, phase3_pct: float, total_pct: float,
        phase1_completed_at_iso: str | None,
        phase2_completed_at_iso: str | None,
        phase3_completed_at_iso: str | None,
    ) -> OnboardingProgressView:
        existing = await self.get_progress(profile_id)
        view = OnboardingProgressView(
            progress_id=existing.progress_id,
            profile_id=profile_id,
            current_phase=current_phase,
            phase1_pct=Decimal(str(phase1_pct)),
            phase2_pct=Decimal(str(phase2_pct)),
            phase3_pct=Decimal(str(phase3_pct)),
            phase1_completed_at=datetime.fromisoformat(phase1_completed_at_iso) if phase1_completed_at_iso else None,
            phase2_completed_at=datetime.fromisoformat(phase2_completed_at_iso) if phase2_completed_at_iso else None,
            phase3_completed_at=datetime.fromisoformat(phase3_completed_at_iso) if phase3_completed_at_iso else None,
            total_completion_pct=Decimal(str(total_pct)),
            updated_at=_now(),
        )
        self._progress[profile_id] = view
        return view

    async def list_responses(
        self, profile_id: str, phase: int | None = None
    ) -> list[OnboardingResponseView]:
        rows = [v for (pid, _), v in self._responses.items() if pid == profile_id]
        if phase is not None:
            rows = [v for v in rows if v.phase == phase]
        return sorted(rows, key=lambda v: (v.phase, v.question_key))

    async def upsert_response(
        self, profile_id: str, request: OnboardingResponseSubmit
    ) -> OnboardingResponseView:
        now = _now()
        key = (profile_id, request.question_key)
        existing = self._responses.get(key)
        view = OnboardingResponseView(
            response_id=existing.response_id if existing else _new_id(),
            profile_id=profile_id,
            phase=request.phase,
            question_key=request.question_key,
            question_text=request.question_text,
            response_value=request.response_value,
            response_type=request.response_type,
            answered_at=existing.answered_at if existing else now,
            updated_at=now,
        )
        self._responses[key] = view
        return view

    async def count_answered_by_phase(self, profile_id: str) -> dict[int, int]:
        out = {1: 0, 2: 0, 3: 0}
        for (pid, _), v in self._responses.items():
            if pid != profile_id:
                continue
            if v.response_value not in (None, ""):
                out[v.phase] = out.get(v.phase, 0) + 1
        return out


# ────────────────────────────────────────────────────────────────────────────


class InMemorySalesbookPipelineRepository(SalesbookPipelineRepositoryPort):
    def __init__(self) -> None:
        self._deals: dict[str, PipelineDealView] = {}

    async def list_deals(self, profile_id: str) -> list[PipelineDealView]:
        return sorted(
            (d for d in self._deals.values() if d.profile_id == profile_id),
            key=lambda d: d.created_at,
            reverse=True,
        )

    async def get_deal(self, deal_id: str) -> PipelineDealView | None:
        return self._deals.get(deal_id)

    async def create_deal(
        self, profile_id: str, request: PipelineDealCreateRequest
    ) -> PipelineDealView:
        now = _now()
        view = PipelineDealView(
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
            closed_at=None,
            close_reason=None,
        )
        self._deals[view.deal_id] = view
        return view

    async def update_deal(
        self, deal_id: str, request: PipelineDealUpdateRequest
    ) -> PipelineDealView:
        existing = self._deals[deal_id]
        now = _now()
        old_stage = existing.stage
        new_stage = request.stage if request.stage is not None else existing.stage
        stage_entered = now if (request.stage and request.stage != old_stage) else existing.stage_entered_at
        closed_at = existing.closed_at
        if new_stage in ("closed_won", "closed_lost") and closed_at is None:
            closed_at = now
        view = existing.model_copy(update={
            "stage": new_stage,
            "lead_source": request.lead_source if request.lead_source is not None else existing.lead_source,
            "lead_score": request.lead_score if request.lead_score is not None else existing.lead_score,
            "assigned_agent": request.assigned_agent if request.assigned_agent is not None else existing.assigned_agent,
            "deal_value": request.deal_value if request.deal_value is not None else existing.deal_value,
            "deal_probability": request.deal_probability if request.deal_probability is not None else existing.deal_probability,
            "next_action": request.next_action if request.next_action is not None else existing.next_action,
            "next_action_date": request.next_action_date if request.next_action_date is not None else existing.next_action_date,
            "stage_entered_at": stage_entered,
            "closed_at": closed_at,
            "close_reason": request.close_reason if request.close_reason is not None else existing.close_reason,
        })
        self._deals[deal_id] = view
        return view


# ────────────────────────────────────────────────────────────────────────────


class InMemorySalesbookEngagementRepository(SalesbookEngagementRepositoryPort):
    def __init__(self) -> None:
        self._logs: list[EngagementLogView] = []

    async def create(self, request: EngagementLogCreateRequest) -> EngagementLogView:
        view = EngagementLogView(
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
        self._logs.append(view)
        return view

    async def list_for_profile(
        self, profile_id: str, deal_id: str | None = None, limit: int = 100
    ) -> list[EngagementLogView]:
        rows = [l for l in self._logs if l.profile_id == profile_id]
        if deal_id is not None:
            rows = [l for l in rows if l.deal_id == deal_id]
        rows.sort(key=lambda l: l.timestamp, reverse=True)
        return rows[:limit]

    async def list_all(self, limit: int = 200) -> list[EngagementLogView]:
        rows = sorted(self._logs, key=lambda l: l.timestamp, reverse=True)
        return rows[:limit]


# ────────────────────────────────────────────────────────────────────────────


class InMemorySalesbookTeamMembershipRepository(SalesbookTeamMembershipRepositoryPort):
    def __init__(self) -> None:
        self._members: dict[str, TeamMembershipView] = {}

    async def list_team(self, profile_id: str) -> list[TeamMembershipView]:
        return sorted(
            (m for m in self._members.values() if m.profile_id == profile_id),
            key=lambda m: m.created_at,
        )

    async def add(self, profile_id: str, request: TeamMembershipCreateRequest) -> TeamMembershipView:
        view = TeamMembershipView(
            membership_id=_new_id(),
            profile_id=profile_id,
            user_email=request.user_email,
            role_level=request.role_level,
            can_invite=request.can_invite,
            can_export=request.can_export,
            can_edit_onboarding=request.can_edit_onboarding,
            created_at=_now(),
        )
        self._members[view.membership_id] = view
        return view

    async def remove(self, membership_id: str) -> None:
        self._members.pop(membership_id, None)


# ────────────────────────────────────────────────────────────────────────────


class NullProductReadPort(SalesbookProductReadPort):
    """Used in tests when there's no real CompanyProfileService backing the products read."""

    async def list_products_for_profile(self, profile_id: str) -> list[SalesbookExhaustiveProductEntry]:
        return []


class InMemorySalesbookCommentRepository(SalesbookCommentRepositoryPort):
    def __init__(self) -> None:
        self._comments: dict[str, SalesbookCommentView] = {}

    async def create(
        self, profile_id: str, request: SalesbookCommentCreateRequest
    ) -> SalesbookCommentView:
        now = _now()
        view = SalesbookCommentView(
            comment_id=_new_id(),
            profile_id=profile_id,
            target_type=request.target_type,
            target_id=request.target_id,
            author_email=request.author_email,
            body=request.body,
            status="pending",
            approved_by=None,
            approved_at=None,
            created_at=now,
            updated_at=now,
        )
        self._comments[view.comment_id] = view
        return view

    async def list_for_profile(
        self, profile_id: str, status: str | None = None,
        target_id: str | None = None,
    ) -> list[SalesbookCommentView]:
        rows = [c for c in self._comments.values() if c.profile_id == profile_id]
        if status is not None:
            rows = [c for c in rows if c.status == status]
        if target_id is not None:
            rows = [c for c in rows if c.target_id == target_id]
        return sorted(rows, key=lambda c: c.created_at, reverse=True)

    async def get(self, comment_id: str) -> SalesbookCommentView | None:
        return self._comments.get(comment_id)

    async def update_status(
        self, comment_id: str, *, status: str, approved_by: str | None,
    ) -> SalesbookCommentView:
        existing = self._comments[comment_id]
        view = existing.model_copy(update={
            "status": status,
            "approved_by": approved_by,
            "approved_at": _now() if status == "approved" else None,
            "updated_at": _now(),
        })
        self._comments[comment_id] = view
        return view


class InMemorySalesbookPinRepository(SalesbookPinRepositoryPort):
    def __init__(self) -> None:
        # keyed by (profile_id, target_type, target_id)
        self._pins: dict[tuple[str, str, str], SalesbookPinView] = {}

    async def list_for_profile(self, profile_id: str) -> list[SalesbookPinView]:
        return sorted(
            (p for p in self._pins.values() if p.profile_id == profile_id),
            key=lambda p: p.pinned_at, reverse=True,
        )

    async def upsert(
        self, profile_id: str, request: SalesbookPinRequest
    ) -> SalesbookPinView:
        key = (profile_id, request.target_type, request.target_id)
        existing = self._pins.get(key)
        view = SalesbookPinView(
            pin_id=existing.pin_id if existing else _new_id(),
            profile_id=profile_id,
            target_type=request.target_type,
            target_id=request.target_id,
            pinned_by=request.pinned_by,
            pinned_at=existing.pinned_at if existing else _now(),
        )
        self._pins[key] = view
        return view

    async def remove(
        self, profile_id: str, target_type: str, target_id: str
    ) -> None:
        self._pins.pop((profile_id, target_type, target_id), None)


__all__ = [
    "InMemorySalesbookClientContactRepository",
    "InMemorySalesbookOnboardingRepository",
    "InMemorySalesbookPipelineRepository",
    "InMemorySalesbookEngagementRepository",
    "InMemorySalesbookTeamMembershipRepository",
    "InMemorySalesbookCommentRepository",
    "InMemorySalesbookPinRepository",
    "NullProductReadPort",
]
