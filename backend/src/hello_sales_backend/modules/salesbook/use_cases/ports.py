"""Salesbook repository ports. /Oliviercontribution.

Each Protocol is implemented by both InMemory (tests, scaffold-stage) and
SqlAlchemy (production) repositories in infra/.
"""

from __future__ import annotations

from typing import Protocol

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
    SalesbookDiagnosticsSummary,
    TeamMembershipCreateRequest,
    TeamMembershipView,
)


class SalesbookClientContactRepositoryPort(Protocol):
    async def get(self, profile_id: str) -> ClientContactView | None: ...
    async def upsert(self, profile_id: str, request: ClientContactUpsertRequest) -> ClientContactView: ...


class SalesbookOnboardingRepositoryPort(Protocol):
    async def get_progress(self, profile_id: str) -> OnboardingProgressView: ...
    async def upsert_progress(
        self, profile_id: str, *, current_phase: int,
        phase1_pct: float, phase2_pct: float, phase3_pct: float,
        total_pct: float,
        phase1_completed_at_iso: str | None,
        phase2_completed_at_iso: str | None,
        phase3_completed_at_iso: str | None,
    ) -> OnboardingProgressView: ...
    async def list_responses(
        self, profile_id: str, phase: int | None = None
    ) -> list[OnboardingResponseView]: ...
    async def upsert_response(
        self, profile_id: str, request: OnboardingResponseSubmit
    ) -> OnboardingResponseView: ...
    async def count_answered_by_phase(self, profile_id: str) -> dict[int, int]: ...


class SalesbookPipelineRepositoryPort(Protocol):
    async def list_deals(self, profile_id: str) -> list[PipelineDealView]: ...
    async def get_deal(self, deal_id: str) -> PipelineDealView | None: ...
    async def create_deal(
        self, profile_id: str, request: PipelineDealCreateRequest
    ) -> PipelineDealView: ...
    async def update_deal(
        self, deal_id: str, request: PipelineDealUpdateRequest
    ) -> PipelineDealView: ...


class SalesbookEngagementRepositoryPort(Protocol):
    async def create(self, request: EngagementLogCreateRequest) -> EngagementLogView: ...
    async def list_for_profile(
        self, profile_id: str, deal_id: str | None = None, limit: int = 100
    ) -> list[EngagementLogView]: ...
    async def list_all(self, limit: int = 200) -> list[EngagementLogView]: ...


class SalesbookTeamMembershipRepositoryPort(Protocol):
    async def list_team(self, profile_id: str) -> list[TeamMembershipView]: ...
    async def add(
        self, profile_id: str, request: TeamMembershipCreateRequest
    ) -> TeamMembershipView: ...
    async def remove(self, membership_id: str) -> None: ...


class SalesbookProductReadPort(Protocol):
    """Read-only view of company_profile products — used to build the exhaustive view.

    Implemented by adapting CompanyProfileService.list_products(). The salesbook
    module never writes to products — that's company_profile's responsibility.
    """

    async def list_products_for_profile(
        self, profile_id: str
    ) -> list[SalesbookExhaustiveProductEntry]: ...


class SalesbookCommentRepositoryPort(Protocol):
    async def create(
        self, profile_id: str, request: SalesbookCommentCreateRequest
    ) -> SalesbookCommentView: ...
    async def list_for_profile(
        self, profile_id: str, status: str | None = None,
        target_id: str | None = None,
    ) -> list[SalesbookCommentView]: ...
    async def get(self, comment_id: str) -> SalesbookCommentView | None: ...
    async def update_status(
        self, comment_id: str, *, status: str, approved_by: str | None,
    ) -> SalesbookCommentView: ...


class SalesbookPinRepositoryPort(Protocol):
    async def list_for_profile(self, profile_id: str) -> list[SalesbookPinView]: ...
    async def upsert(
        self, profile_id: str, request: SalesbookPinRequest
    ) -> SalesbookPinView: ...
    async def remove(
        self, profile_id: str, target_type: str, target_id: str
    ) -> None: ...


class SalesbookDiagnosticsPort(Protocol):
    """Provides operator-facing salesbook diagnostics."""

    async def summarize(self, limit: int = 10) -> SalesbookDiagnosticsSummary: ...


class SheetPushPort(Protocol):
    """Port for pushing salesbook events to an external sheet provider.

    The concrete implementation (e.g. SalesbookSheetsProvider) lives in infra/
    and is injected at composition time.
    """

    async def push(self, action: str, payload: dict[str, object]) -> None: ...


__all__ = [
    "SalesbookClientContactRepositoryPort",
    "SalesbookOnboardingRepositoryPort",
    "SalesbookPipelineRepositoryPort",
    "SalesbookEngagementRepositoryPort",
    "SalesbookTeamMembershipRepositoryPort",
    "SalesbookProductReadPort",
    "SalesbookCommentRepositoryPort",
    "SalesbookPinRepositoryPort",
    "SalesbookDiagnosticsPort",
    "SheetPushPort",
]
