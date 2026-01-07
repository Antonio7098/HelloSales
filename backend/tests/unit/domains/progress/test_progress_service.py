"""Unit tests for ProgressService."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.assessment.progress import ProgressService
from app.models.assessment import Assessment
from app.models.session import Session
from app.models.skill import Skill, UserSkill
from app.schemas.progress import SessionHistoryItem, SkillProgressResponse


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
async def test_get_skill_progress_returns_history_for_tracked_skills(mock_db: AsyncSession):
    """get_skill_progress should return per-skill current level and history using mocked rows."""

    service = ProgressService(mock_db)
    user_id = uuid.uuid4()

    # Create in-memory Skill and UserSkill objects
    skill = Skill(
        slug="discourse_coherence",
        title="Discourse Coherence",
        description="Test skill",
        levels=[{"level": 0, "criteria": "", "examples": []}],
        category="test",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    user_skill = UserSkill(
        user_id=user_id,
        skill_id=skill.id,
        current_level=3,
        is_tracked=True,
        track_order=1,
        started_at=datetime.utcnow(),
        last_tracked_at=datetime.utcnow(),
    )

    # First query: select(UserSkill, Skill)...
    result_user_skills = MagicMock()
    result_user_skills.all.return_value = [(user_skill, skill)]

    # Second query: select(SkillLevelHistory)... (no history rows)
    result_history = MagicMock()
    result_history.scalars.return_value.all.return_value = []

    async def execute_side_effect(query):
        text = str(query)
        if "FROM user_skills" in text and "JOIN skills" in text:
            return result_user_skills
        if "FROM skill_level_history" in text:
            return result_history
        return MagicMock()

    mock_db.execute.side_effect = execute_side_effect

    items = await service.get_skill_progress(user_id)

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, SkillProgressResponse)
    assert item.skill_id == skill.id
    assert item.slug == skill.slug
    assert item.title == skill.title
    assert item.current_level == 3
    assert item.is_tracked is True
    assert item.history == []


@pytest.mark.asyncio
async def test_get_session_history_returns_sessions_with_assessment_counts(mock_db: AsyncSession):
    """get_session_history should return recent sessions with assessment counts and last_assessment_at."""

    service = ProgressService(mock_db)
    user_id = uuid.uuid4()

    base_time = datetime.utcnow()

    # In-memory sessions
    s1 = Session(user_id=user_id, started_at=base_time - timedelta(minutes=10), state="ended")
    s2 = Session(user_id=user_id, started_at=base_time - timedelta(minutes=5), state="active")

    # Attach in-memory assessments
    a1 = Assessment(
        user_id=user_id,
        session_id=s1.id,
        interaction_id=None,
        group_id=uuid.uuid4(),
        triage_decision="assess",
        created_at=base_time - timedelta(minutes=9),
    )
    a2 = Assessment(
        user_id=user_id,
        session_id=s2.id,
        interaction_id=None,
        group_id=uuid.uuid4(),
        triage_decision="assess",
        created_at=base_time - timedelta(minutes=4),
    )

    s1.assessments = [a1]
    s2.assessments = [a2]

    # Query result for sessions ordered by started_at desc
    result_sessions = MagicMock()
    result_sessions.scalars.return_value.all.return_value = [s2, s1]

    async def execute_side_effect(query):
        text = str(query)
        if "FROM sessions" in text:
            return result_sessions
        return MagicMock()

    mock_db.execute.side_effect = execute_side_effect

    items = await service.get_session_history(user_id, limit=10)

    assert len(items) == 2
    assert all(isinstance(i, SessionHistoryItem) for i in items)

    # Sessions are ordered by started_at desc, so s2 should come first
    first, second = items
    assert first.id == s2.id
    assert first.assessment_count == 1
    assert first.last_assessment_at == a2.created_at

    assert second.id == s1.id
    assert second.assessment_count == 1
    assert second.last_assessment_at == a1.created_at
