from __future__ import annotations


async def test_dashboard_data_entries_endpoint_returns_seeded_sections(client) -> None:
    response = await client.get("/api/dashboard-data/entries")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["total_entries"] == 21
    assert payload["sections"][0]["dataset_key"] == "company_overview"
    assert payload["sections"][0]["entries"][0]["entry_id"] == "product_truth_anchor"
    assert any(section["dataset_key"] == "product_profile" for section in payload["sections"])
