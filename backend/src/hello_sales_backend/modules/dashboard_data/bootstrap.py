"""Dashboard data module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.modules.dashboard_data.infra.memory import InMemoryDashboardDataRepository
from hello_sales_backend.modules.dashboard_data.infra.repository import (
    SqlAlchemyDashboardDataRepository,
)
from hello_sales_backend.modules.dashboard_data.infra.static_seed_loader import (
    StaticDashboardSeedLoader,
)
from hello_sales_backend.modules.dashboard_data.use_cases.dashboard_data_service import (
    DashboardDataService,
)
from hello_sales_backend.platform.config.settings import Settings


@dataclass(slots=True)
class DashboardDataModule:
    """Resolved dashboard-data module bundle."""

    service: DashboardDataService


def build_dashboard_data_module(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> DashboardDataModule:
    """Build the dashboard-data module."""

    repository = (
        InMemoryDashboardDataRepository()
        if settings.database_url.startswith("sqlite+aiosqlite")
        else SqlAlchemyDashboardDataRepository(session_factory)
    )
    seed_loader = StaticDashboardSeedLoader()
    return DashboardDataModule(
        service=DashboardDataService(
            repository=repository,
            seed_loader=seed_loader,
        )
    )
