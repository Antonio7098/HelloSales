from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.providers.llm.contracts import (
    ChatCompletion,
    ChatMessage,
    ChatModelPort,
)


class FixedClock:
    def now_iso(self) -> str:
        return "2026-01-01T00:00:00+00:00"


class FakeChatModel(ChatModelPort):
    provider_name = "fake"

    async def generate(self, messages: list[ChatMessage]) -> ChatCompletion:
        return ChatCompletion(provider=self.provider_name, model="fake-model", output_text="ok")

    def is_configured(self) -> bool:
        return True


async def test_app_overrides_are_visible_through_diagnostics(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'overrides.db'}",
    )
    app = create_app(
        settings=settings,
        overrides=AppOverrides(
            llm_provider=FakeChatModel(),
            system_clock=FixedClock(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/system/diagnostics")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["current_time_utc"] == "2026-01-01T00:00:00+00:00"
    assert payload["providers"][0]["name"] == "fake"
    assert payload["providers"][0]["available"] is True
    assert {item["agent_id"] for item in payload["agent_profiles"]} == {"generic", "observer"}
