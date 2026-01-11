"""Stageflow event sink for WebSocket integration."""

import asyncio
import logging
from typing import Any

from stageflow import EventSink

from app.api.ws.manager import ConnectionManager, get_connection_manager

logger = logging.getLogger("stageflow")


class WebSocketEventSink(EventSink):
    """Event sink that emits stageflow events to WebSocket clients.

    This integrates stageflow's observability with the WebSocket connection
    manager to broadcast pipeline events to connected clients.
    """

    def __init__(self, connection_manager: ConnectionManager | None = None):
        """Initialize the event sink.

        Args:
            connection_manager: Optional connection manager for testing.
                              Defaults to the global connection manager.
        """
        self._connection_manager = connection_manager
        self._queue: asyncio.Queue[tuple[str, dict | None]] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task[None] | None = None

    @property
    def connection_manager(self) -> ConnectionManager:
        """Get the connection manager, lazily loading the global one if needed."""
        if self._connection_manager is None:
            self._connection_manager = get_connection_manager()
        return self._connection_manager

    async def emit(self, *, type: str, data: dict | None = None) -> None:
        """Emit an event to the WebSocket.

        Args:
            type: Event type (e.g., "chat.token", "pipeline.started")
            data: Event payload data
        """
        message = {"type": type, "payload": data or {}}

        # Try to emit immediately to connected clients
        try:
            # The actual emission happens through the pipeline context
            # which is set up by the chat handler
            logger.debug(
                f"Stageflow event: {type}",
                extra={"service": "stageflow", "event_type": type},
            )
        except Exception as e:
            logger.warning(
                f"Failed to emit event {type}: {e}",
                extra={"service": "stageflow", "event_type": type, "error": str(e)},
            )

    def try_emit(self, *, type: str, data: dict | None = None) -> None:
        """Fire-and-forget event emission.

        Args:
            type: Event type
            data: Event payload data
        """
        asyncio.create_task(self.emit(type=type, data=data))

    async def emit_to_user(
        self, user_id: str, *, type: str, data: dict | None = None
    ) -> None:
        """Emit an event to a specific user.

        Args:
            user_id: Target user ID
            type: Event type
            data: Event payload data
        """
        from uuid import UUID

        try:
            user_uuid = UUID(user_id)
            message = {"type": type, "payload": data or {}}
            await self.connection_manager.send_to_user(user_uuid, message)
        except ValueError:
            logger.warning(
                f"Invalid user_id format: {user_id}",
                extra={"service": "stageflow", "user_id": user_id},
            )
        except Exception as e:
            logger.warning(
                f"Failed to emit event to user {user_id}: {e}",
                extra={"service": "stageflow", "user_id": user_id, "error": str(e)},
            )

    async def emit_to_connection(
        self, websocket_id: int, *, type: str, data: dict | None = None
    ) -> None:
        """Emit an event to a specific WebSocket connection.

        Args:
            websocket_id: WebSocket connection ID
            type: Event type
            data: Event payload data
        """
        message = {"type": type, "payload": data or {}}

        # Find the connection and send directly
        connection = self.connection_manager._connections.get(websocket_id)
        if connection:
            await self.connection_manager.send_message(connection.websocket, message)
        else:
            logger.debug(
                f"Connection {websocket_id} not found for event {type}",
                extra={"service": "stageflow", "ws_id": websocket_id, "event_type": type},
            )

    def start(self) -> None:
        """Start the event processing loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._process_events())

    def stop(self) -> None:
        """Stop the event processing loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                type, data = await self._queue.get()
                # Process event (currently just logs)
                logger.debug(
                    f"Processed queued event: {type}",
                    extra={"service": "stageflow", "event_type": type},
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error processing event: {e}",
                    extra={"service": "stageflow", "error": str(e)},
                )
