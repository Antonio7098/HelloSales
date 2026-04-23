"""Dashboard data application service."""

from __future__ import annotations

from hello_sales_backend.modules.dashboard_data.use_cases.ports import (
    DashboardDataRepositoryPort,
    DashboardSeedLoaderPort,
)
from hello_sales_backend.modules.dashboard_data.use_cases.views import DashboardDataListView


class DashboardDataService:
    """Expose governed dashboard data through a stable module facade."""

    def __init__(
        self,
        *,
        repository: DashboardDataRepositoryPort,
        seed_loader: DashboardSeedLoaderPort,
    ) -> None:
        self._repository = repository
        self._seed_loader = seed_loader

    async def ensure_seeded(self) -> int:
        existing_count = await self._repository.count_entries()
        if existing_count > 0:
            return existing_count
        entries = list(self._seed_loader.load_entries())
        await self._repository.replace_entries(entries)
        return len(entries)

    async def list_entries(self) -> DashboardDataListView:
        await self.ensure_seeded()
        return await self._repository.list_entries()
