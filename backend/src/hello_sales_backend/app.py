"""Application factory and ASGI entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from hello_sales_backend.entrypoints.http.error_handlers import register_error_handlers
from hello_sales_backend.entrypoints.http.router import api_router
from hello_sales_backend.platform.composition.app_container import AppContainer, build_app_container
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.composition.startup import bootstrap_container, shutdown_container
from hello_sales_backend.platform.config.settings import Settings, get_settings
from hello_sales_backend.platform.observability.logging import configure_logging
from hello_sales_backend.platform.observability.middleware import RequestContextMiddleware


def create_app(
    settings: Settings | None = None,
    container: AppContainer | None = None,
    overrides: AppOverrides | None = None,
) -> FastAPI:
    """Create a configured FastAPI application."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level, resolved_settings.environment)
    resolved_container = container or build_app_container(resolved_settings, overrides=overrides)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await bootstrap_container(resolved_container)
        try:
            yield
        finally:
            await shutdown_container(resolved_container)

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="HelloSales backend foundation scaffold",
        lifespan=lifespan,
    )
    app.state.container = resolved_container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware, observability=resolved_container.observability)
    register_error_handlers(app)
    app.include_router(api_router, prefix=resolved_settings.api_prefix)

    @app.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        return {
            "name": resolved_settings.app_name,
            "version": resolved_settings.app_version,
            "environment": resolved_settings.environment,
        }

    if resolved_settings.observability_metrics_endpoint_enabled:

        @app.get(
            resolved_settings.observability_metrics_endpoint_path,
            include_in_schema=False,
        )
        async def metrics() -> Response:
            # This stays at the app root because it is an operational surface,
            # not a product endpoint under the `/api` router tree.
            payload, media_type = resolved_container.observability.render_metrics()
            return Response(content=payload, media_type=media_type)

    return app


app = create_app()
