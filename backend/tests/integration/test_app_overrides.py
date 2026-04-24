from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.auth.contracts import AuthResult
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.llm import (
    JSONGenerationResult,
    LLMCallContext,
    LLMMessage,
    LLMProviderPort,
    TextGenerationResult,
)
from tests.support.auth import FakeAuthProvider, attach_test_session_cookie, build_test_auth_context


class FixedClock:
    def now_iso(self) -> str:
        return "2026-01-01T00:00:00+00:00"


class FakeChatModel(LLMProviderPort):
    provider_name = "fake"

    async def generate(self, messages: list[LLMMessage]) -> TextGenerationResult:
        return TextGenerationResult(
            provider=self.provider_name, model="fake-model", output_text="ok"
        )

    async def generate_text(
        self,
        messages: list[LLMMessage],
        *,
        context: LLMCallContext | None = None,
    ) -> TextGenerationResult:
        return TextGenerationResult(
            provider=self.provider_name, model="fake-model", output_text="ok"
        )

    async def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema_hint=None,
        context: LLMCallContext | None = None,
    ) -> JSONGenerationResult:
        return JSONGenerationResult(
            provider=self.provider_name,
            model="fake-model",
            raw_text="{}",
            output_json={},
        )

    def is_configured(self) -> bool:
        return True


async def test_app_overrides_are_visible_through_diagnostics(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'overrides.db'}",
    )
    auth_context = build_test_auth_context()
    app = create_app(
        settings=settings,
        overrides=AppOverrides(
            auth_provider=FakeAuthProvider(
                AuthResult(
                    context=auth_context,
                    session_token="test-session",
                    source="session_cookie",
                )
            ),
            llm_provider=FakeChatModel(),
            system_clock=FixedClock(),
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            response = await client.get("/api/system/diagnostics")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["current_time_utc"] == "2026-01-01T00:00:00+00:00"
    providers = {item["kind"]: item for item in payload["providers"]}
    assert providers["llm"]["name"] == "fake"
    assert providers["llm"]["available"] is True
    assert {item["agent_id"] for item in payload["agent_profiles"]} == {"generic", "observer"}
