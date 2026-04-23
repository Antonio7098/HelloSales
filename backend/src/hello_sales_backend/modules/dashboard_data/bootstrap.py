"""Dashboard data module assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from hello_sales_backend.modules.dashboard_data.infra.csv_seed_loader import CsvDashboardSeedLoader
from hello_sales_backend.modules.dashboard_data.infra.memory import InMemoryDashboardDataRepository
from hello_sales_backend.modules.dashboard_data.infra.repository import SqlAlchemyDashboardDataRepository
from hello_sales_backend.modules.dashboard_data.use_cases.dashboard_data_service import (
    DashboardDataService,
)
from hello_sales_backend.platform.config.settings import Settings


@dataclass(slots=True)
class DashboardDataModule:
    """Resolved dashboard-data module bundle."""

    service: DashboardDataService


def _resolve_seed_path(configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute():
        return path
    backend_root = Path(__file__).resolve().parents[4]
    repo_root = Path(__file__).resolve().parents[5]
    candidates = (
        Path.cwd() / path,
        backend_root / path,
        repo_root / path,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return repo_root / path


def build_dashboard_data_module(
    *,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    seed_path: str,
) -> DashboardDataModule:
    """Build the dashboard-data module."""

    repository = (
        InMemoryDashboardDataRepository()
        if settings.database_url.startswith("sqlite+aiosqlite")
        else SqlAlchemyDashboardDataRepository(session_factory)
    )
    seed_loader = CsvDashboardSeedLoader(_resolve_seed_path(seed_path))
    return DashboardDataModule(
        service=DashboardDataService(
            repository=repository,
            seed_loader=seed_loader,
        )
    )
