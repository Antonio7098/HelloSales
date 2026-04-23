"""SQLAlchemy repository for dashboard data."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.modules.dashboard_data.use_cases.ports import DashboardDataRepositoryPort
from hello_sales_backend.modules.dashboard_data.use_cases.views import (
    DashboardDataEntryView,
    DashboardDataListView,
    DashboardDataSectionView,
)
from hello_sales_backend.platform.db.models import DashboardDataRecord


class SqlAlchemyDashboardDataRepository(DashboardDataRepositoryPort):
    """Persist and read dashboard data entries."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def count_entries(self) -> int:
        async with self._session_factory() as session:
            rows = await session.scalars(select(DashboardDataRecord.entry_id))
            return len(list(rows))

    async def replace_entries(self, entries: Sequence[DashboardDataEntryView]) -> None:
        async with self._session_factory() as session:
            await session.execute(delete(DashboardDataRecord))
            session.add_all(
                DashboardDataRecord(
                    entry_id=entry.entry_id,
                    dataset_key=entry.dataset_key,
                    sequence_no=entry.sequence_no,
                    section_label=entry.section_label,
                    prompt_text=entry.prompt_text,
                    answer_type=entry.answer_type,
                    example_answer=entry.example_answer,
                )
                for entry in entries
            )
            await session.commit()

    async def list_entries(self) -> DashboardDataListView:
        async with self._session_factory() as session:
            records = list(
                await session.scalars(
                    select(DashboardDataRecord).order_by(
                        DashboardDataRecord.dataset_key,
                        DashboardDataRecord.sequence_no,
                    )
                )
            )

        sections_by_key: dict[tuple[str, str], list[DashboardDataEntryView]] = defaultdict(list)
        for record in records:
            key = (record.dataset_key, record.section_label)
            sections_by_key[key].append(
                DashboardDataEntryView(
                    entry_id=record.entry_id,
                    dataset_key=record.dataset_key,
                    sequence_no=record.sequence_no,
                    section_label=record.section_label,
                    prompt_text=record.prompt_text,
                    answer_type=record.answer_type,
                    example_answer=record.example_answer,
                )
            )

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
        return DashboardDataListView(
            total_entries=len(records),
            sections=ordered_sections,
        )
