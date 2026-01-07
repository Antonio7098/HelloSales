"""Seed rich assessment and progress history for a single user.

This script creates:
- Sessions with realistic timestamps
- Interactions within those sessions
- Assessments and per-skill SkillAssessment rows
- SkillLevelHistory rows that drive the progress dashboard

It is intended for local/dev usage to quickly populate the
progress dashboard and assessment history views.

Usage (from backend directory):

    # Use dev Clerk user (when running with dev_token / no Clerk secret)
    python scripts/seed_assessment_history.py

    # Or target a specific Clerk user id (e.g. from Clerk dashboard)
    python scripts/seed_assessment_history.py --clerk-id user_12345

    # Or target an existing DB user UUID directly
    python scripts/seed_assessment_history.py --user-id 01234567-89ab-cdef-0123-456789abcdef

Environment:
- Uses DATABASE_URL via app.config (same as the API)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database import get_session_context
from app.models import (
    Assessment,
    Interaction,
    Session,
    Skill,
    SkillAssessment,
    SkillLevelHistory,
    User,
    UserSkill,
)

logger = logging.getLogger("seed.history")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed rich assessment & progress history for a single user.",
    )

    user_group = parser.add_mutually_exclusive_group()
    user_group.add_argument(
        "--user-id",
        type=str,
        help="Existing DB user UUID (users.id)",
    )
    user_group.add_argument(
        "--clerk-id",
        type=str,
        help=(
            "Clerk user id (claims.sub). If omitted, defaults to dev_user_123 "
            "when no --user-id is provided."
        ),
    )

    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help=(
            "Email to use when creating a new user (only used if the user does not already exist)."
        ),
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="How many days back in time to spread sessions over (default: 14).",
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=12,
        help="How many sessions to create (default: 12).",
    )
    parser.add_argument(
        "--assessments-per-session",
        type=int,
        default=2,
        help="How many assessments to create per session on average (default: 2).",
    )
    parser.add_argument(
        "--skills-per-assessment",
        type=int,
        default=2,
        help="How many skills to include in each assessment (default: 2).",
    )
    parser.add_argument(
        "--max-skills",
        type=int,
        default=4,
        help=(
            "Maximum number of skills to track for this user (picked from active "
            "skills; default: 4)."
        ),
    )

    return parser.parse_args()


async def _get_or_create_user(
    *,
    user_id: UUID | None,
    clerk_id: str | None,
    email: str | None,
) -> User:
    """Resolve target user by DB id or Clerk id, creating if needed.

    In dev without Clerk configured, "dev_user_123" is a sensible default
    Clerk id that matches the backend's dev auth bypass.
    """

    async with get_session_context() as db:
        if user_id is not None:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None:
                raise SystemExit(f"No user found with id={user_id}")
            logger.info("Using existing user by id", extra={"user_id": str(user.id)})
            return user

        # Fall back to Clerk id path
        clerk_id = clerk_id or "dev_user_123"

        result = await db.execute(
            select(User).where(
                User.auth_provider == "clerk",
                User.auth_subject == clerk_id,
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            user_email = email or "dev@example.com"
            user = User(
                id=uuid4(),
                auth_provider="clerk",
                auth_subject=clerk_id,
                clerk_id=clerk_id,
                email=user_email,
                display_name=user_email.split("@")[0] if user_email else None,
            )
            db.add(user)
            await db.flush()
            logger.info(
                "Created new user",
                extra={
                    "clerk_id": clerk_id,
                    "user_id": str(user.id),
                    "email": user_email,
                },
            )
        else:
            logger.info(
                "Using existing user by clerk_id",
                extra={"clerk_id": clerk_id, "user_id": str(user.id)},
            )

        return user


async def seed_assessment_history(
    *,
    target_user_id: UUID | None,
    target_clerk_id: str | None,
    email: str | None,
    days: int,
    sessions: int,
    assessments_per_session: int,
    skills_per_assessment: int,
    max_skills: int,
) -> None:
    """Seed sessions, interactions, assessments, and skill history for a user."""

    if sessions <= 0:
        raise SystemExit("--sessions must be positive")
    if days <= 0:
        raise SystemExit("--days must be positive")

    user = await _get_or_create_user(user_id=target_user_id, clerk_id=target_clerk_id, email=email)

    async with get_session_context() as db:
        # 1) Load skills and pick a subset to track
        result = await db.execute(select(Skill).where(Skill.is_active).order_by(Skill.title))
        skills: list[Skill] = list(result.scalars().all())

        if not skills:
            raise SystemExit(
                "No skills found. Run scripts/seed_skills.py first to seed the skills catalog."
            )

        tracked_skills = skills[: max_skills or len(skills)]

        # 2) Ensure UserSkill rows exist for tracked skills
        result = await db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user.id, UserSkill.skill_id.in_([s.id for s in tracked_skills])
            )
        )
        existing_user_skills: list[UserSkill] = list(result.scalars().all())
        user_skills_by_skill: dict[UUID, UserSkill] = {
            us.skill_id: us for us in existing_user_skills
        }

        track_order = 1
        now = datetime.utcnow()

        for skill in tracked_skills:
            if skill.id in user_skills_by_skill:
                continue
            us = UserSkill(
                id=uuid4(),
                user_id=user.id,
                skill_id=skill.id,
                current_level=0,
                is_tracked=True,
                track_order=track_order,
                started_at=now - timedelta(days=days),
                last_tracked_at=None,
            )
            db.add(us)
            user_skills_by_skill[skill.id] = us
            track_order += 1

        # 3) Create sessions spread over the requested window
        sessions_created: list[Session] = []
        start_base = now - timedelta(days=days)
        total_seconds = days * 24 * 3600
        step = total_seconds / (sessions + 1)

        for i in range(sessions):
            started_at = start_base + timedelta(seconds=(i + 1) * step)
            ended_at = started_at + timedelta(minutes=random.randint(10, 40))

            session = Session(
                id=uuid4(),
                user_id=user.id,
                state="ended",
                started_at=started_at,
                ended_at=ended_at,
                total_cost_cents=0,
                interaction_count=0,
            )
            db.add(session)
            sessions_created.append(session)

        await db.flush()

        # 4) Create interactions and assessments per session
        assessments_by_skill: dict[UUID, list[Assessment]] = {}

        for idx, session in enumerate(sessions_created, start=1):
            # Interactions
            num_interactions = random.randint(4, 8)
            interactions: list[Interaction] = []

            for j in range(num_interactions):
                role = "user" if j % 2 == 0 else "assistant"
                created_at = session.started_at + timedelta(
                    minutes=(j + 1)
                    * ((session.ended_at - session.started_at).total_seconds() / 60)
                    / (num_interactions + 1)
                )
                content = (
                    f"Sample {role} message {j + 1} in session {idx}. "
                    f"This is synthetic data for progress seeding."
                )

                interaction = Interaction(
                    id=uuid4(),
                    session_id=session.id,
                    message_id=uuid4(),
                    role=role,
                    input_type="text" if role == "user" else None,
                    content=content,
                    transcript=None,
                    audio_url=None,
                    audio_duration_ms=None,
                    stt_cost_cents=0,
                    llm_cost_cents=0,
                    tts_cost_cents=0,
                    latency_ms=None,
                    tokens_in=None,
                    tokens_out=None,
                    created_at=created_at,
                )
                db.add(interaction)
                interactions.append(interaction)

            session.interaction_count = len(interactions)
            session.duration_ms = int(
                (session.ended_at - session.started_at).total_seconds() * 1000
            )

            # Assessments
            user_interactions = [it for it in interactions if it.role == "user"] or interactions
            if not user_interactions:
                continue

            num_assessments = max(1, assessments_per_session)

            for _ in range(num_assessments):
                interaction = random.choice(user_interactions)
                created_at = interaction.created_at + timedelta(minutes=1)

                assessment = Assessment(
                    id=uuid4(),
                    user_id=user.id,
                    session_id=session.id,
                    interaction_id=interaction.id,
                    group_id=uuid4(),
                    triage_decision="skill_practice",
                    created_at=created_at,
                )
                db.add(assessment)

                # Per-skill assessments
                chosen_skills = random.sample(
                    tracked_skills,
                    k=min(max(1, skills_per_assessment), len(tracked_skills)),
                )

                for skill in chosen_skills:
                    base_level = user_skills_by_skill[skill.id].current_level
                    level = max(0, min(10, base_level + random.randint(0, 3)))

                    feedback: dict[str, Any] = {
                        "primary_takeaway": "Synthetic feedback for seeded history.",
                        "strengths": ["Clear structure", "Good pacing"],
                        "improvements": ["Add more concrete examples"],
                        "example_quotes": [
                            {
                                "quote": "This is a dummy quote from your response.",
                                "annotation": "Used to illustrate seeded feedback.",
                                "type": "strength",
                            }
                        ],
                        "next_level_criteria": "Focus on varying tone and adding vivid details.",
                    }

                    sa = SkillAssessment(
                        id=uuid4(),
                        assessment_id=assessment.id,
                        skill_id=skill.id,
                        level=level,
                        confidence=0.7 + random.random() * 0.3,
                        summary="Synthetic assessment result for seeded data.",
                        feedback=feedback,
                        provider="seed_script",
                        model_id=None,
                        tokens_used=None,
                        cost_cents=None,
                        latency_ms=None,
                        created_at=created_at,
                    )
                    db.add(sa)

                    assessments_by_skill.setdefault(skill.id, []).append(assessment)

        # 5) Create SkillLevelHistory to show level progression over time
        for skill_id, assessments in assessments_by_skill.items():
            if not assessments:
                continue

            assessments_sorted = sorted(assessments, key=lambda a: a.created_at)
            user_skill = user_skills_by_skill.get(skill_id)
            if user_skill is None:
                continue

            level = 0
            # Use up to 5 assessments to generate level-up events
            for assessment in assessments_sorted[:5]:
                new_level = min(10, level + random.randint(1, 2))
                history = SkillLevelHistory(
                    id=uuid4(),
                    user_id=user.id,
                    skill_id=skill_id,
                    from_level=level,
                    to_level=new_level,
                    reason="seed_script",
                    source_assessment_id=assessment.id,
                    created_at=assessment.created_at,
                )
                db.add(history)
                level = new_level

            user_skill.current_level = max(user_skill.current_level, level)
            user_skill.last_tracked_at = now

        logger.info(
            "Seeded assessment history",
            extra={
                "user_id": str(user.id),
                "sessions": len(sessions_created),
                "skills": len(tracked_skills),
            },
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()

    user_id: UUID | None = None
    if args.user_id:
        try:
            user_id = UUID(args.user_id)
        except ValueError as exc:  # pragma: no cover - CLI validation
            raise SystemExit(f"Invalid --user-id UUID: {exc}") from exc

    asyncio.run(
        seed_assessment_history(
            target_user_id=user_id,
            target_clerk_id=args.clerk_id,
            email=args.email,
            days=args.days,
            sessions=args.sessions,
            assessments_per_session=args.assessments_per_session,
            skills_per_assessment=args.skills_per_assessment,
            max_skills=args.max_skills,
        )
    )


if __name__ == "__main__":
    main()
