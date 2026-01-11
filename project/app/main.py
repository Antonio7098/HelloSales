"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.infrastructure.database import close_db, init_db
from app.infrastructure.middleware import (
    RequestContextMiddleware,
    error_handler_middleware,
)
from app.infrastructure.telemetry import configure_logging, get_logger
from app.infrastructure.telemetry.metrics import set_service_info
from app.infrastructure.telemetry.tracing import (
    configure_tracing,
    instrument_fastapi,
    instrument_httpx,
    shutdown_tracing,
)
from app.presentation.http import api_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()

    # Startup
    logger.info(
        "Starting HelloSales backend",
        extra={
            "version": settings.version,
            "environment": settings.environment,
        },
    )

    # Initialize database
    await init_db(settings)
    logger.info("Database connection initialized")

    yield

    # Shutdown
    logger.info("Shutting down HelloSales backend")
    await close_db()
    shutdown_tracing()
    logger.info("Database connection closed")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override for testing

    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()

    # Configure logging
    configure_logging(
        level=settings.log_level,
        format_type=settings.log_format,
        service_name=settings.otel_service_name,
    )

    # Configure OpenTelemetry tracing
    configure_tracing(
        service_name=settings.otel_service_name,
        service_version=settings.version,
        environment=settings.environment,
        otlp_endpoint=settings.otlp_endpoint if settings.otlp_endpoint else None,
    )

    # Set service info for metrics
    set_service_info(
        version=settings.version,
        environment=settings.environment,
    )

    # Instrument httpx for tracing
    instrument_httpx()

    # Create FastAPI app
    app = FastAPI(
        title="HelloSales API",
        description="AI-powered sales content platform",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # Instrument FastAPI for tracing
    instrument_fastapi(app)

    # Add middleware (order matters - last added is first executed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    # Register error handlers
    error_handler_middleware(app)

    # Include API routes
    app.include_router(api_router)

    return app


# Default app instance for uvicorn
app = create_app()
