"""Auto-generated onboarding registry. /Oliviercontribution.

DO NOT edit by hand. Regenerate via:
    python3 backend/scripts/generate_onboarding_registry.py

Source: Google Sheet 1HGSlYMtxE9tbk15198wkg-U7n85vdO4u2oNCZP6B2Pw
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ONBOARDING_QUESTIONS: dict[str, dict[str, Any]] = {}


@lru_cache(maxsize=1)
def _load_registry() -> list[dict[str, Any]]:
    return json.loads(  # type: ignore[no-any-return]
        (Path(__file__).parent / "_onboarding_registry.json").read_text(encoding="utf-8")
    )


def _ensure_loaded() -> None:
    if not ONBOARDING_QUESTIONS:
        ONBOARDING_QUESTIONS.update({q["key"]: q for q in _load_registry()})


def get_onboarding_questions() -> dict[str, dict[str, Any]]:
    _ensure_loaded()
    return ONBOARDING_QUESTIONS


def get_phase_questions(phase: int) -> dict[str, dict[str, Any]]:
    _ensure_loaded()
    return {k: v for k, v in ONBOARDING_QUESTIONS.items() if v.get("phase") == phase}


def get_section_questions(phase: int, section: str) -> dict[str, dict[str, Any]]:
    _ensure_loaded()
    return {
        k: v for k, v in ONBOARDING_QUESTIONS.items()
        if v.get("phase") == phase and v.get("section") == section
    }


def get_phase_sections(phase: int) -> list[str]:
    _ensure_loaded()
    seen: set[str] = set()
    out: list[str] = []
    for v in ONBOARDING_QUESTIONS.values():
        if v.get("phase") == phase and v.get("section") not in seen:
            seen.add(v["section"])
            out.append(v["section"])
    return out


def get_phase_totals() -> tuple[int, int, int, int]:
    _ensure_loaded()
    p1 = sum(1 for q in ONBOARDING_QUESTIONS.values() if q.get("phase") == 1)
    p2 = sum(1 for q in ONBOARDING_QUESTIONS.values() if q.get("phase") == 2)
    p3 = sum(1 for q in ONBOARDING_QUESTIONS.values() if q.get("phase") == 3)
    return p1, p2, p3, p1 + p2 + p3


__all__ = [
    "ONBOARDING_QUESTIONS",
    "get_onboarding_questions",
    "get_phase_questions",
    "get_section_questions",
    "get_phase_sections",
    "get_phase_totals",
]
