from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.shared.auth import APP_ACCESS_PERMISSION
from tests.support.auth import attach_test_session_cookie, build_test_auth_provider


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}",
        frontend_app_url="http://frontend.test",
    )


@pytest.mark.asyncio
async def test_protected_api_requires_authentication(tmp_path: Path) -> None:
    app = create_app(
        _settings(tmp_path),
        overrides=AppOverrides(auth_provider=build_test_auth_provider()),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/system/diagnostics")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.unauthenticated"


@pytest.mark.asyncio
async def test_protected_api_rejects_missing_permission(tmp_path: Path) -> None:
    app = create_app(
        _settings(tmp_path),
        overrides=AppOverrides(
            auth_provider=build_test_auth_provider(permissions=(APP_ACCESS_PERMISSION,))
        ),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            response = await client.get("/api/system/diagnostics")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "auth.permission_denied"


@pytest.mark.asyncio
async def test_session_endpoint_returns_current_auth_context(tmp_path: Path) -> None:
    app = create_app(
        _settings(tmp_path),
        overrides=AppOverrides(auth_provider=build_test_auth_provider()),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            response = await client.get("/api/auth/session")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["actor_id"] == "user_test_123"
    assert payload["org_id"] == "org_test_123"
    assert payload["email"] == "seller@example.test"
    assert APP_ACCESS_PERMISSION in payload["permissions"]


@pytest.mark.asyncio
async def test_auth_callback_sets_session_cookie_and_redirects_to_safe_return_path(
    tmp_path: Path,
) -> None:
    app = create_app(
        _settings(tmp_path),
        overrides=AppOverrides(auth_provider=build_test_auth_provider()),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            response = await client.get("/api/auth/callback?code=good-code&state=/sessions")

    assert response.status_code == 302
    assert response.headers["location"] == "http://frontend.test/sessions"
    assert "hello_sales_session=test-session" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_logout_clears_session_cookie_and_returns_provider_redirect(tmp_path: Path) -> None:
    app = create_app(
        _settings(tmp_path),
        overrides=AppOverrides(auth_provider=build_test_auth_provider()),
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            attach_test_session_cookie(client)
            response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json()["data"]["redirect_url"] == "https://auth.example.test/logout"
    assert "hello_sales_session=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]
