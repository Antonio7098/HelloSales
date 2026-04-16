from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from hello_sales_backend.app import create_app
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.shared.errors import AppError, app_error


@pytest.mark.asyncio
async def test_structured_app_errors_include_operational_context(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'errors.db'}",
    )
    app = create_app(settings)
    router = APIRouter()

    @router.get("/boom")
    async def boom() -> None:
        raise app_error(
            "Provider timed out",
            code="provider.timeout",
            category="provider",
            status_code=502,
            retryable=True,
            details={"provider": "fake", "timeout_seconds": 3},
            operation="provider.llm.generate",
            component="provider",
        )

    app.include_router(router, prefix="/test-errors")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/test-errors/boom", headers={"x-request-id": "req-123", "x-trace-id": "tr-456"})
            diagnostics = await client.get("/api/system/diagnostics")

    assert response.status_code == 502
    payload = response.json()["error"]
    assert payload["code"] == "provider.timeout"
    assert payload["category"] == "provider"
    assert payload["retryable"] is True
    assert payload["correlation_id"] == "req-123"
    assert payload["trace_id"] == "tr-456"
    assert payload["details"]["provider"] == "fake"
    diagnostics_payload = diagnostics.json()["data"]
    assert any(event["code"] == "provider.timeout" for event in diagnostics_payload["events"])
    assert any(alert["code"] == "provider.timeout" for alert in diagnostics_payload["alerts"])


@pytest.mark.asyncio
async def test_unhandled_exceptions_are_returned_as_internal_errors(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'unexpected.db'}",
    )
    app = create_app(settings)
    router = APIRouter()

    @router.get("/crash")
    async def crash() -> None:
        raise RuntimeError("unexpected boom")

    app.include_router(router, prefix="/test-errors")

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/test-errors/crash")
            diagnostics = await client.get("/api/system/diagnostics")

    assert response.status_code == 500
    payload = response.json()["error"]
    assert payload["code"] == "internal.unhandled_exception"
    assert payload["category"] == "internal"
    assert payload["details"]["exception_type"] == "RuntimeError"
    diagnostics_payload = diagnostics.json()["data"]
    assert any(event["code"] == "internal.unhandled_exception" for event in diagnostics_payload["events"])
    assert any(alert["code"] == "internal.unhandled_exception" for alert in diagnostics_payload["alerts"])


@pytest.mark.asyncio
async def test_partial_llm_configuration_fails_startup(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'startup.db'}",
            generic_agent_provider="openai-compatible",
            generic_agent_model="test-model",
        )
    )

    with pytest.raises(AppError) as exc_info:
        async with app.router.lifespan_context(app):
            pass

    assert exc_info.value.code == "config.llm_provider.partial"
    assert exc_info.value.category == "config"


@pytest.mark.asyncio
async def test_generic_agent_provider_without_provider_key_fails_startup(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'generic-provider.db'}",
            generic_agent_provider="groq",
            generic_agent_model="openai/gpt-oss-20b",
        )
    )

    with pytest.raises(AppError) as exc_info:
        async with app.router.lifespan_context(app):
            pass

    assert exc_info.value.code == "config.llm_provider.partial"
    assert exc_info.value.category == "config"


@pytest.mark.asyncio
async def test_unsupported_generic_agent_provider_fails_startup(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            environment="test",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'unsupported-provider.db'}",
            generic_agent_provider="unknown-provider",
            generic_agent_model="test-model",
        )
    )

    with pytest.raises(AppError) as exc_info:
        async with app.router.lifespan_context(app):
            pass

    assert exc_info.value.code == "config.llm_provider.unsupported"
    assert exc_info.value.category == "config"
