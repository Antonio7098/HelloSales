from __future__ import annotations

from hello_sales_backend.modules.dashboard_data.infra.static_seed_loader import (
    StaticDashboardSeedLoader,
)


def test_static_seed_loader_returns_governed_mvp_dataset() -> None:
    loader = StaticDashboardSeedLoader()

    entries = list(loader.load_entries())

    assert len(entries) == 21
    assert entries[0].entry_id == "product_truth_anchor"
    assert entries[0].dataset_key == "company_overview"
    assert entries[-1].entry_id == "product_revenue_share"
    assert entries[-1].dataset_key == "product_profile"
