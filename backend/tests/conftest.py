from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
src_str = str(SRC_PATH)
if src_str not in sys.path:
    sys.path.insert(0, src_str)

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.config.settings import Settings


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        cors_allowed_origins=("http://testserver",),
    )


@pytest.fixture()
def app(test_settings: Settings):
    return create_app(test_settings)


@pytest_asyncio.fixture()
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as async_client:
            yield async_client
