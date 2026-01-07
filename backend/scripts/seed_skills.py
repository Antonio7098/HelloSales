"""Seed the skills catalog from skills.json."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.database import get_session_factory
from app.models.skill import Skill

logger = logging.getLogger("seed.skills")


def _load_skills_file() -> list[dict[str, Any]]:
    """Load the skills JSON file from the repo root."""

    skills_path = Path(__file__).resolve().parents[2] / "skills.json"
    if not skills_path.exists():
        raise FileNotFoundError(f"skills.json not found at {skills_path}")

    with skills_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    skills = data.get("skills", [])
    if not isinstance(skills, list):
        raise ValueError("skills.json is malformed: 'skills' must be a list")
    return skills


def _normalize_levels(levels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize level data to the schema we store in the DB."""

    normalized = []
    for level in levels:
        raw_level = level["level"]
        # Clamp to valid range for SkillLevelCriteria (1-10)
        try:
            as_int = int(raw_level)
        except (TypeError, ValueError):
            as_int = 1

        normalized_level = max(1, min(as_int, 10))

        entry: dict[str, Any] = {
            "level": normalized_level,
            "criteria": level.get("criteria", ""),
            "examples": level.get("examples", []),
        }
        # Preserve rubric hints if present
        if hints := level.get("rubricHints"):
            entry["hints"] = hints
        normalized.append(entry)
    return normalized


async def seed_skills() -> None:
    """Seed (upsert) skills into the database from skills.json."""

    skills_data = _load_skills_file()
    session_factory = get_session_factory()
    inserted = 0
    updated = 0

    async with session_factory() as session:
        for skill_data in skills_data:
            slug = skill_data["id"]
            result = await session.execute(select(Skill).where(Skill.slug == slug))
            skill = result.scalar_one_or_none()

            payload = {
                "slug": slug,
                "title": skill_data["title"],
                "description": skill_data.get("description"),
                "category": skill_data.get("category"),
                "levels": _normalize_levels(skill_data.get("levels", [])),
                "is_active": bool(skill_data.get("isActive", True)),
            }

            if skill:
                for key, value in payload.items():
                    setattr(skill, key, value)
                updated += 1
            else:
                skill = Skill(
                    id=uuid4(),
                    created_at=datetime.utcnow(),
                    **payload,
                )
                session.add(skill)
                inserted += 1

        await session.commit()

    logger.info(
        "Seeded skills",
        extra={"service": "seed.skills", "inserted": inserted, "updated": updated},
    )
    print(f"✅ Skills seed complete (inserted={inserted}, updated={updated})")


def main() -> None:
    """Entry point for CLI usage."""

    asyncio.run(seed_skills())


if __name__ == "__main__":
    main()
