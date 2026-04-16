from __future__ import annotations

import httpx


async def test_liveness_endpoint(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health/liveness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "live"


async def test_readiness_endpoint(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ready"
    assert payload["data"]["database"] == "configured"
    assert payload["data"]["checks"]["database"]["required"] is False
