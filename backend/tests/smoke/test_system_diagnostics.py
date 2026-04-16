from __future__ import annotations


async def test_system_diagnostics_endpoint(client):
    response = await client.get("/api/system/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["database_scheme"] == "sqlite+aiosqlite"
    assert payload["data"]["providers"][0]["name"] == "noop"
    assert {item["agent_id"] for item in payload["data"]["agent_profiles"]} == {"generic", "observer"}
    assert payload["data"]["tasks"]["total_count"] == 0
    assert payload["data"]["agents"]["total_count"] == 0
    assert payload["data"]["events"][0]["event_type"] == "startup.completed"
    assert payload["data"]["alerts"] == []
