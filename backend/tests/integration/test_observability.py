from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.config.settings import Settings


@pytest.mark.asyncio
async def test_metrics_endpoint_is_operational_and_observability_state_is_visible(
    tmp_path: Path,
) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'metrics.db'}",
            observability_metrics_enabled=True,
            observability_metrics_endpoint_enabled=True,
            observability_tracing_enabled=True,
            observability_tracing_exporter="none",
        )
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=True)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            readiness = await client.get("/api/health/readiness")
            diagnostics = await client.get("/api/system/diagnostics")
            metrics = await client.get("/metrics")

    assert readiness.status_code == 200
    assert diagnostics.status_code == 200
    diagnostics_payload = diagnostics.json()["data"]
    assert diagnostics_payload["observability"]["metrics"]["enabled"] is True
    assert diagnostics_payload["observability"]["metrics"]["endpoint_path"] == "/metrics"
    assert diagnostics_payload["observability"]["tracing"]["enabled"] is True

    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    body = metrics.text
    assert "hello_sales_http_requests_total" in body
    assert 'route="/api/health/readiness"' in body
    assert "hello_sales_health_overall_status" in body


@pytest.mark.asyncio
async def test_metrics_endpoint_records_http_failures(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'failure-metrics.db'}",
            observability_metrics_enabled=True,
            observability_metrics_endpoint_enabled=True,
        )
    )
    router = APIRouter()

    @router.get("/crash")
    async def crash() -> None:
        raise RuntimeError("boom")

    app.include_router(router, prefix="/test-errors")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/test-errors/crash")
            metrics = await client.get("/metrics")

    assert response.status_code == 500
    assert 'hello_sales_http_requests_total{method="GET",outcome="failure",route="/test-errors/crash",status_code="500"} 1.0' in metrics.text
