"""Progress service for dashboards and history views."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Assessment, Session, SkillAssessment, SkillLevelHistory
from app.models.skill import Skill, UserSkill
from app.schemas.assessment import (
    AssessmentMetrics,
    AssessmentResponse,
    SkillAssessmentResponse,
    SkillFeedback,
)
from app.schemas.progress import (
    SessionHistoryItem,
    SkillLevelPoint,
    SkillProgressResponse,
)

logger = logging.getLogger("progress")


class ProgressService:
    """Aggregated progress data for dashboards and history views."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------------------
    # Skill progress
    # ---------------------------------------------------------------------

    async def get_skill_progress(self, user_id: UUID) -> list[SkillProgressResponse]:
        """Return per-skill level history for a user.

        Uses `user_skills` for current level and `skill_level_history` for
        historical level changes.
        """

        start = time.time()

        result = await self.db.execute(
            select(UserSkill, Skill)
            .join(Skill, UserSkill.skill_id == Skill.id)
            .where(UserSkill.user_id == user_id)
            .order_by(Skill.title)
        )
        rows: Iterable[tuple[UserSkill, Skill]] = result.all()

        # Preload all history rows and assessment counts for these skills
        skill_ids = [us.skill_id for us, _ in rows]
        history_by_skill: dict[UUID, list[SkillLevelHistory]] = {}
        assessment_counts: dict[UUID, int] = {}

        if skill_ids:
            hist_result = await self.db.execute(
                select(SkillLevelHistory)
                .where(
                    SkillLevelHistory.user_id == user_id,
                    SkillLevelHistory.skill_id.in_(skill_ids),
                )
                .order_by(SkillLevelHistory.created_at)
            )
            for row in hist_result.scalars().all():
                history_by_skill.setdefault(row.skill_id, []).append(row)

            # Count total (non-deleted) assessments per skill for this user
            sa_result = await self.db.execute(
                select(SkillAssessment.skill_id)
                .join(Assessment, SkillAssessment.assessment_id == Assessment.id)
                .where(
                    Assessment.user_id == user_id,
                    Assessment.deleted_at.is_(None),
                    SkillAssessment.skill_id.in_(skill_ids),
                )
            )
            for (skill_id,) in sa_result.all():
                assessment_counts[skill_id] = assessment_counts.get(skill_id, 0) + 1

        items: list[SkillProgressResponse] = []

        for user_skill, skill in rows:
            history_rows = history_by_skill.get(user_skill.skill_id, [])
            history = [
                SkillLevelPoint(
                    timestamp=h.created_at,
                    from_level=h.from_level,
                    to_level=h.to_level,
                    reason=h.reason,
                    source_assessment_id=h.source_assessment_id,
                )
                for h in history_rows
            ]

            items.append(
                SkillProgressResponse(
                    skill_id=skill.id,
                    slug=skill.slug,
                    title=skill.title,
                    current_level=user_skill.current_level,
                    is_tracked=user_skill.is_tracked,
                    history=history,
                    assessment_count=assessment_counts.get(user_skill.skill_id, 0),
                )
            )

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "Skill progress fetched",
            extra={
                "service": "progress",
                "user_id": str(user_id),
                "skill_count": len(items),
                "duration_ms": duration_ms,
            },
        )

        return items

    # ---------------------------------------------------------------------
    # Session history
    # ---------------------------------------------------------------------

    async def get_session_history(self, user_id: UUID, limit: int = 20) -> list[SessionHistoryItem]:
        """Return recent sessions with assessment counts for a user."""

        start = time.time()

        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .options(selectinload(Session.assessments))
            .order_by(Session.started_at.desc())
            .limit(limit)
        )

        sessions = list(result.scalars().all())

        items: list[SessionHistoryItem] = []
        for session in sessions:
            # Exclude soft-deleted assessments from history aggregates
            assessments = [
                a for a in (session.assessments or []) if getattr(a, "deleted_at", None) is None
            ]
            assessment_count = len(assessments)
            last_assessment_at = max(a.created_at for a in assessments) if assessments else None

            items.append(
                SessionHistoryItem(
                    id=session.id,
                    started_at=session.started_at,
                    ended_at=session.ended_at,
                    state=session.state,
                    interaction_count=session.interaction_count,
                    assessment_count=assessment_count,
                    last_assessment_at=last_assessment_at,
                )
            )

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "Session history fetched",
            extra={
                "service": "progress",
                "user_id": str(user_id),
                "session_count": len(items),
                "duration_ms": duration_ms,
            },
        )

        return items

    # ---------------------------------------------------------------------
    # Assessment details
    # ---------------------------------------------------------------------

    async def get_assessment_details(
        self,
        *,
        user_id: UUID,
        assessment_id: UUID,
    ) -> AssessmentResponse | None:
        """Return detailed assessment data for a single assessment.

        The response mirrors `AssessmentResponse` used by the assessment
        engine and WebSocket events so the mobile client can reuse mapping
        logic.
        """

        start = time.time()

        result = await self.db.execute(
            select(Assessment)
            .options(selectinload(Assessment.skill_assessments))
            .where(
                Assessment.id == assessment_id,
                Assessment.user_id == user_id,
                Assessment.deleted_at.is_(None),
            )
        )
        assessment = result.scalar_one_or_none()
        if not assessment:
            return None

        skill_items: list[SkillAssessmentResponse] = []
        total_cost_cents: int | None = 0
        max_latency_ms: int | None = None

        for sa in assessment.skill_assessments:
            call = sa.provider_call
            latency_ms: int | None = None
            tokens_used: int | None = None
            cost_cents: int | None = None
            provider: str | None = None
            model: str | None = None

            if call is not None:
                latency_ms = call.latency_ms
                if call.tokens_in is not None or call.tokens_out is not None:
                    tokens_used = (call.tokens_in or 0) + (call.tokens_out or 0)
                cost_cents = call.cost_cents
                provider = call.provider
                model = call.model_id

            fb_raw = sa.feedback or {}
            feedback = SkillFeedback(
                primary_takeaway=fb_raw.get("primary_takeaway")
                or fb_raw.get("primaryTakeaway")
                or "",
                strengths=fb_raw.get("strengths", []),
                improvements=fb_raw.get("improvements", []),
                example_quotes=fb_raw.get("example_quotes") or fb_raw.get("exampleQuotes") or [],
                next_level_criteria=fb_raw.get("next_level_criteria")
                or fb_raw.get("nextLevelCriteria"),
            )

            skill_items.append(
                SkillAssessmentResponse(
                    skill_id=sa.skill_id,
                    level=sa.level,
                    confidence=sa.confidence,
                    summary=sa.summary,
                    feedback=feedback,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                    cost_cents=cost_cents,
                    provider=provider,
                    model=model,
                )
            )

            if cost_cents is not None:
                total_cost_cents = (total_cost_cents or 0) + cost_cents
            if latency_ms is not None:
                max_latency_ms = max(max_latency_ms or 0, latency_ms)

        metrics = AssessmentMetrics(
            triage_latency_ms=None,
            assessment_latency_ms=max_latency_ms,
            total_cost_cents=total_cost_cents,
        )

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "Assessment details fetched",
            extra={
                "service": "progress",
                "user_id": str(user_id),
                "assessment_id": str(assessment_id),
                "skill_count": len(skill_items),
                "duration_ms": duration_ms,
            },
        )

        return AssessmentResponse(
            assessment_id=assessment.id,
            session_id=assessment.session_id,
            interaction_id=assessment.interaction_id,
            triage_decision=assessment.triage_decision,
            triage_override_label=getattr(assessment, "triage_override_label", None),
            user_response=None,
            skills=skill_items,
            metrics=metrics,
        )
