"""Integration tests for health endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "eloquence-backend"

    def test_root_endpoint_in_dev(self, client):
        """Test root endpoint returns API info in dev mode."""
        response = client.get("/")
        # Should work in development mode
        if response.status_code == 200:
            data = response.json()
            assert "service" in data
            assert "version" in data
