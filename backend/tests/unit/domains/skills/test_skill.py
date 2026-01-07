import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.skills.service import MaxTrackedSkillsError, SkillService, SkillServiceError
from app.models.skill import Skill, UserSkill
from app.schemas.skill import SkillContextForLLM, TrackedSkillResponse


@pytest.fixture(autouse=True)
def mock_beta_mode_disabled():
    """Disable beta mode for all skill tests to test standard behavior."""
    with patch("app.domains.skills.service.get_settings") as mock_settings:
        mock_settings.return_value.beta_mode_enabled = False
        yield mock_settings


class AsyncIterator:
    """Helper to turn a list into an async iterator for mocking streams."""

    def __init__(self, iterable):
        self._iter = iter(iterable)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:  # pragma: no cover - helper
            raise StopAsyncIteration from exc


@pytest.fixture
def mock_db():
    """Fixture to create a mock AsyncSession."""
    from unittest.mock import AsyncMock, MagicMock

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def skill_service(mock_db):
    return SkillService(db=mock_db)


def make_skill(slug: str = "clarity", levels: list | None = None) -> Skill:
    return Skill(
        id=uuid.uuid4(),
        slug=slug,
        title=slug.title(),
        description="Test skill",
        category="test",
        levels=levels or [{"level": 1, "criteria": "test", "examples": []}],
        is_active=True,
        created_at=datetime.utcnow(),
    )


def make_user_skill(
    skill: Skill, level: int = 3, tracked: bool = True, order: int | None = 1
) -> UserSkill:
    return UserSkill(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        skill_id=skill.id,
        current_level=level,
        is_tracked=tracked,
        track_order=order,
        started_at=datetime.utcnow(),
        last_tracked_at=datetime.utcnow(),
    )


