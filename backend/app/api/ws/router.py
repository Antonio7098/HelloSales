"""WebSocket message router."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket

from app.api.ws.manager import ConnectionManager

logger = logging.getLogger("ws")

# Type alias for message handlers
MessageHandler = Callable[[WebSocket, dict[str, Any], ConnectionManager], Awaitable[None]]


class MessageRouter:
    """Routes WebSocket messages to appropriate handlers."""

    def __init__(self):
        self._handlers: dict[str, MessageHandler] = {}

    def register(self, message_type: str, handler: MessageHandler) -> None:
        """Register a handler for a message type.

        Args:
            message_type: The message type to handle (e.g., 'auth', 'ping')
            handler: Async function to handle the message
        """
        self._handlers[message_type] = handler
        logger.debug(
            "Handler registered",
            extra={"service": "ws", "message_type": message_type},
        )

    def handler(self, message_type: str) -> Callable[[MessageHandler], MessageHandler]:
        """Decorator to register a message handler.

        Usage:
            @router.handler("auth")
            async def handle_auth(websocket, payload, manager):
                ...
        """

        def decorator(func: MessageHandler) -> MessageHandler:
            self.register(message_type, func)
            return func

        return decorator

    async def route(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
        manager: ConnectionManager,
    ) -> None:
        """Route a message to its handler.

        Args:
            websocket: The WebSocket that sent the message
            message: The parsed message dict
            manager: Connection manager instance
        """
        message_type = message.get("type")

        if not message_type:
            logger.warning(
                "Message missing type field",
                extra={"service": "ws", "ws_id": id(websocket)},
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "INVALID_MESSAGE",
                        "message": "Message must include 'type' field",
                    },
                },
            )
            return

        handler = self._handlers.get(message_type)

        if not handler:
            logger.warning(
                "Unknown message type",
                extra={
                    "service": "ws",
                    "ws_id": id(websocket),
                    "message_type": message_type,
                },
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "UNKNOWN_MESSAGE_TYPE",
                        "message": f"Unknown message type: {message_type}",
                    },
                },
            )
            return

        logger.debug(
            "Routing message",
            extra={
                "service": "ws",
                "ws_id": id(websocket),
                "message_type": message_type,
            },
        )

        try:
            await handler(websocket, message.get("payload", {}), manager)
        except Exception as e:
            logger.error(
                "Handler error",
                extra={
                    "service": "ws",
                    "ws_id": id(websocket),
                    "message_type": message_type,
                    "error": str(e),
                },
                exc_info=True,
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "HANDLER_ERROR",
                        "message": "An error occurred processing your request",
                        "requestId": message.get("requestId"),
                    },
                },
            )


# Global router instance
_router: MessageRouter | None = None
_handlers_imported: bool = False


def get_router() -> MessageRouter:
    """Get global message router instance.

    On first call, creates the router and imports all handlers.
    On subsequent calls, returns the same router instance.
    """
    global _router, _handlers_imported

    if _router is None:
        _router = MessageRouter()

    if not _handlers_imported:
        _import_handlers()
        _handlers_imported = True

    return _router


def _import_handlers() -> None:
    """Import all handler modules to register their handlers.

    This is done lazily on first get_router() call to avoid
    circular import issues at module load time.
    """
    from app.api.ws.handlers import (  # noqa: F401
        assessment,
        auth,
        chat,
        feedback,
        ping,
        pipeline,
        profile,
        sailwind_practice,
        session,
        settings,
        skills,
        voice,
    )

    registered_types = list(_router._handlers.keys())
    logger.info(
        "Handlers registered",
        extra={
            "service": "ws",
            "handlers": registered_types,
            "count": len(registered_types),
        },
    )
    voice_handlers = [h for h in registered_types if h.startswith("voice.")]
    if voice_handlers:
        logger.info(
            "Voice handlers registered",
            extra={"service": "ws", "voice_handlers": voice_handlers},
        )
