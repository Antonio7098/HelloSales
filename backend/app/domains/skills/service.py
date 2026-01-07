"""Skill service for managing skill catalog and user skill tracking."""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.assessment import Assessment, SkillAssessment
from app.models.skill import Skill, UserSkill
from app.schemas.skill import (
    SkillContextForLLM,
    SkillDetailResponse,
    SkillLevelCriteria,
    SkillResponse,
    TrackedSkillResponse,
    UserSkillProgress,
)

logger = logging.getLogger("skills")

# Maximum number of skills a user can track simultaneously
MAX_TRACKED_SKILLS = 2

# Minimum number of recent assessments required to compute recent_avg_score
MIN_ASSESSMENTS_FOR_AVERAGE = 3


class SkillServiceError(Exception):
    """Base exception for skill service errors."""

    pass


class MaxTrackedSkillsError(SkillServiceError):
    """Raised when user tries to track more than MAX_TRACKED_SKILLS."""

    pass


class SkillNotFoundError(SkillServiceError):
    """Raised when skill is not found."""

    pass


class UntrackingDisabledError(SkillServiceError):
    """Raised when untracking is disabled (e.g., beta mode)."""

    pass


class SkillService:
    """Service for skill catalog and user skill tracking operations."""

    def __init__(self, db: AsyncSession):
        """Initialize skill service.

        Args:
            db: Database session
        """
        self.db = db

    async def _get_recent_avg_scores(
        self,
        *,
        user_id: UUID,
        skill_ids: list[UUID],
        history_window: int = 5,
    ) -> dict[UUID, float]:
        """Compute recent average assessed level per skill for a user.

        Looks at the last ``history_window`` SkillAssessment rows per
        user+skill and returns their average level.
        """

        if not skill_ids:
            return {}

        result = await self.db.execute(
            select(SkillAssessment.skill_id, SkillAssessment.level)
            .join(Assessment, SkillAssessment.assessment_id == Assessment.id)
            .where(
                Assessment.user_id == user_id,
                Assessment.deleted_at.is_(None),
                SkillAssessment.skill_id.in_(skill_ids),
            )
            .order_by(SkillAssessment.created_at.desc())
        )

        rows = result.all()

        scores_by_skill: dict[UUID, list[int]] = {}
        for skill_id, level in rows:
            bucket = scores_by_skill.setdefault(skill_id, [])
            if len(bucket) >= history_window:
                continue
            bucket.append(level)

        avg_scores: dict[UUID, float] = {}
        for skill_id, scores in scores_by_skill.items():
            if len(scores) >= MIN_ASSESSMENTS_FOR_AVERAGE:
                avg_scores[skill_id] = sum(scores) / len(scores)

        return avg_scores

    async def list_skills(self, user_id: UUID) -> list[SkillResponse]:
        """Get all active skills with user's tracking status.

        Args:
            user_id: User ID

        Returns:
            List of skills with tracking status
        """
        # Get all active skills
        result = await self.db.execute(
            select(Skill).where(Skill.is_active).order_by(Skill.title)  # noqa: E712
        )
        skills = result.scalars().all()

        # Get user's skill progress
        user_skills_result = await self.db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id)
        )
        user_skills = {us.skill_id: us for us in user_skills_result.scalars().all()}

        avg_scores = await self._get_recent_avg_scores(
            user_id=user_id,
            skill_ids=list(user_skills.keys()),
        )

        # Build response
        response = []
        for skill in skills:
            user_skill = user_skills.get(skill.id)
            response.append(
                SkillResponse(
                    id=skill.id,
                    slug=skill.slug,
                    title=skill.title,
                    description=skill.description,
                    category=skill.category,
                    is_tracked=user_skill.is_tracked if user_skill else False,
                    current_level=user_skill.current_level if user_skill else None,
                    recent_avg_score=avg_scores.get(skill.id) if user_skill else None,
                )
            )

        logger.info(
            "Listed skills for user",
            extra={
                "service": "skills",
                "user_id": str(user_id),
                "skill_count": len(response),
            },
        )

        return response

    async def get_tracked_skills(self, user_id: UUID) -> list[TrackedSkillResponse]:
        """Get user's currently tracked skills.

        Args:
            user_id: User ID

        Returns:
            List of tracked skills with progress
        """
        result = await self.db.execute(
            select(UserSkill)
            .options(selectinload(UserSkill.skill))
            .where(UserSkill.user_id == user_id, UserSkill.is_tracked)
            .order_by(UserSkill.track_order)
        )
        user_skills = result.scalars().all()

        avg_scores = await self._get_recent_avg_scores(
            user_id=user_id,
            skill_ids=[us.skill_id for us in user_skills],
        )

        response = [
            TrackedSkillResponse(
                id=us.skill.id,
                slug=us.skill.slug,
                title=us.skill.title,
                current_level=us.current_level,
                track_order=us.track_order,
                started_at=us.started_at,
                last_tracked_at=us.last_tracked_at,
                recent_avg_score=avg_scores.get(us.skill_id),
            )
            for us in user_skills
        ]

        logger.debug(
            "Retrieved tracked skills",
            extra={
                "service": "skills",
                "user_id": str(user_id),
                "tracked_count": len(response),
            },
        )

        return response

    async def track_skill(self, user_id: UUID, skill_id: UUID) -> TrackedSkillResponse:
        """Track a skill for the user.

        Args:
            user_id: User ID
            skill_id: Skill ID to track

        Returns:
            The tracked skill response

        Raises:
            SkillNotFoundError: If skill doesn't exist
            MaxTrackedSkillsError: If user already has MAX_TRACKED_SKILLS tracked
        """
        # Verify skill exists
        skill = await self._get_skill(skill_id)
        if not skill:
            raise SkillNotFoundError(f"Skill {skill_id} not found")

        # Check current tracked count
        tracked = await self.get_tracked_skills(user_id)

        # Check if already tracked
        for ts in tracked:
            if ts.id == skill_id:
                logger.info(
                    "Skill already tracked",
                    extra={
                        "service": "skills",
                        "user_id": str(user_id),
                        "skill_id": str(skill_id),
                    },
                )
                return ts

        if len(tracked) >= MAX_TRACKED_SKILLS:
            raise MaxTrackedSkillsError(
                f"Cannot track more than {MAX_TRACKED_SKILLS} skills. Untrack one first."
            )

        # Determine next track_order
        used_orders = {ts.track_order for ts in tracked}
        next_order = 1 if 1 not in used_orders else 2

        # Get or create user_skill record
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill_id,
            )
        )
        user_skill = result.scalar_one_or_none()

        now = datetime.utcnow()

        if user_skill:
            # Re-tracking a previously tracked skill
            user_skill.is_tracked = True
            user_skill.track_order = next_order
            user_skill.last_tracked_at = now
            user_skill.untracked_at = None
        else:
            # First time tracking this skill
            user_skill = UserSkill(
                user_id=user_id,
                skill_id=skill_id,
                current_level=0,
                is_tracked=True,
                track_order=next_order,
                started_at=now,
                last_tracked_at=now,
            )
            self.db.add(user_skill)

        await self.db.commit()
        await self.db.refresh(user_skill)

        logger.info(
            "Skill tracked",
            extra={
                "service": "skills",
                "user_id": str(user_id),
                "skill_id": str(skill_id),
                "track_order": next_order,
                "current_level": user_skill.current_level,
            },
        )

        return TrackedSkillResponse(
            id=skill.id,
            slug=skill.slug,
            title=skill.title,
            current_level=user_skill.current_level,
            track_order=user_skill.track_order,
            started_at=user_skill.started_at,
            last_tracked_at=user_skill.last_tracked_at,
        )

    async def untrack_skill(self, user_id: UUID, skill_id: UUID) -> None:
        """Untrack a skill for the user. Progress is preserved.

        Args:
            user_id: User ID
            skill_id: Skill ID to untrack

        Raises:
            SkillNotFoundError: If skill or user_skill doesn't exist
            UntrackingDisabledError: If beta mode is enabled
        """
        settings = get_settings()
        if settings.beta_mode_enabled:
            raise UntrackingDisabledError("Untracking skills is disabled in beta mode.")

        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill_id,
            )
        )
        user_skill = result.scalar_one_or_none()

        if not user_skill:
            raise SkillNotFoundError(f"User skill {skill_id} not found")

        if not user_skill.is_tracked:
            logger.info(
                "Skill already untracked",
                extra={
                    "service": "skills",
                    "user_id": str(user_id),
                    "skill_id": str(skill_id),
                },
            )
            return

        user_skill.is_tracked = False
        user_skill.track_order = None
        user_skill.untracked_at = datetime.utcnow()

        await self.db.commit()

        logger.info(
            "Skill untracked",
            extra={
                "service": "skills",
                "user_id": str(user_id),
                "skill_id": str(skill_id),
                "preserved_level": user_skill.current_level,
            },
        )

    async def get_skill_detail(
        self, skill_id: UUID, user_id: UUID | None = None
    ) -> SkillDetailResponse:
        """Get full skill details including rubric.

        Args:
            skill_id: Skill ID
            user_id: Optional user ID to include progress

        Returns:
            Full skill detail with levels

        Raises:
            SkillNotFoundError: If skill doesn't exist
        """
        skill = await self._get_skill(skill_id)
        if not skill:
            raise SkillNotFoundError(f"Skill {skill_id} not found")

        # Parse levels from JSONB, normalizing any out-of-range level values
        raw_levels = skill.levels or []
        normalized_levels: list[SkillLevelCriteria] = []
        for level_data in raw_levels:
            level_value = level_data.get("level")
            if isinstance(level_value, int) and level_value < 1:
                # Normalize legacy/invalid levels (e.g., 0) up to 1 so schema validation passes
                logger.warning(
                    "Normalizing invalid skill level<1 in rubric",
                    extra={
                        "service": "skills",
                        "skill_id": str(skill_id),
                        "raw_level": level_value,
                    },
                )
                level_data = {**level_data, "level": 1}

            normalized_levels.append(SkillLevelCriteria(**level_data))

        levels = normalized_levels

        # Get user progress if user_id provided
        user_progress = None
        if user_id:
            result = await self.db.execute(
                select(UserSkill).where(
                    UserSkill.user_id == user_id,
                    UserSkill.skill_id == skill_id,
                )
            )
            user_skill = result.scalar_one_or_none()
            if user_skill:
                avg_scores = await self._get_recent_avg_scores(
                    user_id=user_id,
                    skill_ids=[skill_id],
                )
                user_progress = UserSkillProgress(
                    current_level=user_skill.current_level,
                    is_tracked=user_skill.is_tracked,
                    track_order=user_skill.track_order,
                    recent_avg_score=avg_scores.get(skill_id),
                )

        logger.debug(
            "Retrieved skill detail",
            extra={
                "service": "skills",
                "skill_id": str(skill_id),
                "user_id": str(user_id) if user_id else None,
            },
        )

        return SkillDetailResponse(
            id=skill.id,
            slug=skill.slug,
            title=skill.title,
            description=skill.description,
            category=skill.category,
            levels=levels,
            user_progress=user_progress,
        )

    async def validate_skill_ids(self, user_id: UUID, skill_ids: list[UUID]) -> list[UUID]:
        """Validate that skill IDs belong to user's tracked skills.

        Args:
            user_id: User ID
            skill_ids: List of skill IDs to validate

        Returns:
            List of valid skill IDs (subset of input that user actually tracks)
        """
        if not skill_ids:
            return []

        result = await self.db.execute(
            select(UserSkill.skill_id).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id.in_(skill_ids),
                UserSkill.is_tracked,
            )
        )
        valid_ids = [row[0] for row in result.all()]

        logger.debug(
            "Validated skill IDs",
            extra={
                "service": "skills",
                "user_id": str(user_id),
                "requested": len(skill_ids),
                "valid": len(valid_ids),
            },
        )

        return valid_ids

    async def get_skill_context_for_llm(
        self, user_id: UUID, skill_ids: list[UUID] | None = None
    ) -> list[SkillContextForLLM]:
        """Get skill context for LLM prompts.

        In beta mode: returns all active skills regardless of tracking status.
        Otherwise: validates provided skill_ids or falls back to tracked skills.

        Args:
            user_id: User ID
            skill_ids: Optional list of skill IDs (from frontend)

        Returns:
            List of skill contexts for LLM prompt injection
        """
        settings = get_settings()
        get_settings.cache_clear()
        settings = get_settings()
        print(f"DEBUG SkillService: beta_mode_enabled={settings.beta_mode_enabled}")

        # In beta mode, use all active skills
        if settings.beta_mode_enabled:
            print("DEBUG: Beta mode enabled, calling _get_all_skills_context_for_llm")
            return await self._get_all_skills_context_for_llm(user_id)

        print("DEBUG: Beta mode NOT enabled, continuing with normal flow")

        # If skill_ids provided, validate them
        if skill_ids:
            valid_ids = await self.validate_skill_ids(user_id, skill_ids)
            if not valid_ids:
                # Fallback to fetching tracked skills
                skill_ids = None

        # Fetch tracked skills if no valid skill_ids
        if not skill_ids:
            tracked = await self.get_tracked_skills(user_id)
            if not tracked:
                return []
            skill_ids = [ts.id for ts in tracked]

        # Get full skill data with user progress
        contexts = []
        for skill_id in skill_ids:
            result = await self.db.execute(
                select(UserSkill)
                .options(selectinload(UserSkill.skill))
                .where(
                    UserSkill.user_id == user_id,
                    UserSkill.skill_id == skill_id,
                    UserSkill.is_tracked,
                )
            )
            user_skill = result.scalar_one_or_none()
            if not user_skill:
                continue

            skill = user_skill.skill
            current_level = user_skill.current_level

            # Get next level criteria
            next_level = current_level + 1 if current_level < 10 else None
            next_level_criteria = None
            next_level_examples = []
            current_level_examples = []

            # Extract rubric data for current and next levels
            if skill.levels:
                for level_data in skill.levels:
                    level_number = level_data.get("level")
                    if level_number == current_level:
                        current_level_examples = level_data.get("examples", [])
                    if level_number == next_level:
                        next_level_criteria = level_data.get("criteria")
                        next_level_examples = level_data.get("examples", [])
                    if current_level_examples and next_level_examples:
                        break

            if next_level and skill.levels:
                for level_data in skill.levels:
                    if level_data.get("level") == next_level:
                        next_level_criteria = level_data.get("criteria")
                        next_level_examples = level_data.get("examples", [])
                        break

            contexts.append(
                SkillContextForLLM(
                    skill_id=skill.id,
                    slug=skill.slug,
                    title=skill.title,
                    current_level=current_level,
                    current_level_examples=current_level_examples,
                    next_level=next_level,
                    next_level_criteria=next_level_criteria,
                    next_level_examples=next_level_examples,
                )
            )

        logger.info(
            "Built skill context for LLM",
            extra={
                "service": "skills",
                "user_id": str(user_id),
                "skill_count": len(contexts),
                "skills": [c.slug for c in contexts],
            },
        )

        return contexts

    async def _get_all_skills_context_for_llm(self, user_id: UUID) -> list[SkillContextForLLM]:
        """Get context for ALL active skills (beta mode).

        Returns skill context for all active skills, using user's progress
        if available, or default level 0 otherwise.
        """
        print(f"DEBUG: _get_all_skills_context_for_llm called for user_id={user_id}")

        # Get all active skills
        result = await self.db.execute(
            select(Skill).where(Skill.is_active).order_by(Skill.title)  # noqa: E712
        )
        skills = result.scalars().all()
        print(f"DEBUG: Found {len(skills)} active skills")

        if not skills:
            print("DEBUG: No active skills found")
            return []

        # Get user's skill progress for all skills
        user_skills_result = await self.db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id)
        )
        user_skills_by_id = {us.skill_id: us for us in user_skills_result.scalars().all()}

        contexts = []
        for skill in skills:
            user_skill = user_skills_by_id.get(skill.id)
            current_level = user_skill.current_level if user_skill else 0

            # Get next level criteria
            next_level = current_level + 1 if current_level < 10 else None
            next_level_criteria = None
            next_level_examples = []
            current_level_examples = []

            # Extract rubric data for current and next levels
            if skill.levels:
                for level_data in skill.levels:
                    level_number = level_data.get("level")
                    if level_number == current_level:
                        current_level_examples = level_data.get("examples", [])
                    if level_number == next_level:
                        next_level_criteria = level_data.get("criteria")
                        next_level_examples = level_data.get("examples", [])
                    if current_level_examples and next_level_examples:
                        break

            contexts.append(
                SkillContextForLLM(
                    skill_id=skill.id,
                    slug=skill.slug,
                    title=skill.title,
                    current_level=current_level,
                    current_level_examples=current_level_examples,
                    next_level=next_level,
                    next_level_criteria=next_level_criteria,
                    next_level_examples=next_level_examples,
                )
            )

        logger.info(
            "Built skill context for LLM (beta mode - all skills)",
            extra={
                "service": "skills",
                "user_id": str(user_id),
                "skill_count": len(contexts),
                "skills": [c.slug for c in contexts],
                "beta_mode": True,
            },
        )

        return contexts

    async def _get_skill(self, skill_id: UUID) -> Skill | None:
        """Get a skill by ID."""
        result = await self.db.execute(select(Skill).where(Skill.id == skill_id))
        return result.scalar_one_or_none()
