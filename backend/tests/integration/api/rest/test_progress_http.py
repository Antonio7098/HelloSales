"""Integration tests for progress HTTP endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer dev_token"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestProgressHTTP:
    def test_get_skill_progress_returns_list(self, client: TestClient) -> None:
        response = client.get("/api/v1/progress/skills", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_session_history_respects_limit(self, client: TestClient) -> None:
        response = client.get("/api/v1/progress/sessions?limit=5", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_get_assessment_details_not_found_for_unknown_id(self, client: TestClient) -> None:
        unknown_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/progress/assessments/{unknown_id}", headers=AUTH_HEADERS)
        assert response.status_code == 404
        body = response.json()
        assert body["detail"] == "Assessment not found"
