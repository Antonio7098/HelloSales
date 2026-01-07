#!/usr/bin/env python3
"""Seed test data for curl scripts.

Creates (or reuses) a test user, session, and skill, then prints their IDs
as shell-friendly environment variable exports.

Usage:
    eval "$(python backend/tests/curl/seed_test_data.py)"
    # Now SESSION_ID and SKILL_ID are set in your shell
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

# Suppress SQLAlchemy logs BEFORE any imports
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

# Also suppress via env var
os.environ.setdefault("LOG_LEVEL", "WARNING")

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


async def main() -> None:
    from sqlalchemy import select

    from app.database import get_session_context
    from app.models import Session, Skill, User, UserSkill

    async with get_session_context() as db:
        # 1) Get or create test user
        test_subject = "test_curl_user"
        result = await db.execute(
            select(User).where(
                User.auth_provider == "clerk",
                User.auth_subject == test_subject,
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=uuid4(),
                auth_provider="clerk",
                auth_subject=test_subject,
                clerk_id=test_subject,
                email="curl-test@example.com",
                display_name="Curl Test User",
            )
            db.add(user)
            await db.flush()

        # 2) Create a fresh session for this user
        session = Session(id=uuid4(), user_id=user.id)
        db.add(session)
        await db.flush()

        # 3) Get any existing skill, or create a minimal one
        result = await db.execute(select(Skill).limit(1))
        skill = result.scalar_one_or_none()

        if not skill:
            skill = Skill(
                id=uuid4(),
                slug="clarity_eloquence",
                title="Clarity & Eloquence",
                description="Speak clearly and articulately.",
                category="core",
                levels=[
                    {"level": i, "criteria": f"Level {i} criteria", "examples": []}
                    for i in range(11)
                ],
            )
            db.add(skill)
            await db.flush()

        # 4) Ensure user is tracking this skill
        result = await db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user.id,
                UserSkill.skill_id == skill.id,
            )
        )
        user_skill = result.scalar_one_or_none()

        if not user_skill:
            user_skill = UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                current_level=0,
                is_tracked=True,
                track_order=1,
            )
            db.add(user_skill)

        await db.commit()

        # Output as shell exports
        print(f"export SESSION_ID={session.id}")
        print(f"export SKILL_ID={skill.id}")
        print(f"export USER_ID={user.id}")


if __name__ == "__main__":
    asyncio.run(main())
