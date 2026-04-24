from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
src_str = str(SRC_PATH)
if src_str not in sys.path:
    sys.path.insert(0, src_str)

from hello_sales_backend.app import create_app  # noqa: E402
from hello_sales_backend.platform.composition.overrides import AppOverrides  # noqa: E402
from hello_sales_backend.platform.config.settings import Settings  # noqa: E402
from hello_sales_backend.shared.auth import AuthContext  # noqa: E402
from tests.support.auth import (  # noqa: E402
    FakeAuthProvider,
    attach_test_session_cookie,
    build_test_auth_context,
    build_test_auth_provider,
)


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        cors_allowed_origins=("http://testserver",),
    )


@pytest.fixture()
def test_auth_context() -> AuthContext:
    return build_test_auth_context()


@pytest.fixture()
def test_auth_provider(test_auth_context: AuthContext) -> FakeAuthProvider:
    return build_test_auth_provider()


@pytest.fixture()
def app(test_settings: Settings, test_auth_provider: FakeAuthProvider) -> FastAPI:
    return create_app(test_settings, overrides=AppOverrides(auth_provider=test_auth_provider))


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as async_client:
            attach_test_session_cookie(async_client)
            yield async_client
