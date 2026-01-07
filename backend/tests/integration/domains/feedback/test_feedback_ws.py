"""Integration tests for feedback WebSocket handlers."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _auth_with_dev_token(websocket) -> None:
    """Authenticate using the dev token path (mirrors profile WS tests)."""

    websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
    resp = websocket.receive_json()
    assert resp["type"] == "auth.success"

    status_msg = websocket.receive_json()
    assert status_msg["type"] == "status.update"
    assert status_msg["payload"]["service"] == "ws"
    assert status_msg["payload"]["status"] == "connected"


class TestFeedbackWebSocket:
    def test_message_flag_requires_auth(self, client: TestClient) -> None:
        """feedback.message_flag without auth should return NOT_AUTHENTICATED error."""

        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "feedback.message_flag", "payload": {}})
            resp = websocket.receive_json()

            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "NOT_AUTHENTICATED"

    def test_feedback_report_creates_ack(self, client: TestClient) -> None:
        """feedback.report after auth should return a feedback.ack with an id."""

        with client.websocket_connect("/ws") as websocket:
            _auth_with_dev_token(websocket)

            websocket.send_json(
                {
                    "type": "feedback.report",
                    "payload": {
                        "category": "bug",
                        "name": "App crash",
                        "description": "Crashed on open",
                        "scope": "app",
                        "timeBucket": "just_now",
                        "requestId": "req-123",
                    },
                }
            )

            resp = websocket.receive_json()
            assert resp["type"] == "feedback.ack"
            payload = resp["payload"]
            assert payload["success"] is True
            assert isinstance(payload["feedbackId"], str)
            assert payload["requestId"] == "req-123"
