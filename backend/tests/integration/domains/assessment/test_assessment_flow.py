"""Integration tests for full assessment flow.

These tests exercise the real database schema, AssessmentService, and
level progression logic, using the stub LLM provider to avoid external
LLM calls.
"""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.ai.providers.llm.stub import StubLLMProvider
from app.database import get_session_context
from app.domains.assessment.service import AssessmentService
from app.models.assessment import SkillAssessment, SkillLevelHistory
from app.models.session import Session
from app.models.skill import Skill, UserSkill
from app.models.user import User


@pytest.mark.asyncio
async def test_full_assessment_flow_levels_up():
    """Running assessments with stub LLM should eventually level up the user.

    Flow:
    - Create user, session, skill, user_skill at level 0
    - Run AssessmentService.assess_response several times with stub LLM
    - check_level_progression (invoked internally) should promote the user
      from level 0 → 3 and write SkillLevelHistory rows.
    """

    async with get_session_context() as db_session:
        # 1) Seed user + session + skill + user_skill in the test DB (idempotent)
        result_user = await db_session.execute(
            select(User).where(
                User.auth_provider == "clerk",
                User.auth_subject == "integration_user_assessment",
            )
        )
        user = result_user.scalar_one_or_none()
        if not user:
            user = User(
                auth_provider="clerk",
                auth_subject="integration_user_assessment",
                clerk_id="integration_user_assessment",
                email="integration@example.com",
                display_name="Integration User",
            )
            db_session.add(user)
            await db_session.flush()

        session = Session(user_id=user.id)
        db_session.add(session)

        # Simple skill with basic levels JSON (get-or-create by slug)
        levels = [
            {"level": i, "criteria": f"Level {i} criteria", "examples": []} for i in range(11)
        ]
        result_skill = await db_session.execute(
            select(Skill).where(Skill.slug == "integration_clarity")
        )
        skill = result_skill.scalar_one_or_none()
        if not skill:
            skill = Skill(
                slug="integration_clarity",
                title="Integration Clarity",
                description="Integration test skill",
                levels=levels,
                category="test",
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db_session.add(skill)
            await db_session.flush()

        # Get-or-create UserSkill for this user+skill, resetting level to 0
        result_us = await db_session.execute(
            select(UserSkill).where(
                UserSkill.user_id == user.id,
                UserSkill.skill_id == skill.id,
            )
        )
        user_skill = result_us.scalar_one_or_none()
        if not user_skill:
            user_skill = UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                current_level=0,
                is_tracked=True,
                track_order=1,
                started_at=datetime.utcnow(),
                last_tracked_at=datetime.utcnow(),
            )
            db_session.add(user_skill)
        else:
            user_skill.current_level = 0
            user_skill.is_tracked = True
            user_skill.track_order = user_skill.track_order or 1
            user_skill.last_tracked_at = datetime.utcnow()

        await db_session.commit()

        # 2) Create AssessmentService with stub LLM provider
        service = AssessmentService(db=db_session, llm_provider=StubLLMProvider())

        # 3) Run several assessments for this user/skill
        for _ in range(5):
            await service.assess_response(
                user_id=user.id,
                session_id=session.id,
                interaction_id=None,
                user_response="The solution is straightforward. We implement phase one next week...",
                skill_ids=[skill.id],
                send_status=None,
                triage_decision="assess",
            )

        # 4) Verify that level progression has occurred
        result_us = await db_session.execute(
            select(UserSkill).where(
                UserSkill.user_id == user.id,
                UserSkill.skill_id == skill.id,
            )
        )
        updated_user_skill = result_us.scalar_one()

        assert updated_user_skill.current_level >= 3

        # 5) Verify SkillAssessment rows exist for this user/skill
        result_sa = await db_session.execute(
            select(SkillAssessment).where(SkillAssessment.skill_id == skill.id)
        )
        assessments = list(result_sa.scalars().all())
        assert len(assessments) >= 1

        # 6) Verify SkillLevelHistory has at least one level-up event
        result_hist = await db_session.execute(
            select(SkillLevelHistory).where(
                SkillLevelHistory.user_id == user.id,
                SkillLevelHistory.skill_id == skill.id,
            )
        )
        history_rows = list(result_hist.scalars().all())
        assert len(history_rows) >= 1

        # Ensure the most recent history row reflects a level increase
        latest = sorted(history_rows, key=lambda h: h.created_at)[-1]
        assert latest.from_level < latest.to_level
