"""WebSocket endpoint."""

import asyncio
import contextlib
import logging

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.ai.substrate.events import clear_event_sink
from app.api.ws.manager import get_connection_manager
from app.api.ws.router import get_router
from app.logging_config import clear_request_context

logger = logging.getLogger("ws")


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint handler.

    Handles the connection lifecycle:
    1. Accept connection
    2. Receive and route messages
    3. Handle disconnection
    """
    manager = get_connection_manager()
    router = get_router()

    # Accept connection
    await manager.connect(websocket)

    # Long-running handlers should not block the receive loop, otherwise
    # cancellation and settings updates can't be processed.
    async_message_types = {
        "chat.message",
        "chat.typed",
        "sailwind.practice.message",
    }

    in_flight: set[asyncio.Task[None]] = set()

    def _track_task(task: asyncio.Task[None]) -> None:
        in_flight.add(task)

        def _done(t: asyncio.Task[None]) -> None:
            in_flight.discard(t)
            with contextlib.suppress(asyncio.CancelledError):
                exc = t.exception()
                if exc is not None:
                    logger.error(
                        "WebSocket handler task failed",
                        extra={"service": "ws", "ws_id": id(websocket), "error": str(exc)},
                        exc_info=True,
                    )

        task.add_done_callback(_done)

    try:
        while True:
            # Receive message
            try:
                message = await websocket.receive_json()
            except ValueError as e:
                logger.warning(
                    "Invalid JSON received",
                    extra={"service": "ws", "error": str(e)},
                )
                await manager.send_message(
                    websocket,
                    {
                        "type": "error",
                        "payload": {
                            "code": "INVALID_JSON",
                            "message": "Message must be valid JSON",
                        },
                    },
                )
                continue

            # Route message to handler
            message_type = message.get("type")
            print(f"[DEBUG] WebSocket received message type: {message_type}")
            if message_type in async_message_types:
                _track_task(asyncio.create_task(router.route(websocket, message, manager)))
            else:
                await router.route(websocket, message, manager)

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected by client",
            extra={"service": "ws", "ws_id": id(websocket)},
        )
    except Exception as e:
        logger.error(
            "WebSocket error",
            extra={"service": "ws", "error": str(e)},
            exc_info=True,
        )
        # Try to send error to client if connection is still open
        if websocket.application_state == WebSocketState.CONNECTED:
            with contextlib.suppress(Exception):
                await manager.send_message(
                    websocket,
                    {
                        "type": "error",
                        "payload": {
                            "code": "SERVER_ERROR",
                            "message": "An unexpected error occurred",
                        },
                    },
                )
    finally:
        # Clean up
        if in_flight:
            done, pending = await asyncio.wait(
                in_flight,
                timeout=2.0,
                return_when=asyncio.ALL_COMPLETED,
            )

            for task in pending:
                task.cancel()
            with contextlib.suppress(Exception):
                await asyncio.gather(*pending, return_exceptions=True)

            with contextlib.suppress(Exception):
                await asyncio.gather(*done, return_exceptions=True)
        await manager.disconnect(websocket)
        clear_request_context()
        clear_event_sink()
