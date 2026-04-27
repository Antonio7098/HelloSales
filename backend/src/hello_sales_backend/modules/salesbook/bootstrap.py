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
    InMemorySalesbookEngagementRepository,
    InMemorySalesbookOnboardingRepository,
    InMemorySalesbookPipelineRepository,
    InMemorySalesbookTeamMembershipRepository,
    NullProductReadPort,
)
from hello_sales_backend.modules.salesbook.infra.repository import (
    CompanyProfileProductReadAdapter,
    SqlAlchemySalesbookClientContactRepository,
    SqlAlchemySalesbookEngagementRepository,
    SqlAlchemySalesbookOnboardingRepository,
    SqlAlchemySalesbookPipelineRepository,
    SqlAlchemySalesbookTeamMembershipRepository,
)
from hello_sales_backend.modules.salesbook.use_cases.ports import (
    SalesbookProductReadPort,
)
from hello_sales_backend.modules.salesbook.use_cases.salesbook_service import (
    SalesbookService,
)
from hello_sales_backend.platform.config.settings import Settings

if TYPE_CHECKING:
    from hello_sales_backend.modules.company_profile import CompanyProfileService


@dataclass(slots=True)
class SalesbookModule:
    """Resolved salesbook module bundle."""

    service: SalesbookService


def build_salesbook_module(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    company_profile_service: "CompanyProfileService | None" = None,
) -> SalesbookModule:
    """Build the salesbook module.

    ``company_profile_service`` is optional so the module can be built without
    that dependency in tests; when omitted, the exhaustive view returns an
    empty product list (NullProductReadPort).
    """

    on_sqlite = settings.database_url.startswith("sqlite+aiosqlite")

    if on_sqlite:
        contact_repo = InMemorySalesbookClientContactRepository()
        onboarding_repo = InMemorySalesbookOnboardingRepository()
        pipeline_repo = InMemorySalesbookPipelineRepository()
        engagement_repo = InMemorySalesbookEngagementRepository()
        team_repo = InMemorySalesbookTeamMembershipRepository()
    else:
        contact_repo = SqlAlchemySalesbookClientContactRepository(session_factory)
        onboarding_repo = SqlAlchemySalesbookOnboardingRepository(session_factory)
        pipeline_repo = SqlAlchemySalesbookPipelineRepository(session_factory)
        engagement_repo = SqlAlchemySalesbookEngagementRepository(session_factory)
        team_repo = SqlAlchemySalesbookTeamMembershipRepository(session_factory)

    product_read: SalesbookProductReadPort = (
        CompanyProfileProductReadAdapter(company_profile_service)
        if company_profile_service is not None
        else NullProductReadPort()
    )

    sheets_provider = None
    sheets_url = os.getenv("HELLO_SALES_SHEETS_WEBHOOK_URL")
    if sheets_url:
        # Lazy import to avoid forcing httpx at import-time when feature is off.
        from hello_sales_backend.modules.salesbook.infra.sheets_provider import (  # noqa: E402
            SalesbookSheetsProvider,
        )
        sheets_provider = SalesbookSheetsProvider(webhook_url=sheets_url)

    return SalesbookModule(
        service=SalesbookService(
            contact_repo=contact_repo,
            onboarding_repo=onboarding_repo,
            pipeline_repo=pipeline_repo,
            engagement_repo=engagement_repo,
            team_repo=team_repo,
            product_read=product_read,
            sheets_provider=sheets_provider,
        )
    )


__all__ = ["SalesbookModule", "build_salesbook_module"]
