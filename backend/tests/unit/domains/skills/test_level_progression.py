"""Unit tests for level progression logic in AssessmentService.check_level_progression."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.assessment.service import AssessmentService
from app.models.assessment import SkillAssessment, SkillLevelHistory
from app.models.skill import UserSkill


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession-like object."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    async def refresh_side_effect(obj):
        # Simulate DB assigning created_at on insert so LevelChangeEvent can
        # safely read history.created_at, matching real behavior.
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.utcnow()

    db.refresh = AsyncMock(side_effect=refresh_side_effect)
    db.add = MagicMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create an AssessmentService with mocked DB (no real LLM needed)."""
    from app.ai.providers.base import LLMProvider
    # Create a mock LLM provider that satisfies the requirement
    mock_llm = MagicMock(spec=LLMProvider)
    return AssessmentService(db=mock_db, llm_provider=mock_llm)


@pytest.mark.asyncio
async def test_check_level_progression_no_user_skill_returns_none(service, mock_db):
    """If there is no UserSkill row, progression should return None and not write history."""

    user_id = uuid.uuid4()
    skill_id = uuid.uuid4()

    # First execute() call: select(UserSkill) → no row
    result_user_skill = MagicMock()
    result_user_skill.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result_user_skill

    event = await service.check_level_progression(user_id=user_id, skill_id=skill_id)

    assert event is None
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_level_progression_no_recent_assessments_returns_none(service, mock_db):
    """If there are no recent SkillAssessment rows, progression should return None."""

    user_id = uuid.uuid4()
    skill_id = uuid.uuid4()

    # UserSkill exists at level 0
    user_skill = UserSkill(
        id=uuid.uuid4(),
        user_id=user_id,
        skill_id=skill_id,
        current_level=0,
        is_tracked=True,
        track_order=1,
        started_at=datetime.utcnow(),
        last_tracked_at=datetime.utcnow(),
    )

    result_user_skill = MagicMock()
    result_user_skill.scalar_one_or_none.return_value = user_skill

    # No recent assessments
    result_sa = MagicMock()
    result_sa.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [result_user_skill, result_sa]

    event = await service.check_level_progression(user_id=user_id, skill_id=skill_id)

    assert event is None
    # No history written
    mock_db.add.assert_not_called()
    # We may have one commit from previous operations, but no extra due to progression


@pytest.mark.asyncio
async def test_check_level_progression_levels_up_from_0_to_3(service, mock_db):
    """Average >= 3 when current level <=2 should level user up to 3 and record history."""

    user_id = uuid.uuid4()
    skill_id = uuid.uuid4()

    # UserSkill at level 0
    user_skill = UserSkill(
        id=uuid.uuid4(),
        user_id=user_id,
        skill_id=skill_id,
        current_level=0,
        is_tracked=True,
        track_order=1,
        started_at=datetime.utcnow(),
        last_tracked_at=datetime.utcnow(),
    )

    # Recent assessments with average >= 3
    scores = [3, 4, 3, 2, 3]  # avg = 3.0
    recent_assessments = [
        SkillAssessment(
            id=uuid.uuid4(),
            assessment_id=uuid.uuid4(),
            skill_id=skill_id,
            level=score,
            confidence=None,
            summary=None,
            feedback={},
            provider="test",
            model_id="test",
            tokens_used=None,
            cost_cents=None,
            latency_ms=None,
            created_at=datetime.utcnow(),
        )
        for score in scores
    ]

    result_user_skill = MagicMock()
    result_user_skill.scalar_one_or_none.return_value = user_skill

    result_sa = MagicMock()
    result_sa.scalars.return_value.all.return_value = recent_assessments

    mock_db.execute.side_effect = [result_user_skill, result_sa]

    event = await service.check_level_progression(user_id=user_id, skill_id=skill_id)

    # LevelChangeEvent returned with correct levels
    assert event is not None
    assert event.from_level == 0
    assert event.to_level == 3
    assert event.user_id == user_id
    assert event.skill_id == skill_id

    # UserSkill updated in-memory
    assert user_skill.current_level == 3

    # SkillLevelHistory written
    mock_db.add.assert_called_once()
    history_obj = mock_db.add.call_args.args[0]
    assert isinstance(history_obj, SkillLevelHistory)
    assert history_obj.from_level == 0
    assert history_obj.to_level == 3

    # Commits and refresh called
    assert mock_db.commit.await_count >= 2
    mock_db.refresh.assert_awaited_with(history_obj)
