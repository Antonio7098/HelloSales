"""Ping/pong WebSocket handler for keepalive."""

import logging
from typing import Any

from fastapi import WebSocket

from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router

logger = logging.getLogger("ws")
router = get_router()


@router.handler("ping")
async def handle_ping(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle ping message - respond with pong.

    This is used for keepalive and connection health checks.
    """
    # Update last ping time
    manager.update_ping(websocket)

    # Respond with pong
    await manager.send_message(websocket, {"type": "pong"})

    logger.debug(
        "Ping/pong",
        extra={"service": "ws", "ws_id": id(websocket)},
    )
