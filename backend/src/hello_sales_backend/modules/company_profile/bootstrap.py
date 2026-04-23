"""Company profile data module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.modules.company_profile.infra.memory import (
    InMemoryCompanyProfileRepository,
)
from hello_sales_backend.modules.company_profile.infra.repository import (
    SqlAlchemyCompanyProfileRepository,
)
from hello_sales_backend.modules.company_profile.use_cases.company_profile_service import (
    CompanyProfileService,
)
from hello_sales_backend.platform.config.settings import Settings


@dataclass(slots=True)
class CompanyProfileModule:
    """Resolved company profile module bundle."""

    service: CompanyProfileService


def build_company_profile_module(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> CompanyProfileModule:
    """Build the company profile module."""

    repository = (
        InMemoryCompanyProfileRepository()
        if settings.database_url.startswith("sqlite+aiosqlite")
        else SqlAlchemyCompanyProfileRepository(session_factory)
    )
    return CompanyProfileModule(
        service=CompanyProfileService(
            repository=repository,
        )
    )
