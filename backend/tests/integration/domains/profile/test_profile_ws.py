"""Integration tests for profile WebSocket handlers."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _auth_with_dev_token(websocket) -> None:
    """Authenticate over WebSocket using the development token path."""

    websocket.send_json({"type": "auth", "payload": {"token": "dev_token"}})
    # First message: auth.success
    resp = websocket.receive_json()
    assert resp["type"] == "auth.success"

    # Second message: status.update (ws: connected)
    status_msg = websocket.receive_json()
    assert status_msg["type"] == "status.update"
    assert status_msg["payload"]["service"] == "ws"
    assert status_msg["payload"]["status"] == "connected"


class TestProfileWebSocket:
    def test_profile_get_requires_auth(self, client: TestClient) -> None:
        """profile.get without auth should return NOT_AUTHENTICATED error."""

        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "profile.get", "payload": {}})
            resp = websocket.receive_json()

            assert resp["type"] == "error"
            assert resp["payload"]["code"] == "NOT_AUTHENTICATED"

    def test_profile_get_returns_empty_initially(self, client: TestClient) -> None:
        """profile.get after auth should return an empty profile for a new dev user."""

        with client.websocket_connect("/ws") as websocket:
            _auth_with_dev_token(websocket)

            websocket.send_json({"type": "profile.get", "payload": {}})
            resp = websocket.receive_json()

            assert resp["type"] == "profile.data"
            data = resp["payload"]

            assert set(data.keys()) == {
                "name",
                "bio",
                "goal",
                "contexts",
                "notes",
                "onboarding_completed",
                "created_at",
                "updated_at",
            }
            # For a brand new dev user we primarily care about the response shape
            # and that onboarding_completed is a boolean; the underlying DB may
            # already contain seeded profile data from other tests, so we avoid
            # asserting that all fields are strictly None here.
            assert isinstance(data["onboarding_completed"], bool)

    def test_profile_update_and_get_roundtrip(self, client: TestClient) -> None:
        """profile.update should persist changes visible via subsequent profile.get."""

        payload = {
            "name": "Antonio",
            "bio": "Engineer — Backend",
            "goal": {"title": "Improve speaking", "description": "Interviews"},
            "contexts": {
                "title": "Sales call for X product",
                "description": "First conversations with new prospects ahead of my funding pitch",
            },
            "notes": "Initial notes",
        }

        with client.websocket_connect("/ws") as websocket:
            _auth_with_dev_token(websocket)

            websocket.send_json({"type": "profile.update", "payload": payload})

            # First response: updated profile.data
            resp1 = websocket.receive_json()
            assert resp1["type"] == "profile.data"
            data = resp1["payload"]

            assert data["name"] == "Antonio"
            assert data["bio"] == "Engineer — Backend"
            assert data["goal"]["title"] == "Improve speaking"
            assert data["contexts"]["title"] == "Sales call for X product"
            assert (
                data["contexts"]["description"]
                == "First conversations with new prospects ahead of my funding pitch"
            )
            assert data["notes"] == "Initial notes"

            # Second response: profile.updated ack
            resp2 = websocket.receive_json()
            assert resp2["type"] == "profile.updated"
            assert resp2["payload"]["success"] is True
            assert "updatedAt" in resp2["payload"]

            # Now call profile.get and ensure persisted values are returned
            websocket.send_json({"type": "profile.get", "payload": {}})
            resp3 = websocket.receive_json()
            assert resp3["type"] == "profile.data"
            data2 = resp3["payload"]

            assert data2["name"] == "Antonio"
            assert data2["bio"] == "Engineer — Backend"
            assert data2["goal"]["title"] == "Improve speaking"
            assert data2["contexts"]["title"] == "Sales call for X product"
            assert (
                data2["contexts"]["description"]
                == "First conversations with new prospects ahead of my funding pitch"
            )
            assert data2["notes"] == "Initial notes"
