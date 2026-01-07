"""Integration tests for assessment WebSocket handlers and feature gate."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for WebSocket tests."""
    return TestClient(app)


def _set_assessment_enabled(enabled: bool) -> None:
    """Helper to flip assessment_enabled on the cached settings object.

    This relies on get_settings() returning a cached instance; we mutate it
    in-place for the duration of the test process.
    """

    settings = get_settings()
    # type: ignore[attr-defined] - we know this field exists
    settings.assessment_enabled = enabled  # pragma: no cover - simple setter


def test_assessment_trigger_gate_off_returns_error(client: TestClient):
    """When assessment_enabled is false, assessment.trigger should error and not run."""

    _set_assessment_enabled(False)

    with client.websocket_connect("/ws") as websocket:
        # Dev auth
        websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        auth_response = websocket.receive_json()
        assert auth_response["type"] == "auth.success"

        # Consume initial status.update (ws: connected), same pattern as other WS tests
        status_msg = websocket.receive_json()
        assert status_msg["type"] == "status.update"

        # Even with a fake session UUID, gate should short-circuit before any work.
        payload = {
            "type": "assessment.trigger",
            "payload": {
                "sessionId": auth_response["payload"].get("sessionId")
                or "00000000-0000-0000-0000-000000000000",
            },
        }
        websocket.send_json(payload)

        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["payload"]["code"] == "ASSESSMENT_DISABLED"


def test_assessment_history_gate_off_returns_error(client: TestClient):
    """When assessment_enabled is false, assessment.history should error and not run."""

    _set_assessment_enabled(False)

    with client.websocket_connect("/ws") as websocket:
        # Dev auth
        websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        auth_response = websocket.receive_json()
        assert auth_response["type"] == "auth.success"

        # Consume initial status.update (ws: connected)
        status_msg = websocket.receive_json()
        assert status_msg["type"] == "status.update"

        websocket.send_json({"type": "assessment.history", "payload": {"limit": 5}})
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert response["payload"]["code"] == "ASSESSMENT_DISABLED"
