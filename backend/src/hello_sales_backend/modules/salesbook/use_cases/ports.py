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
    SalesbookExhaustiveProductEntry,
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


__all__ = [
    "SalesbookClientContactRepositoryPort",
    "SalesbookOnboardingRepositoryPort",
    "SalesbookPipelineRepositoryPort",
    "SalesbookEngagementRepositoryPort",
    "SalesbookTeamMembershipRepositoryPort",
    "SalesbookProductReadPort",
]
