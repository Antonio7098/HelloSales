"""WebSocket connection manager - Enterprise Edition."""

import collections
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import WebSocket

from app.api.ws.projector import WSMessageProjector
from app.logging_config import pipeline_run_id_var, request_id_var

logger = logging.getLogger("ws")

# Type aliases for connection settings
PipelineMode = Literal["fast", "accurate", "accurate_filler"]
ModelChoice = Literal["model1", "model2"]
PlatformType = Literal["web", "native"]


@dataclass
class Connection:
    """Represents an active WebSocket connection."""

    websocket: WebSocket
    user_id: UUID | None = None
    session_id: UUID | None = None
    org_id: UUID | None = None  # Enterprise: always set after auth
    connected_at: datetime = field(default_factory=datetime.utcnow)
    authenticated: bool = False
    last_ping: datetime | None = None
    # Per-connection pipeline mode override (None = use server default)
    pipeline_mode: PipelineMode | None = None
    # Per-connection model choice override (None = use server default)
    model_choice: ModelChoice | None = None
    # Client platform hint for this connection ("web" or "native")
    platform: PlatformType | None = None


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        # Map of websocket id -> Connection
        self._connections: dict[int, Connection] = {}
        # Map of user_id -> list of websocket ids
        self._user_connections: dict[UUID, list[int]] = {}
        self._projector = WSMessageProjector()
        self._emit_counts: collections.Counter[str] = collections.Counter()
        self._disconnect_count: int = 0
        self._contract_violation_counts: collections.Counter[str] = collections.Counter()
        self._chat_complete_counts_by_run: collections.Counter[str] = collections.Counter()

    def get_metrics_snapshot(self) -> dict[str, Any]:
        return {
            "disconnect_count": int(self._disconnect_count),
            "emit_counts": dict(self._emit_counts),
            "contract_violation_counts": dict(self._contract_violation_counts),
        }

    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self._connections)

    @property
    def authenticated_count(self) -> int:
        """Get number of authenticated connections."""
        return sum(1 for c in self._connections.values() if c.authenticated)

    async def connect(self, websocket: WebSocket) -> Connection:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket to connect

        Returns:
            Connection object for tracking
        """
        await websocket.accept()
        connection = Connection(websocket=websocket)
        ws_id = id(websocket)
        self._connections[ws_id] = connection

        logger.info(
            "WebSocket connected",
            extra={
                "service": "ws",
                "ws_id": ws_id,
                "connection_count": self.connection_count,
            },
        )
        return connection

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection.

        Args:
            websocket: The WebSocket that disconnected
        """
        ws_id = id(websocket)
        connection = self._connections.pop(ws_id, None)

        self._disconnect_count += 1

        if connection and connection.user_id:
            # Remove from user connections
            user_ws_list = self._user_connections.get(connection.user_id, [])
            if ws_id in user_ws_list:
                user_ws_list.remove(ws_id)
            if not user_ws_list:
                self._user_connections.pop(connection.user_id, None)

        logger.info(
            "WebSocket disconnected",
            extra={
                "service": "ws",
                "ws_id": ws_id,
                "user_id": str(connection.user_id) if connection else None,
                "connection_count": self.connection_count,
            },
        )

    def authenticate(
        self,
        websocket: WebSocket,
        user_id: UUID,
        session_id: UUID | None = None,
    ) -> None:
        """Mark a connection as authenticated.

        Args:
            websocket: The authenticated WebSocket
            user_id: The user's ID
            session_id: The session ID (can be None, will be set on first message)
        """
        ws_id = id(websocket)
        connection = self._connections.get(ws_id)

        if connection:
            connection.user_id = user_id
            connection.session_id = session_id
            connection.authenticated = True

            # Track user connections
            if user_id not in self._user_connections:
                self._user_connections[user_id] = []
            self._user_connections[user_id].append(ws_id)

            logger.info(
                "WebSocket authenticated (enterprise)",
                extra={
                    "service": "ws",
                    "ws_id": ws_id,
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                },
            )

    def get_connection(self, websocket: WebSocket) -> Connection | None:
        """Get connection info for a WebSocket.

        Args:
            websocket: The WebSocket to look up

        Returns:
            Connection if found, None otherwise
        """
        return self._connections.get(id(websocket))

    def update_ping(self, websocket: WebSocket) -> None:
        """Update last ping time for a connection.

        Args:
            websocket: The WebSocket that sent ping
        """
        connection = self._connections.get(id(websocket))
        if connection:
            connection.last_ping = datetime.utcnow()

    def set_pipeline_mode(self, websocket: WebSocket, mode: PipelineMode | None) -> bool:
        """Set the pipeline mode for a connection.

        Args:
            websocket: The WebSocket to update
            mode: Pipeline mode ('fast', 'accurate', 'accurate_filler') or None for default

        Returns:
            True if successful, False if connection not found
        """
        connection = self._connections.get(id(websocket))
        if connection:
            connection.pipeline_mode = mode
            logger.info(
                "Pipeline mode set",
                extra={
                    "service": "ws",
                    "ws_id": id(websocket),
                    "user_id": str(connection.user_id) if connection.user_id else None,
                    "pipeline_mode": mode,
                },
            )
            return True
        return False

    def get_pipeline_mode(self, websocket: WebSocket) -> PipelineMode:
        """Get the effective pipeline mode for a connection.

        Returns the connection's override if set, otherwise the server default.

        Args:
            websocket: The WebSocket to check

        Returns:
            Effective pipeline mode
        """
        from app.config import get_settings

        connection = self._connections.get(id(websocket))
        if connection and connection.pipeline_mode:
            return connection.pipeline_mode
        return get_settings().pipeline_mode

    def set_model_choice(self, websocket: WebSocket, choice: ModelChoice | None) -> bool:
        """Set the model choice for a connection.

        Args:
            websocket: The WebSocket to update
            choice: Model choice ('model1', 'model2') or None for default

        Returns:
            True if successful, False if connection not found
        """
        connection = self._connections.get(id(websocket))
        if connection:
            connection.model_choice = choice
            logger.info(
                "Model choice set",
                extra={
                    "service": "ws",
                    "ws_id": id(websocket),
                    "user_id": str(connection.user_id) if connection.user_id else None,
                    "model_choice": choice,
                },
            )
            return True
        return False

    def get_model_choice(self, websocket: WebSocket) -> ModelChoice:
        """Get the effective model choice for a connection.

        Returns the connection's override if set, otherwise the server default.

        Args:
            websocket: The WebSocket to check

        Returns:
            Effective model choice ('model1' or 'model2')
        """
        from app.config import get_settings

        connection = self._connections.get(id(websocket))
        if connection and connection.model_choice:
            return connection.model_choice
        return get_settings().llm_model_choice

    def get_model_id(self, websocket: WebSocket) -> str:
        """Get the actual Groq model ID for a connection.

        Resolves model choice to the configured model ID.

        Args:
            websocket: The WebSocket to check

        Returns:
            Groq model ID string
        """
        from app.config import get_settings

        settings = get_settings()
        choice = self.get_model_choice(websocket)
        if choice == "model1":
            return settings.llm_model1_id
        return settings.llm_model2_id

    async def send_message(self, websocket: WebSocket, message: dict[str, Any]) -> bool:
        """Send a message to a specific WebSocket.

        Args:
            websocket: Target WebSocket
            message: Message to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            conn = self._connections.get(id(websocket))
            projected = self._projector.project(
                message,
                connection_org_id=getattr(conn, "org_id", None) if conn else None,
                context_request_id=request_id_var.get(),
                context_pipeline_run_id=pipeline_run_id_var.get(),
            )
            msg_type = projected.get("type")
            self._emit_counts[str(msg_type)] += 1

            if msg_type == "chat.complete":
                meta = projected.get("metadata")
                if isinstance(meta, dict) and meta.get("pipeline_run_id"):
                    run_id = str(meta["pipeline_run_id"])
                    self._chat_complete_counts_by_run[run_id] += 1
                    if self._chat_complete_counts_by_run[run_id] > 1:
                        self._contract_violation_counts["duplicate_chat_complete"] += 1

            if msg_type == "status.update":
                payload = projected.get("payload")
                meta = projected.get("metadata")
                if (
                    isinstance(payload, dict)
                    and payload.get("service") == "pipeline"
                    and payload.get("status") in ("completed", "complete")
                    and isinstance(meta, dict)
                    and meta.get("pipeline_run_id")
                ):
                    run_id = str(meta["pipeline_run_id"])
                    if self._chat_complete_counts_by_run.get(run_id, 0) == 0:
                        self._contract_violation_counts["missing_chat_complete"] += 1
            # Check if websocket is still connected before sending
            try:
                if websocket.client_state.name == "DISCONNECTED":
                    logger.debug(
                        f"Skipping send to disconnected websocket: {msg_type}",
                        extra={
                            "service": "ws",
                            "ws_id": id(websocket),
                            "message_type": msg_type,
                        },
                    )
                    return False
            except Exception:
                # If we can't check the state, try sending anyway
                pass

            logger.info(
                f"WS sending: {msg_type}",
                extra={
                    "service": "ws",
                    "ws_id": id(websocket),
                    "message_type": msg_type,
                    "message_type_count": self._emit_counts.get(str(msg_type), 0),
                    "payload_service": projected.get("payload", {}).get("service") if msg_type == "status.update" else None,
                },
            )
            await websocket.send_json(projected)
            logger.info(
                f"WS sent: {msg_type}",
                extra={
                    "service": "ws",
                    "ws_id": id(websocket),
                    "message_type": msg_type,
                    "message_type_count": self._emit_counts.get(str(msg_type), 0),
                },
            )
            return True
        except Exception as e:
            # Don't log errors for expected disconnections
            if "closed" in str(e).lower() or "disconnected" in str(e).lower():
                logger.debug(
                    f"WebSocket already closed when sending {msg_type}: {type(e).__name__}",
                    extra={
                        "service": "ws",
                        "ws_id": id(websocket),
                        "error_type": type(e).__name__,
                    },
                )
            else:
                logger.error(
                    f"Failed to send message {msg_type}: {type(e).__name__}: {e}",
                    extra={
                        "service": "ws",
                        "ws_id": id(websocket),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
            return False

    async def send_to_user(self, user_id: UUID, message: dict[str, Any]) -> int:
        """Send a message to all connections for a user.

        Args:
            user_id: Target user ID
            message: Message to send

        Returns:
            Number of successful sends
        """
        ws_ids = self._user_connections.get(user_id, [])
        sent_count = 0

        for ws_id in ws_ids:
            connection = self._connections.get(ws_id)
            if connection and await self.send_message(connection.websocket, message):
                sent_count += 1

        return sent_count

    async def send_to_user_platform(
        self,
        user_id: UUID,
        platform: PlatformType,
        message: dict[str, Any],
    ) -> int:
        ws_ids = self._user_connections.get(user_id, [])
        sent_count = 0

        for ws_id in ws_ids:
            connection = self._connections.get(ws_id)
            if not connection:
                continue
            if (connection.platform or "native") != platform:
                continue
            if await self.send_message(connection.websocket, message):
                sent_count += 1

        return sent_count

    async def broadcast(self, message: dict[str, Any], authenticated_only: bool = True) -> int:
        """Broadcast a message to all connections.

        Args:
            message: Message to broadcast
            authenticated_only: Only send to authenticated connections

        Returns:
            Number of successful sends
        """
        sent_count = 0

        for connection in self._connections.values():
            if authenticated_only and not connection.authenticated:
                continue
            if await self.send_message(connection.websocket, message):
                sent_count += 1

        return sent_count

    async def disconnect_user(self, user_id: UUID) -> int:
        """Disconnect all active WebSocket connections for a user.

        Sends a final status.update message before closing each connection and
        reuses the standard disconnect bookkeeping.

        Args:
            user_id: Target user ID

        Returns:
            Number of connections disconnected
        """
        ws_ids = list(self._user_connections.get(user_id, []))
        disconnected = 0

        for ws_id in ws_ids:
            connection = self._connections.get(ws_id)
            if not connection:
                continue

            # Best-effort notification to the client
            await self.send_message(
                connection.websocket,
                {
                    "type": "status.update",
                    "payload": {
                        "service": "ws",
                        "status": "disconnected",
                        "metadata": {"reason": "account_deleted"},
                    },
                },
            )

            with contextlib.suppress(Exception):
                # Close the underlying WebSocket and run normal disconnect logic
                # (which will clean up connection maps and logging).
                if connection.websocket.client_state.value == 1:  # CONNECTED
                    await connection.websocket.close(code=1000)
                await self.disconnect(connection.websocket)

            disconnected += 1

        logger.info(
            "User connections disconnected",
            extra={
                "service": "ws",
                "user_id": str(user_id),
                "disconnected_count": disconnected,
            },
        )

        return disconnected


# Global connection manager instance
_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
