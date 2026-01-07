"""Database connection and session management (infrastructure layer)."""

import logging
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger("db")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Engine will be created on startup
_engine = None
_async_session_factory = None
_sync_engine = None
_sync_session_factory = None


async def dispose_async_engine() -> None:
    """Dispose the async engine if it exists (for tests)."""

    global _engine
    if _engine is not None:
        await _engine.dispose()
    _engine = None


def reset_async_session_factory() -> None:
    """Clear cached async session factory (for tests)."""

    global _async_session_factory
    _async_session_factory = None


def reset_sync_session_factory() -> None:
    """Clear cached sync session factory (for tests)."""

    global _sync_session_factory
    _sync_session_factory = None


def get_engine():
    """Get the SQLAlchemy async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        engine_kwargs = {
            "echo": settings.is_development,
            "pool_pre_ping": True,
        }
        if settings.database_disable_pooling:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update({"pool_size": 5, "max_overflow": 10})
        _engine = create_async_engine(
            settings.database_url,
            **engine_kwargs,
        )
        logger.info(
            "Database engine created",
            extra={
                "service": "db",
                "database": settings._redact_url(settings.database_url),
            },
        )
    return _engine


def get_sync_engine():
    """Get the SQLAlchemy sync engine."""
    global _sync_engine
    if _sync_engine is None:
        settings = get_settings()
        engine_kwargs = {
            "echo": settings.is_development,
            "pool_pre_ping": True,
        }
        if settings.database_disable_pooling:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.update({"pool_size": 5, "max_overflow": 10})
        _sync_engine = create_engine(
            settings.database_url,
            **engine_kwargs,
        )
        logger.info(
            "Sync database engine created",
            extra={
                "service": "db",
                "database": settings._redact_url(settings.database_url),
            },
        )
    return _sync_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


def get_sync_session_factory():
    """Get the sync session factory."""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _sync_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions.

    Usage:
        @app.get("/users")
        async def get_users(session: AsyncSession = Depends(get_session)):
            ...
    """

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting database sessions.

    Usage:
        async with get_session_context() as session:
            ...
    """

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def get_sync_session_context() -> Generator:
    """Context manager for getting synchronous database sessions.

    Usage:
        with get_sync_session_context() as session:
            ...
    """

    factory = get_sync_session_factory()
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


async def init_db() -> None:
    """Initialize database connection (call on startup)."""
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Database connection failed during init",
            extra={"service": "db", "error": str(exc)},
        )
        return
    logger.info("Database connection verified", extra={"service": "db"})


async def close_db() -> None:
    """Close database connection (call on shutdown)."""
    global _engine, _async_session_factory, _sync_engine, _sync_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
        _sync_session_factory = None
    logger.info("Database connections closed", extra={"service": "db"})


__all__ = [
    "Base",
    "get_engine",
    "get_sync_engine",
    "get_session_factory",
    "get_sync_session_factory",
    "get_session",
    "get_session_context",
    "get_sync_session_context",
    "init_db",
    "close_db",
]
