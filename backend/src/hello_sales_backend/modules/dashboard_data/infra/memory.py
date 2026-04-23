"""In-memory repository for dashboard data."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from hello_sales_backend.modules.dashboard_data.use_cases.ports import DashboardDataRepositoryPort
from hello_sales_backend.modules.dashboard_data.use_cases.views import (
    DashboardDataEntryView,
    DashboardDataListView,
    DashboardDataSectionView,
)


class InMemoryDashboardDataRepository(DashboardDataRepositoryPort):
    """Keep dashboard data in process memory for SQLite-backed test paths."""

    def __init__(self) -> None:
        self._entries: list[DashboardDataEntryView] = []

    async def count_entries(self) -> int:
        return len(self._entries)

    async def replace_entries(self, entries: Sequence[DashboardDataEntryView]) -> None:
        self._entries = [entry.model_copy(deep=True) for entry in entries]

    async def list_entries(self) -> DashboardDataListView:
        sections_by_key: dict[tuple[str, str], list[DashboardDataEntryView]] = defaultdict(list)
        for entry in self._entries:
            sections_by_key[(entry.dataset_key, entry.section_label)].append(entry.model_copy(deep=True))
        ordered_sections = [
            DashboardDataSectionView(
                dataset_key=dataset_key,
                section_label=section_label,
                entries=sorted(entries, key=lambda item: item.sequence_no),
            )
            for (dataset_key, section_label), entries in sorted(
                sections_by_key.items(),
                key=lambda item: (item[0][0], min(entry.sequence_no for entry in item[1])),
            )
        ]
        return DashboardDataListView(total_entries=len(self._entries), sections=ordered_sections)
