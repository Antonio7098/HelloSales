"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Test settings with defaults."""
    return Settings(
        environment="development",
        database_url="postgresql+asyncpg://test:test@localhost:5432/hellosales_test",
        workos_client_id="test_client_id",
        workos_api_key="test_api_key",
        groq_api_key="test_groq_key",
        log_level="DEBUG",
        log_format="text",
    )


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session
