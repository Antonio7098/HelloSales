from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.config.settings import Settings


async def test_metrics_endpoint_smoke(tmp_path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'smoke-metrics.db'}",
            observability_metrics_enabled=True,
            observability_metrics_endpoint_enabled=True,
        )
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.get("/api/health/liveness")
            response = await client.get("/metrics")

    assert response.status_code == 200
    assert "hello_sales_http_requests_total" in response.text
