"""Integration tests for WebSocket endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestWebSocketConnection:
    """Test WebSocket connection lifecycle."""

    def test_websocket_connect(self, client):
        """Test WebSocket connection is accepted."""
        with client.websocket_connect("/ws") as websocket:
            # Connection should be accepted
            assert websocket is not None

    def test_ping_pong(self, client):
        """Test ping/pong keepalive."""
        with client.websocket_connect("/ws") as websocket:
            # Send ping
            websocket.send_json({"type": "ping"})

            # Should receive pong
            response = websocket.receive_json()
            assert response["type"] == "pong"

    def test_auth_with_dev_token(self, client):
        """Test authentication with development token."""
        with client.websocket_connect("/ws") as websocket:
            # Send auth with dev token
            websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})

            # Should receive auth.success
            response = websocket.receive_json()
            assert response["type"] == "auth.success"
            assert "userId" in response["payload"]
            # sessionId is null until first message
            assert "sessionId" in response["payload"]
            assert response["payload"]["sessionId"] is None

    def test_invalid_message_type(self, client):
        """Test handling of unknown message type."""
        with client.websocket_connect("/ws") as websocket:
            # Send unknown message type
            websocket.send_json({"type": "unknown_type"})

            # Should receive error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert response["payload"]["code"] == "UNKNOWN_MESSAGE_TYPE"

    def test_missing_type_field(self, client):
        """Test handling of message without type field."""
        with client.websocket_connect("/ws") as websocket:
            # Send message without type
            websocket.send_json({"payload": "test"})

            # Should receive error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert response["payload"]["code"] == "INVALID_MESSAGE"

    def test_auth_then_status_update(self, client):
        """Test that auth triggers status update."""
        with client.websocket_connect("/ws") as websocket:
            # Authenticate
            websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})

            # Receive auth.success
            response = websocket.receive_json()
            assert response["type"] == "auth.success"

            # Should also receive status.update
            response = websocket.receive_json()
            assert response["type"] == "status.update"
            assert response["payload"]["service"] == "ws"
            assert response["payload"]["status"] == "connected"


class TestWebSocketAuth:
    """Test WebSocket authentication flows."""

    def test_auth_creates_user(self, client):
        """Test that auth creates a user record."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})

            response = websocket.receive_json()
            assert response["type"] == "auth.success"

            # User ID should be a valid UUID format
            user_id = response["payload"]["userId"]
            assert len(user_id) == 36  # UUID format
            assert user_id.count("-") == 4

    def test_auth_defers_session_creation(self, client):
        """Test that auth does NOT create a session (deferred to first message)."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})

            response = websocket.receive_json()
            assert response["type"] == "auth.success"

            # Session ID should be null (created on first message)
            assert response["payload"]["sessionId"] is None

    def test_auth_missing_token(self, client):
        """Test auth without token returns error."""
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "auth", "payload": {}})

            response = websocket.receive_json()
            assert response["type"] == "auth.error"
            assert "code" in response["payload"]
