"""Integration tests for feedback HTTP endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer dev_token"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestFeedbackHTTP:
    def test_post_feedback_report_creates_event(self, client: TestClient) -> None:
        payload = {
            "category": "bug",
            "name": "Crash on open",
            "description": "App crashed on launch",
            "scope": "app",
            "time_bucket": "just_now",
            "session_id": None,
            "interaction_id": None,
        }

        resp = client.post("/api/v1/feedback/report", headers=AUTH_HEADERS, json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert set(data.keys()) == {
            "id",
            "user_id",
            "session_id",
            "interaction_id",
            "role",
            "category",
            "name",
            "short_reason",
            "time_bucket",
            "created_at",
        }
        assert data["category"] == "bug"
        assert data["name"] == "Crash on open"

    def test_get_feedback_returns_list_response(self, client: TestClient) -> None:
        resp = client.get("/api/v1/feedback", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()

        assert set(body.keys()) == {"items", "total"}
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)

    def test_get_feedback_respects_limit(self, client: TestClient) -> None:
        resp = client.get("/api/v1/feedback?limit=1", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        body = resp.json()

        assert isinstance(body["items"], list)
        assert body["total"] >= 0
        assert len(body["items"]) <= 1
