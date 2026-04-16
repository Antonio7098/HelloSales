from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.config.settings import Settings

pytestmark = pytest.mark.postgres


@pytest.mark.skipif(
    os.getenv("HELLO_SALES_RUN_POSTGRES_TESTS") != "1",
    reason="Set HELLO_SALES_RUN_POSTGRES_TESTS=1 to run PostgreSQL integration tests.",
)
async def test_postgres_readiness_against_real_database() -> None:
    database_url = os.getenv(
        "HELLO_SALES_POSTGRES_TEST_DATABASE_URL",
        "postgresql+asyncpg://hello_sales:hello_sales@localhost:5432/hello_sales",
    )
    app = create_app(Settings(environment="test", database_url=database_url))

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/health/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ready"
    assert payload["data"]["database"] == "ok"
