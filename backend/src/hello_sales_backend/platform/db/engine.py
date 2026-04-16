"""Async engine factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from hello_sales_backend.platform.config.settings import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    """Build the application async engine."""

    return create_async_engine(
        settings.database_url,
        future=True,
        pool_pre_ping=not settings.database_url.startswith("sqlite"),
    )
