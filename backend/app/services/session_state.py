"""SessionState service for managing session configuration.

This module provides the SessionStateService class that handles CRUD
operations for session state, including structured event logging
and integration with the event bus.

Events Emitted:
- session_state.created: When a new session state is created
- session_state.updated: When session state is modified
- session_state.read: When session state is fetched

Usage:
    service = SessionStateService(session=db_session)
    state = await service.get_or_create(session_id)
    await service.update(session_id, behavior="onboarding")
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    InvalidSessionStateError,
    SessionStateConflictError,
    SessionStateNotFoundError,
)
from app.models.session_state import (
    DEFAULT_BEHAVIOR,
    DEFAULT_CONFIG,
    DEFAULT_TOPOLOGY,
    VALID_BEHAVIORS,
    VALID_TOPOLOGIES,
    SessionState,
)
from app.services.events import EventBus
from app.services.logging import get_logger

logger = get_logger(__name__)


class SessionStateService:
    """Service for managing SessionState CRUD operations.

    Provides methods for creating, reading, updating, and deleting
    session state records with event emission and structured logging.

    Attributes:
        session: Database session for operations
        event_bus: Event bus for emitting events (default: global event bus)
    """

    def __init__(
        self,
        session: AsyncSession,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the session state service.

        Args:
            session: Database session for operations
            event_bus: Optional event bus for custom event handling
        """
        self._session = session
        self._event_bus = event_bus or event_bus

    @property
    def session(self) -> AsyncSession:
        """Get the database session."""
        return self._session

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database transactions.

        Yields:
            The database session with automatic commit/rollback.

        Example:
            async with service.transaction() as tx:
                await service.update(session_id, behavior="onboarding")
        """
        try:
            yield self._session
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def get(
        self,
        session_id: UUID,
        for_update: bool = False,
    ) -> SessionState:
        """Get session state by session ID.

        Args:
            session_id: The session UUID to look up
            for_update: Whether to lock the row for update (for transactions)

        Returns:
            The SessionState record

        Raises:
            SessionStateNotFoundError: If no state exists for the session

        Example:
            state = await service.get(session_id)
            logger.info(f"Retrieved state: {state.behavior}")
        """
        query = select(SessionState).where(
            SessionState.session_id == session_id
        )

        if for_update:
            query = query.with_for_update()

        result = await self._session.execute(query)
        state = result.scalar_one_or_none()

        if state is None:
            logger.warning(
                "session_state_not_found",
                extra={"session_id": str(session_id)},
            )
            raise SessionStateNotFoundError(session_id=session_id)

        await self._emit_event(
            "session_state.read",
            session_id=str(session_id),
            topology=state.topology,
            behavior=state.behavior,
        )

        logger.debug(
            "session_state_retrieved",
            extra={
                "session_id": str(session_id),
                "topology": state.topology,
                "behavior": state.behavior,
            },
        )

        return state

    async def get_or_create(
        self,
        session_id: UUID,
        topology: str | None = None,
        behavior: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> SessionState:
        """Get existing session state or create new one.

        This is the primary method for loading session state when a session
        is opened. If state doesn't exist, creates it with defaults or
        specified values.

        Args:
            session_id: The session UUID
            topology: Optional topology override for new state
            behavior: Optional behavior override for new state
            config: Optional config override for new state

        Returns:
            The existing or newly created SessionState

        Example:
            state = await service.get_or_create(
                session_id,
                topology="voice_fast",
                behavior="practice"
            )
        """
        try:
            return await self.get(session_id)
        except SessionStateNotFoundError:
            pass

        state = SessionState(
            session_id=session_id,
            topology=topology or DEFAULT_TOPOLOGY,
            behavior=behavior or DEFAULT_BEHAVIOR,
            config=config or DEFAULT_CONFIG.copy(),
        )

        self._session.add(state)
        await self._session.flush()

        await self._emit_event(
            "session_state.created",
            session_id=str(session_id),
            topology=state.topology,
            behavior=state.behavior,
            config=state.config,
        )

        logger.info(
            "session_state_created",
            extra={
                "session_id": str(session_id),
                "topology": state.topology,
                "behavior": state.behavior,
            },
        )

        return state

    async def create(
        self,
        session_id: UUID,
        topology: str | None = None,
        behavior: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> SessionState:
        """Create new session state.

        Unlike get_or_create, this method only creates and will raise
        an error if state already exists.

        Args:
            session_id: The session UUID
            topology: Topology for the new state (default: chat_fast)
            behavior: Behavior for the new state (default: practice)
            config: Config dict for the new state (default: {})

        Returns:
            The newly created SessionState

        Raises:
            ValueError: If state already exists for the session
        """
        try:
            await self.get(session_id)
            raise ValueError(
                f"Session state already exists for session {session_id}"
            )
        except SessionStateNotFoundError:
            pass

        state = SessionState(
            session_id=session_id,
            topology=topology or DEFAULT_TOPOLOGY,
            behavior=behavior or DEFAULT_BEHAVIOR,
            config=config or DEFAULT_CONFIG.copy(),
        )

        self._session.add(state)
        await self._session.flush()

        await self._emit_event(
            "session_state.created",
            session_id=str(session_id),
            topology=state.topology,
            behavior=state.behavior,
            config=state.config,
        )

        logger.info(
            "session_state_created",
            extra={
                "session_id": str(session_id),
                "topology": state.topology,
                "behavior": state.behavior,
            },
        )

        return state

    async def update(
        self,
        session_id: UUID,
        topology: str | None = None,
        behavior: str | None = None,
        config: dict[str, Any] | None = None,
        expected_version: datetime | None = None,
    ) -> SessionState:
        """Update session state.

        Args:
            session_id: The session UUID
            topology: New topology value (optional)
            behavior: New behavior value (optional)
            config: New config dict (optional, merged with existing)
            expected_version: Optional version for optimistic locking

        Returns:
            The updated SessionState

        Raises:
            SessionStateNotFoundError: If state doesn't exist
            InvalidSessionStateError: If topology/behavior values are invalid
            SessionStateConflictError: If expected_version doesn't match

        Example:
            state = await service.update(
                session_id,
                behavior="onboarding"
            )
        """
        state = await self.get(session_id, for_update=True)

        old_topology = state.topology
        old_behavior = state.behavior
        old_config = state.config.copy() if state.config else {}

        if expected_version and state.updated_at != expected_version:
            raise SessionStateConflictError(
                session_id=session_id,
                expected_version=expected_version,
                actual_version=state.updated_at,
            )

        state.update(
            topology=topology,
            behavior=behavior,
            config=config,
        )

        await self._session.flush()

        await self._emit_event(
            "session_state.updated",
            session_id=str(session_id),
            old_topology=old_topology,
            new_topology=state.topology,
            old_behavior=old_behavior,
            new_behavior=state.behavior,
            config_changed=state.config != old_config,
        )

        logger.info(
            "session_state_updated",
            extra={
                "session_id": str(session_id),
                "old_topology": old_topology,
                "new_topology": state.topology,
                "old_behavior": old_behavior,
                "new_behavior": state.behavior,
            },
        )

        return state

    async def delete(self, session_id: UUID) -> bool:
        """Delete session state.

        Args:
            session_id: The session UUID

        Returns:
            True if deleted, False if not found

        Raises:
            SessionStateNotFoundError: If state doesn't exist
        """
        state = await self.get(session_id)

        await self._session.delete(state)
        await self._session.flush()

        await self._emit_event(
            "session_state.deleted",
            session_id=str(session_id),
            topology=state.topology,
            behavior=state.behavior,
        )

        logger.info(
            "session_state_deleted",
            extra={
                "session_id": str(session_id),
                "topology": state.topology,
                "behavior": state.behavior,
            },
        )

        return True

    async def list_by_behavior(
        self,
        behavior: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SessionState]:
        """List session states by behavior.

        Args:
            behavior: The behavior value to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of SessionState records
        """
        if behavior not in VALID_BEHAVIORS:
            raise InvalidSessionStateError(
                field="behavior",
                value=behavior,
                valid_values=list(VALID_BEHAVIORS),
            )

        query = (
            select(SessionState)
            .where(SessionState.behavior == behavior)
            .order_by(SessionState.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def list_by_topology(
        self,
        topology: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SessionState]:
        """List session states by topology.

        Args:
            topology: The topology value to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of SessionState records
        """
        if topology not in VALID_TOPOLOGIES:
            raise InvalidSessionStateError(
                field="topology",
                value=topology,
                valid_values=list(VALID_TOPOLOGIES),
            )

        query = (
            select(SessionState)
            .where(SessionState.topology == topology)
            .order_by(SessionState.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def _emit_event(
        self,
        event_type: str,
        **kwargs: Any,
    ) -> None:
        """Emit an event to the event bus.

        Args:
            event_type: The event type identifier
            **kwargs: Additional event data
        """
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        if self._event_bus:
            await self._event_bus.emit(event_type, event_data)

        logger.debug(
            "session_state_event",
            extra={"event_type": event_type, **kwargs},
        )


__all__ = [
    "SessionStateService",
]