class TestSkillService:
    async def test_list_skills(self, mock_db, skill_service):
        """list_skills returns catalog with correct tracking info."""

        skills = [make_skill("clarity"), make_skill("persuasion")]
        user_skill = make_user_skill(skills[0], level=5)

        async def execute_side_effect(query):
            from unittest.mock import MagicMock

            result = MagicMock()
            text = str(query)
            if "FROM skills" in text and "user_skills" not in text:
                result.scalars.return_value.all.return_value = skills
            elif "FROM user_skills" in text:
                result.scalars.return_value.all.return_value = [user_skill]
            else:  # pragma: no cover - should not happen
                result.scalars.return_value.all.return_value = []
            return result

        mock_db.execute.side_effect = execute_side_effect

        response = await skill_service.list_skills(uuid.uuid4())

        assert len(response) == 2
        tracked = next(r for r in response if r.slug == "clarity")
        assert tracked.is_tracked is True
        assert tracked.current_level == 5
        untracked = next(r for r in response if r.slug == "persuasion")
        assert untracked.is_tracked is False
        assert untracked.current_level is None

    async def test_track_skill_enforces_max(self, mock_db, skill_service):
        """track_skill raises when user already has max tracked skills."""

        skill = make_skill()
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [skill]
        tracked = [
            TrackedSkillResponse(
                id=uuid.uuid4(), slug="a", title="A", current_level=1, track_order=1
            ),
            TrackedSkillResponse(
                id=uuid.uuid4(), slug="b", title="B", current_level=2, track_order=2
            ),
        ]

        async def mock_get_tracked(_user_id):
            return tracked

        skill_service.get_tracked_skills = mock_get_tracked

        with pytest.raises(MaxTrackedSkillsError):
            await skill_service.track_skill(uuid.uuid4(), skill.id)

    async def test_track_skill_existing(self, mock_db, skill_service):
        """track_skill resumes tracking existing user_skill."""

        skill = make_skill()
        user_skill = make_user_skill(skill, tracked=False, order=None)
        from unittest.mock import MagicMock

        result_skill = MagicMock()
        result_skill.scalar_one_or_none.return_value = skill

        result_user_skill = MagicMock()
        result_user_skill.scalar_one_or_none.return_value = user_skill

        mock_db.execute.side_effect = [result_skill, result_user_skill]

        async def mock_get_tracked(_user_id):
            return [
                TrackedSkillResponse(
                    id=uuid.uuid4(), slug="a", title="A", current_level=1, track_order=1
                )
            ]

        skill_service.get_tracked_skills = mock_get_tracked

        response = await skill_service.track_skill(uuid.uuid4(), skill.id)

        assert response.id == skill.id
        assert user_skill.is_tracked is True
        assert user_skill.track_order == 2
        mock_db.commit.assert_awaited()

    async def test_untrack_skill(self, mock_db, skill_service):
        """untrack_skill marks skill as untracked but preserves level."""

        skill = make_skill()
        user_skill = make_user_skill(skill)

        from unittest.mock import MagicMock

        result = MagicMock()
        result.scalar_one_or_none.return_value = user_skill
        mock_db.execute.return_value = result

        await skill_service.untrack_skill(user_skill.user_id, skill.id)

        assert user_skill.is_tracked is False
        assert user_skill.track_order is None
        mock_db.commit.assert_awaited()

    async def test_get_skill_context_for_llm_from_ids(self, mock_db, skill_service):
        """get_skill_context_for_llm validates IDs and returns contexts."""

        skill = make_skill(
            levels=[
                {"level": 1, "criteria": "basic", "examples": ["do"], "hints": []},
                {"level": 2, "criteria": "next", "examples": ["more"], "hints": []},
            ]
        )
        user_skill = make_user_skill(skill, level=1)

        from unittest.mock import MagicMock

        result_validate = MagicMock()
        result_validate.all.return_value = [(skill.id,)]

        # Attach skill relationship for selectinload
        user_skill.skill = skill

        result_context = MagicMock()
        result_context.scalar_one_or_none.return_value = user_skill

        mock_db.execute.side_effect = [result_validate, result_context]

        contexts = await skill_service.get_skill_context_for_llm(user_skill.user_id, [skill.id])

        assert len(contexts) == 1
        ctx = contexts[0]
        assert isinstance(ctx, SkillContextForLLM)
        assert ctx.next_level == 2
        assert ctx.next_level_criteria == "next"

    async def test_validate_skill_ids_empty(self, skill_service):
        assert await skill_service.validate_skill_ids(uuid.uuid4(), []) == []

    async def test_untrack_skill_missing_raises(self, mock_db, skill_service):
        from unittest.mock import MagicMock

        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with pytest.raises(SkillServiceError):
            await skill_service.untrack_skill(uuid.uuid4(), uuid.uuid4())

    async def test_get_skill_context_for_llm_invalid_ids_fallbacks_to_tracked(
        self, mock_db, skill_service
    ):
        """If provided skill IDs are invalid, fall back to tracked skills."""

        user_id = uuid.uuid4()
        skill = make_skill(
            levels=[
                {"level": 1, "criteria": "basic", "examples": ["ex1"], "hints": []},
                {"level": 2, "criteria": "next", "examples": ["ex2"], "hints": []},
            ]
        )
        user_skill = make_user_skill(skill, level=1)
        user_skill.user_id = user_id
        user_skill.skill = skill

        tracked = TrackedSkillResponse(
            id=skill.id,
            slug=skill.slug,
            title=skill.title,
            current_level=user_skill.current_level,
            track_order=1,
            started_at=user_skill.started_at,
            last_tracked_at=user_skill.last_tracked_at,
        )

        from unittest.mock import AsyncMock

        skill_service.validate_skill_ids = AsyncMock(return_value=[])
        skill_service.get_tracked_skills = AsyncMock(return_value=[tracked])

        from unittest.mock import MagicMock

        result_context = MagicMock()
        result_context.scalar_one_or_none.return_value = user_skill
        mock_db.execute.side_effect = [result_context]

        contexts = await skill_service.get_skill_context_for_llm(user_id, [uuid.uuid4()])

        assert len(contexts) == 1
        assert contexts[0].slug == skill.slug

    async def test_get_skill_context_for_llm_no_tracked_skills_returns_empty(self, skill_service):
        """If user has no tracked skills and none requested, return empty list."""

        user_id = uuid.uuid4()
        from unittest.mock import AsyncMock

        skill_service.get_tracked_skills = AsyncMock(return_value=[])

        contexts = await skill_service.get_skill_context_for_llm(user_id)

        assert contexts == []
