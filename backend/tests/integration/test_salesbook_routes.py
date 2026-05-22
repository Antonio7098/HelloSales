from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from hello_sales_backend.app import create_app
from hello_sales_backend.modules.salesbook.permissions import (
    ONBOARDING_READ_PERMISSION,
    ONBOARDING_WRITE_PERMISSION,
)
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.shared.auth import (
    APP_ACCESS_PERMISSION,
    SESSIONS_READ_ANY_PERMISSION,
    SESSIONS_READ_PERMISSION,
    SESSIONS_WRITE_ANY_PERMISSION,
    SESSIONS_WRITE_PERMISSION,
)
from tests.support.auth import attach_test_session_cookie, build_test_auth_provider


@pytest.fixture()
def salesbook_test_settings(tmp_path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'salesbook-routes.db'}",
        cors_allowed_origins=("http://testserver",),
    )


@pytest.fixture()
def salesbook_app(salesbook_test_settings: Settings) -> FastAPI:
    auth_provider = build_test_auth_provider(
        permissions=(
            APP_ACCESS_PERMISSION,
            SESSIONS_READ_PERMISSION,
            SESSIONS_WRITE_PERMISSION,
            SESSIONS_READ_ANY_PERMISSION,
            SESSIONS_WRITE_ANY_PERMISSION,
            ONBOARDING_READ_PERMISSION,
            ONBOARDING_WRITE_PERMISSION,
        )
    )
    return create_app(salesbook_test_settings, overrides=AppOverrides(auth_provider=auth_provider))


@pytest_asyncio.fixture()
async def salesbook_client(salesbook_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with salesbook_app.router.lifespan_context(salesbook_app):
        transport = httpx.ASGITransport(app=salesbook_app, raise_app_exceptions=True)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            attach_test_session_cookie(async_client)
            yield async_client


@pytest.mark.asyncio
async def test_salesbook_registry_route_returns_questions(salesbook_client: httpx.AsyncClient) -> None:
    response = await salesbook_client.get("/api/salesbook/onboarding/registry?phase=1")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert "questions" in payload
    assert payload["questions"]


@pytest.mark.asyncio
async def test_salesbook_contact_route_round_trips_via_http(salesbook_client: httpx.AsyncClient) -> None:
    put_response = await salesbook_client.put(
        "/api/salesbook/clients/profile-1/contact",
        json={
            "primary_email": "http@example.com",
            "contact_name": "HTTP Contact",
            "contact_role": "CEO",
            "phone": "+15550000",
            "company_size": "1-10",
            "geography": "US",
            "status": "active",
        },
    )

    assert put_response.status_code == 200
    get_response = await salesbook_client.get("/api/salesbook/clients/profile-1/contact")

    assert get_response.status_code == 200
    payload = get_response.json()["data"]
    assert payload["primary_email"] == "http@example.com"
    assert payload["contact_name"] == "HTTP Contact"
