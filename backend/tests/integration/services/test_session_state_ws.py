"""Integration tests for session state WebSocket handlers."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


class TestSessionStateHandlers:
    """Integration tests for session.state handlers."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock connection manager."""
        manager = AsyncMock()
        manager.get_connection = MagicMock()
        manager.send_message = AsyncMock()
        manager.send_to_user = AsyncMock()
        return manager

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        websocket = MagicMock()
        return websocket

    @pytest.fixture
    def authenticated_conn(self):
        """Create an authenticated connection."""
        conn = MagicMock()
        conn.authenticated = True
        conn.user_id = uuid4()
        conn.session_id = uuid4()
        return conn

    @pytest.fixture
    def unauthenticated_conn(self):
        """Create an unauthenticated connection."""
        conn = MagicMock()
        conn.authenticated = False
        conn.user_id = None
        conn.session_id = None
        return conn

    @pytest.mark.asyncio
    async def test_state_get_unauthenticated(
        self,
        mock_websocket,
        mock_manager,
        unauthenticated_conn,
    ):
        """Test session.state.get returns error for unauthenticated user."""
        mock_manager.get_connection.return_value = unauthenticated_conn

        from app.api.ws.handlers.session import handle_session_state_get

        payload = {"sessionId": str(uuid4())}
        await handle_session_state_get(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate first",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_state_get_missing_session_id(
        self,
        mock_websocket,
        mock_manager,
        authenticated_conn,
    ):
        """Test session.state.get returns error when sessionId is missing."""
        mock_manager.get_connection.return_value = authenticated_conn

        from app.api.ws.handlers.session import handle_session_state_get

        payload = {}
        await handle_session_state_get(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "sessionId is required",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_state_get_invalid_session_id(
        self,
        mock_websocket,
        mock_manager,
        authenticated_conn,
    ):
        """Test session.state.get returns error for invalid sessionId."""
        mock_manager.get_connection.return_value = authenticated_conn

        from app.api.ws.handlers.session import handle_session_state_get

        payload = {"sessionId": "not-a-uuid"}
        await handle_session_state_get(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Invalid sessionId format",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_state_update_unauthenticated(
        self,
        mock_websocket,
        mock_manager,
        unauthenticated_conn,
    ):
        """Test session.state.update returns error for unauthenticated user."""
        mock_manager.get_connection.return_value = unauthenticated_conn

        from app.api.ws.handlers.session import handle_session_state_update

        payload = {"sessionId": str(uuid4())}
        await handle_session_state_update(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate first",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_state_update_missing_session_id(
        self,
        mock_websocket,
        mock_manager,
        authenticated_conn,
    ):
        """Test session.state.update returns error when sessionId is missing."""
        mock_manager.get_connection.return_value = authenticated_conn

        from app.api.ws.handlers.session import handle_session_state_update

        payload = {}
        await handle_session_state_update(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "sessionId is required",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_state_update_invalid_topology_type(
        self,
        mock_websocket,
        mock_manager,
        authenticated_conn,
    ):
        """Test session.state.update returns error for non-string topology."""
        mock_manager.get_connection.return_value = authenticated_conn

        from app.api.ws.handlers.session import handle_session_state_update

        payload = {"sessionId": str(uuid4()), "topology": 123}
        await handle_session_state_update(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "topology must be a string",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_state_update_invalid_behavior_type(
        self,
        mock_websocket,
        mock_manager,
        authenticated_conn,
    ):
        """Test session.state.update returns error for non-string behavior."""
        mock_manager.get_connection.return_value = authenticated_conn

        from app.api.ws.handlers.session import handle_session_state_update

        payload = {"sessionId": str(uuid4()), "behavior": 123}
        await handle_session_state_update(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "behavior must be a string",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_state_update_invalid_config_type(
        self,
        mock_websocket,
        mock_manager,
        authenticated_conn,
    ):
        """Test session.state.update returns error for non-dict config."""
        mock_manager.get_connection.return_value = authenticated_conn

        from app.api.ws.handlers.session import handle_session_state_update

        payload = {"sessionId": str(uuid4()), "config": "not-a-dict"}
        await handle_session_state_update(mock_websocket, payload, mock_manager)

        mock_manager.send_message.assert_called_once_with(
            mock_websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "config must be a dictionary",
                },
            },
        )
