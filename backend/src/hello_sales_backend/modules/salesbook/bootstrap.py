"""Salesbook module assembly. /Oliviercontribution.

Mirrors the company_profile module pattern: build_<x>_module(*, settings,
session_factory, ...) returns a Module dataclass containing the resolved
service. Repository swaps to InMemory when running on sqlite+aiosqlite
(matching the agent_store / session_store convention).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.modules.salesbook.infra.memory import (
    InMemorySalesbookClientContactRepository,
    InMemorySalesbookCommentRepository,
    InMemorySalesbookEngagementRepository,
    InMemorySalesbookOnboardingRepository,
    InMemorySalesbookPinRepository,
    InMemorySalesbookPipelineRepository,
    InMemorySalesbookTeamMembershipRepository,
    NullProductReadPort,
)
from hello_sales_backend.modules.salesbook.infra.repository import (
    CompanyProfileProductReadAdapter,
    SqlAlchemySalesbookClientContactRepository,
    SqlAlchemySalesbookCommentRepository,
    SqlAlchemySalesbookEngagementRepository,
    SqlAlchemySalesbookOnboardingRepository,
    SqlAlchemySalesbookPinRepository,
    SqlAlchemySalesbookPipelineRepository,
    SqlAlchemySalesbookTeamMembershipRepository,
)
from hello_sales_backend.modules.salesbook.use_cases.ports import (
    SalesbookClientContactRepositoryPort,
    SalesbookCommentRepositoryPort,
    SalesbookDiagnosticsPort,
    SalesbookEngagementRepositoryPort,
    SalesbookOnboardingRepositoryPort,
    SalesbookPinRepositoryPort,
    SalesbookPipelineRepositoryPort,
    SalesbookProductReadPort,
    SalesbookTeamMembershipRepositoryPort,
)
from hello_sales_backend.modules.salesbook.use_cases.salesbook_service import (
    SalesbookService,
)
from hello_sales_backend.modules.salesbook.use_cases.views import (
    SalesbookDiagnosticsSummary,
)
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner

if TYPE_CHECKING:
    from hello_sales_backend.modules.company_profile import CompanyProfileService


@dataclass(slots=True)
class SalesbookModule:
    """Resolved salesbook module bundle."""

    service: SalesbookService
    diagnostics: SalesbookDiagnosticsPort


class _NoOpSalesbookDiagnostics:
    """Compatibility shim for tests and bootstrap paths without salesbook wiring."""

    async def summarize(self, limit: int = 10) -> SalesbookDiagnosticsSummary:
        return SalesbookDiagnosticsSummary(
            active_count=0, total_count=0, recent_runs=[]
        )


class SalesbookEngagementDiagnosticsAdapter:
    """Adapter that exposes engagement logs as salesbook diagnostics."""

    def __init__(self, engagement_repo: SalesbookEngagementRepositoryPort) -> None:
        self._engagement = engagement_repo

    async def summarize(self, limit: int = 10) -> SalesbookDiagnosticsSummary:
        logs = await self._engagement.list_all(limit=200)
        recent = sorted(logs, key=lambda e: e.timestamp, reverse=True)[:limit]
        return SalesbookDiagnosticsSummary(
            active_count=len(logs),
            total_count=len(logs),
            recent_runs=recent,
        )


def build_salesbook_module(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    tasks: BackgroundTaskRunner,
    company_profile_service: CompanyProfileService | None = None,
) -> SalesbookModule:
    """Build the salesbook module.

    ``company_profile_service`` is optional so the module can be built without
    that dependency in tests; when omitted, the exhaustive view returns an
    empty product list (NullProductReadPort).
    """

    on_sqlite = settings.database_url.startswith("sqlite+aiosqlite")

    # Type the repos against their ports so the in-memory/sqlalchemy swap is
    # type-safe (otherwise mypy infers the first branch's concrete type and
    # complains when the else branch reassigns to a sibling concrete type).
    contact_repo: SalesbookClientContactRepositoryPort
    onboarding_repo: SalesbookOnboardingRepositoryPort
    pipeline_repo: SalesbookPipelineRepositoryPort
    engagement_repo: SalesbookEngagementRepositoryPort
    team_repo: SalesbookTeamMembershipRepositoryPort
    comment_repo: SalesbookCommentRepositoryPort
    pin_repo: SalesbookPinRepositoryPort

    if on_sqlite:
        contact_repo = InMemorySalesbookClientContactRepository()
        onboarding_repo = InMemorySalesbookOnboardingRepository()
        pipeline_repo = InMemorySalesbookPipelineRepository()
        engagement_repo = InMemorySalesbookEngagementRepository()
        team_repo = InMemorySalesbookTeamMembershipRepository()
        comment_repo = InMemorySalesbookCommentRepository()
        pin_repo = InMemorySalesbookPinRepository()
    else:
        contact_repo = SqlAlchemySalesbookClientContactRepository(session_factory)
        onboarding_repo = SqlAlchemySalesbookOnboardingRepository(session_factory)
        pipeline_repo = SqlAlchemySalesbookPipelineRepository(session_factory)
        engagement_repo = SqlAlchemySalesbookEngagementRepository(session_factory)
        team_repo = SqlAlchemySalesbookTeamMembershipRepository(session_factory)
        comment_repo = SqlAlchemySalesbookCommentRepository(session_factory)
        pin_repo = SqlAlchemySalesbookPinRepository(session_factory)

    product_read: SalesbookProductReadPort = (
        CompanyProfileProductReadAdapter(company_profile_service)
        if company_profile_service is not None
        else NullProductReadPort()
    )

    sheets_provider = None
    sheets_url = os.getenv("HELLO_SALES_SHEETS_WEBHOOK_URL")
    if sheets_url:
        from hello_sales_backend.modules.salesbook.infra.sheets_provider import (
            SalesbookSheetsProvider,
        )
        sheets_provider = SalesbookSheetsProvider(webhook_url=sheets_url)

    salesbook_diagnostics: SalesbookDiagnosticsPort = (
        SalesbookEngagementDiagnosticsAdapter(engagement_repo)
        if engagement_repo is not None
        else _NoOpSalesbookDiagnostics()
    )

    return SalesbookModule(
        service=SalesbookService(
            contact_repo=contact_repo,
            onboarding_repo=onboarding_repo,
            pipeline_repo=pipeline_repo,
            engagement_repo=engagement_repo,
            team_repo=team_repo,
            product_read=product_read,
            comment_repo=comment_repo,
            pin_repo=pin_repo,
            sheets_provider=sheets_provider,
            tasks=tasks,
        ),
        diagnostics=salesbook_diagnostics,
    )


__all__ = ["SalesbookModule", "build_salesbook_module"]
