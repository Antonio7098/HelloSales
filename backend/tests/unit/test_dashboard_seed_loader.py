from __future__ import annotations

from pathlib import Path

import pytest

from hello_sales_backend.modules.dashboard_data.infra.csv_seed_loader import CsvDashboardSeedLoader
from hello_sales_backend.shared.errors import AppError


def test_csv_seed_loader_parses_governed_mvp_dataset() -> None:
    loader = CsvDashboardSeedLoader(
        Path("/home/antonioborgerees/coding/HelloSales/ops/hello-sales-data-mvp.csv")
    )

    entries = list(loader.load_entries())

    assert len(entries) == 21
    assert entries[0].entry_id == "product_truth_anchor"
    assert entries[0].dataset_key == "company_overview"
    assert entries[-1].entry_id == "product_revenue_share"
    assert entries[-1].dataset_key == "product_profile"


def test_csv_seed_loader_raises_structured_error_for_missing_file(tmp_path: Path) -> None:
    loader = CsvDashboardSeedLoader(tmp_path / "missing.csv")

    with pytest.raises(AppError) as exc_info:
        loader.load_entries()

    assert exc_info.value.code == "data.dashboard_seed.missing"
    assert exc_info.value.category == "data"
