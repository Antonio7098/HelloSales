"""Unit tests for feedback WebSocket handlers.

These tests exercise validation and basic error handling without touching
real database state (services are invoked against an in-memory session
via get_session_context).
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestFeedbackWSHandlers:
    @patch("app.api.ws.handlers.feedback.FeedbackService")
    def test_message_flag_without_session_id_uses_connection_session(
        self, mock_service: AsyncMock, client: TestClient
    ) -> None:
        """When sessionId is omitted but connection has a session, handler should accept."""
        # Mock the service method to avoid DB constraints
        mock_service.return_value.create_message_flag = AsyncMock(return_value=AsyncMock())

        with client.websocket_connect("/ws") as websocket:
            # Auth to create a user and attach a session on first message
            websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
            auth_resp = websocket.receive_json()
            assert auth_resp["type"] == "auth.success"

            status_msg = websocket.receive_json()
            assert status_msg["type"] == "status.update"

            # Send a minimal valid feedback.message_flag without explicit sessionId
            websocket.send_json(
                {
                    "type": "feedback.message_flag",
                    "payload": {
                        "interactionId": "00000000-0000-0000-0000-000000000001",
                        "role": "assistant",
                        "category": "bad_assistant",
                        "name": "Bad answer",
                    },
                }
            )

            resp = websocket.receive_json()
            assert resp["type"] == "feedback.ack"
            assert resp["payload"]["success"] is True

    def test_feedback_message_flag_validation_error_returns_error(self, client: TestClient) -> None:
        """Invalid payload for feedback.message_flag should yield an error response."""

        with client.websocket_connect("/ws") as websocket:
            # Auth first
            websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
            websocket.receive_json()  # auth.success
            websocket.receive_json()  # status.update

            # Missing required fields like interactionId and name
            websocket.send_json(
                {
                    "type": "feedback.message_flag",
                    "payload": {"category": "bad_assistant", "role": "assistant"},
                }
            )

            resp = websocket.receive_json()
            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "INVALID_PAYLOAD"

    @patch("app.api.ws.handlers.feedback.FeedbackService")
    def test_feedback_message_flag_supports_triage_incorrect_category(
        self, mock_service: AsyncMock, client: TestClient
    ) -> None:
        """feedback.message_flag should accept category=triage_incorrect."""
        # Mock the service method to avoid DB constraints
        mock_service.return_value.create_message_flag = AsyncMock(return_value=AsyncMock())

        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
            websocket.receive_json()  # auth.success
            websocket.receive_json()  # status.update

            websocket.send_json(
                {
                    "type": "feedback.message_flag",
                    "payload": {
                        "interactionId": "00000000-0000-0000-0000-000000000002",
                        "role": "assistant",
                        "category": "triage_incorrect",
                        "name": "Triage was wrong",
                    },
                }
            )

            resp = websocket.receive_json()
            assert resp["type"] == "feedback.ack"
            assert resp["payload"]["success"] is True
