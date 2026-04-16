"""Unit-of-work primitives."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UnitOfWork(Protocol):
    """Minimal async unit-of-work protocol."""

    session: AsyncSession

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class AsyncSqlAlchemyUnitOfWork:
    """Own a single async SQLAlchemy session and transaction boundary."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session is None:
            return
        try:
            if exc_type is not None:
                await self.session.rollback()
        finally:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work session is not active")
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work session is not active")
        await self.session.rollback()


UnitOfWorkFactory = Callable[[], AsyncSqlAlchemyUnitOfWork]


def build_uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> UnitOfWorkFactory:
    """Build a unit-of-work factory."""

    return lambda: AsyncSqlAlchemyUnitOfWork(session_factory)
