"""Unit tests for ProfileService."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.profile.service import ProfileService
from app.models.profile import UserProfile
from app.schemas.profile import UserProfileUpdate


@pytest.fixture
def mock_db() -> AsyncSession:
    """Create a mocked AsyncSession so tests do not touch a real database."""

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_get_profile_response_returns_empty_when_missing(mock_db: AsyncSession):
    """get_profile_response should return an empty, serialisable profile when none exists."""

    service = ProfileService(mock_db)
    user_id = uuid.uuid4()

    # Simulate no stored profile
    service.get_profile = AsyncMock(return_value=None)

    # Simulate no associated user record for onboarding status lookup
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = user_result

    response = await service.get_profile_response(user_id)

    assert response.name is None
    assert response.bio is None
    assert response.goal is None
    assert response.contexts is None
    assert response.notes is None
    # Timestamps should be set and be valid datetimes
    assert isinstance(response.created_at, datetime)
    assert isinstance(response.updated_at, datetime)

    # No DB writes should occur in this path
    mock_db.commit.assert_not_awaited()
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_profile_creates_and_updates_profile(mock_db: AsyncSession):
    """upsert_profile should create a profile and then update its fields on subsequent calls."""

    service = ProfileService(mock_db)
    user_id = uuid.uuid4()

    # First call: behave as if no profile exists yet
    service.get_profile = AsyncMock(return_value=None)

    # Simulate no associated user record for onboarding status lookup
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = user_result

    create_update = UserProfileUpdate(
        name="Antonio",
        bio="Engineer — Backend",
        goal={"title": "Improve speaking", "description": "Interviews"},
        contexts={
            "title": "Sales call for X product",
            "description": "First conversations with new prospects ahead of my funding pitch",
        },
        notes="Initial notes",
    )

    profile = await service.upsert_profile(user_id, create_update)

    assert isinstance(profile, UserProfile)
    assert profile.user_id == user_id
    assert profile.name == "Antonio"
    assert profile.bio == "Engineer — Backend"
    assert profile.goal is not None and profile.goal.get("title") == "Improve speaking"
    assert profile.contexts == {
        "title": "Sales call for X product",
        "description": "First conversations with new prospects ahead of my funding pitch",
    }
    assert profile.notes == "Initial notes"

    # Second call: now get_profile should return the existing profile instance
    service.get_profile = AsyncMock(return_value=profile)

    second_update = UserProfileUpdate(
        name="Antonio Updated",
        contexts={
            "title": "Sales calls for Y product",
            "description": "Follow-up calls with existing customers to upsell",
        },
    )

    updated = await service.upsert_profile(user_id, second_update)

    # Same row updated in-place
    assert updated is profile
    assert updated.name == "Antonio Updated"
    # Bio and goal should be preserved
    assert updated.bio == profile.bio
    assert updated.goal == profile.goal
    # Contexts should reflect the new structured context
    assert updated.contexts == {
        "title": "Sales calls for Y product",
        "description": "Follow-up calls with existing customers to upsell",
    }
    # Notes unchanged
    assert updated.notes == "Initial notes"

    # And get_profile_response should now reflect stored values
    service.get_profile = AsyncMock(return_value=updated)
    response = await service.get_profile_response(user_id)
    assert response.name == "Antonio Updated"
    assert response.bio == "Engineer — Backend"
    assert response.goal is not None and response.goal.title == "Improve speaking"
    assert response.contexts is not None
    assert response.contexts.title == "Sales calls for Y product"
    assert response.contexts.description == "Follow-up calls with existing customers to upsell"
    assert response.notes == "Initial notes"

    # Commits should have been attempted
    assert mock_db.commit.await_count >= 2
