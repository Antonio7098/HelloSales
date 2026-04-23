"""CSV-backed seed loader for dashboard data."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from hello_sales_backend.modules.dashboard_data.use_cases.ports import DashboardSeedLoaderPort
from hello_sales_backend.modules.dashboard_data.use_cases.views import DashboardDataEntryView
from hello_sales_backend.shared.errors import app_error


class CsvDashboardSeedLoader(DashboardSeedLoaderPort):
    """Load dashboard seed rows from the governed CSV contract."""

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path

    def load_entries(self) -> Sequence[DashboardDataEntryView]:
        if not self._source_path.exists():
            raise app_error(
                "Dashboard seed file is missing",
                code="data.dashboard_seed.missing",
                category="data",
                status_code=500,
                severity="critical",
                details={"path": str(self._source_path)},
                operation="dashboard_data.seed_loader.load_entries",
                component="dashboard_data",
            )

        entries: list[DashboardDataEntryView] = []
        current_dataset = "company_overview"
        with self._source_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for raw_row in reader:
                row = [cell.strip() for cell in raw_row]
                if not any(row):
                    continue
                if "#" in row and "Product Field" in row:
                    current_dataset = "product_profile"
                    continue
                if len(row) < 7:
                    continue
                sequence_cell = row[1]
                section_label = row[2]
                question = row[3]
                answer_type = row[4]
                example_answer = row[5]
                entry_name = row[6]
                if not sequence_cell.isdigit():
                    continue
                entries.append(
                    DashboardDataEntryView(
                        entry_id=entry_name,
                        dataset_key=current_dataset,
                        sequence_no=int(sequence_cell),
                        section_label=section_label,
                        prompt_text=question,
                        answer_type=answer_type,
                        example_answer=example_answer,
                    )
                )
        if not entries:
            raise app_error(
                "Dashboard seed file contained no usable rows",
                code="data.dashboard_seed.empty",
                category="data",
                status_code=500,
                severity="critical",
                details={"path": str(self._source_path)},
                operation="dashboard_data.seed_loader.load_entries",
                component="dashboard_data",
            )
        return entries
