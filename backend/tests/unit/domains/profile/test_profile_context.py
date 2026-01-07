"""Unit tests for profile context builder in ChatService."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat.service import ChatService
from app.models.profile import UserProfile


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
async def test_build_profile_context_returns_none_when_no_user(mock_db: AsyncSession) -> None:
    """If the session has no associated user, _build_profile_context should return None."""
    from app.ai.providers.base import LLMProvider
    mock_llm = MagicMock(spec=LLMProvider)
    service = ChatService(db=mock_db, llm_provider=mock_llm)
    session_id = uuid.uuid4()

    # First query: select(Session.user_id)... returns no row
    result_no_user = MagicMock()
    result_no_user.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result_no_user

    context = await service._build_profile_context(session_id)

    assert context is None


@pytest.mark.asyncio
async def test_build_profile_context_formats_profile_fields(mock_db: AsyncSession) -> None:
    """_build_profile_context should mirror the expected backend format for a populated profile."""
    from app.ai.providers.base import LLMProvider
    mock_llm = MagicMock(spec=LLMProvider)
    service = ChatService(db=mock_db, llm_provider=mock_llm)
    session_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Prepare in-memory UserProfile
    profile = UserProfile(
        user_id=user_id,
        name="Antonio",
        bio="Sales Manager — B2B SaaS",
        goal={"title": "Ace investor pitch", "description": "Series A"},
        contexts=["sales_calls", "presentations"],
        notes="Should not appear in context string",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # First execute: resolve user_id from Session
    result_user = MagicMock()
    result_user.scalar_one_or_none.return_value = user_id

    # Second execute: load UserProfile
    result_profile = MagicMock()
    result_profile.scalar_one_or_none.return_value = profile

    async def execute_side_effect(query):
        text = str(query)
        if "FROM sessions" in text:
            return result_user
        if "FROM user_profiles" in text:
            return result_profile
        return MagicMock()

    mock_db.execute.side_effect = execute_side_effect

    context = await service._build_profile_context(session_id)

    assert context is not None
    lines = context.split("\n")

    # Header
    assert lines[0] == "User Profile:"
    # Name line
    assert "- Name: Antonio" in lines[1]
    # Bio and goal lines
    assert any("Bio:" in line and "Sales Manager" in line for line in lines)
    assert any("Goal:" in line and "Ace investor pitch" in line for line in lines)
    # Focus areas
    assert any("Focus areas:" in line and "sales_calls" in line for line in lines)
    # Tailoring instruction
    assert "Tailor your coaching to this context" in context
