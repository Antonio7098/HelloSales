from __future__ import annotations

import httpx
import pytest

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from tests.support.auth import attach_test_session_cookie, build_test_auth_provider


@pytest.mark.asyncio
async def test_voice_providers_are_visible_through_diagnostics(tmp_path) -> None:
    settings = Settings(
        environment="test",
        api_prefix="/api",
        auth_provider="",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'voice.db'}",
        voice_stt_provider="fake",
        voice_tts_provider="fake",
        voice_realtime_provider="fake",
        voice_turn_detection_provider="fake",
    )
    app = create_app(
        settings,
        overrides=AppOverrides(auth_provider=build_test_auth_provider()),
    )

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            response = await client.get("/api/system/diagnostics")

    response.raise_for_status()
    providers = {item["kind"]: item for item in response.json()["data"]["providers"]}
    assert providers["voice_stt"]["name"] == "fake-stt"
    assert providers["voice_stt"]["available"] is True
    assert providers["voice_tts"]["name"] == "fake-tts"
    assert providers["voice_turn_detection"]["available"] is True


@pytest.mark.asyncio
async def test_voice_required_without_provider_fails_readiness(tmp_path) -> None:
    settings = Settings(
        environment="test",
        api_prefix="/api",
        auth_provider="",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'voice-readiness.db'}",
        voice_required=True,
    )
    app = create_app(
        settings,
        overrides=AppOverrides(auth_provider=build_test_auth_provider()),
    )

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            response = await client.get("/api/health/readiness")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dependency.voice_stt.not_configured"
