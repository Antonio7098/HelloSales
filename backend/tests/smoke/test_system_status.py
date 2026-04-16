from __future__ import annotations

import httpx


async def test_system_status_endpoint(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["app_name"] == "HelloSales API"
    assert payload["data"]["environment"] == "test"
    assert payload["data"]["workflow_engine"] == "stageflow"
