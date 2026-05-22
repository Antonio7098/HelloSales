"""Auto-generated onboarding registry. /Oliviercontribution.

DO NOT edit by hand. Regenerate via:
    python3 backend/scripts/generate_onboarding_registry.py

Source: Google Sheet 1HGSlYMtxE9tbk15198wkg-U7n85vdO4u2oNCZP6B2Pw
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA: list[dict[str, Any]] = json.loads(
    (Path(__file__).parent / "_onboarding_registry.json").read_text(encoding="utf-8")
)

ONBOARDING_QUESTIONS: dict[str, dict[str, Any]] = {q["key"]: q for q in _DATA}


def get_phase_questions(phase: int) -> dict[str, dict[str, Any]]:
    return {k: v for k, v in ONBOARDING_QUESTIONS.items() if v.get("phase") == phase}


def get_section_questions(phase: int, section: str) -> dict[str, dict[str, Any]]:
    return {
        k: v for k, v in ONBOARDING_QUESTIONS.items()
        if v.get("phase") == phase and v.get("section") == section
    }


def get_phase_sections(phase: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in ONBOARDING_QUESTIONS.values():
        if v.get("phase") == phase and v.get("section") not in seen:
            seen.add(v["section"])
            out.append(v["section"])
    return out


PHASE_1_TOTAL = len(get_phase_questions(1))
PHASE_2_TOTAL = len(get_phase_questions(2))
PHASE_3_TOTAL = len(get_phase_questions(3))
TOTAL_QUESTIONS = PHASE_1_TOTAL + PHASE_2_TOTAL + PHASE_3_TOTAL

assert TOTAL_QUESTIONS == 114, f"Expected 114 questions, got {TOTAL_QUESTIONS}"


__all__ = [
    "ONBOARDING_QUESTIONS",
    "get_phase_questions",
    "get_section_questions",
    "get_phase_sections",
    "PHASE_1_TOTAL",
    "PHASE_2_TOTAL",
    "PHASE_3_TOTAL",
    "TOTAL_QUESTIONS",
]
