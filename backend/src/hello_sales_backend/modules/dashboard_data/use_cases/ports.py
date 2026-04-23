"""Ports for dashboard data use cases."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from hello_sales_backend.modules.dashboard_data.use_cases.views import (
    DashboardDataEntryView,
    DashboardDataListView,
)


class DashboardDataRepositoryPort(Protocol):
    """Persistence capabilities required by dashboard-data use cases."""

    async def count_entries(self) -> int: ...

    async def replace_entries(self, entries: Sequence[DashboardDataEntryView]) -> None: ...

    async def list_entries(self) -> DashboardDataListView: ...


class DashboardSeedLoaderPort(Protocol):
    """Seed loader contract for governed dashboard data."""

    def load_entries(self) -> Sequence[DashboardDataEntryView]: ...
