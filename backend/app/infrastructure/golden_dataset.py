"""Golden dataset file utilities for EVL-003.

Golden cases are stored in a JSONL file in the main repo under
`docs/eval-golden/golden-cases.jsonl`. Each line is a single JSON object
with a stable `id` and fields compatible with EvalTestCaseExpectedAssessment.

This module provides small helpers to read, filter, update, and write the
file. It is intentionally simple and does not use the database; production
imports are responsible for creating entries in this file.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

# Project root: backend/app/infrastructure -> backend/app -> backend -> project
_PROJECT_ROOT = Path(__file__).resolve().parents[2].parent
GOLDEN_DIR = _PROJECT_ROOT / "docs" / "eval-golden"
GOLDEN_FILE = GOLDEN_DIR / "golden-cases.jsonl"

GoldenStatus = Literal["pending_review", "approved", "rejected"]


@dataclass
class GoldenCase:
    """In-memory representation of a golden dataset case.

    This is a superset of the JSON structure documented in EVL-003. Extra
    fields are allowed and will be preserved round-trip.
    """

    id: str
    transcript: str
    expected_triage_decision: str | None
    expected_assessments: list[dict[str, Any]] | None
    skills: list[str]
    level_range: dict[str, Any] | None
    scenario: str | None
    source: str
    status: GoldenStatus
    source_interaction_id: str | None
    source_session_id: str | None
    notes: str | None
    metadata: dict[str, Any]
    created_at: str
    reviewed_by: str | None
    reviewed_at: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldenCase:
        """Create a GoldenCase from a raw dict, filling defaults.

        Unknown keys are ignored; missing keys are given sensible defaults so
        older entries remain compatible.
        """

        skills = data.get("skills") or []
        if not isinstance(skills, list):
            skills = []

        level_range = data.get("level_range")
        if level_range is not None and not isinstance(level_range, dict):
            level_range = None

        expected_assessments_raw = data.get("expected_assessments") or []
        if isinstance(expected_assessments_raw, dict):
            expected_assessments = [expected_assessments_raw]
        elif isinstance(expected_assessments_raw, list):
            expected_assessments = list(expected_assessments_raw)
        else:
            expected_assessments = []

        status = data.get("status") or "pending_review"
        if status not in ("pending_review", "approved", "rejected"):
            status = "pending_review"

        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

        created_at = data.get("created_at") or datetime.utcnow().isoformat()
        reviewed_at = data.get("reviewed_at")

        return cls(
            id=str(data.get("id") or uuid4()),
            transcript=str(data.get("transcript") or ""),
            expected_triage_decision=data.get("expected_triage_decision"),
            expected_assessments=expected_assessments,
            skills=skills,
            level_range=level_range,
            scenario=data.get("scenario"),
            source=str(data.get("source") or "generated"),
            status=status,  # type: ignore[assignment]
            source_interaction_id=(
                str(data["source_interaction_id"]) if data.get("source_interaction_id") else None
            ),
            source_session_id=(
                str(data["source_session_id"]) if data.get("source_session_id") else None
            ),
            notes=data.get("notes"),
            metadata=metadata,
            created_at=created_at,
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=reviewed_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSONL storage."""

        return asdict(self)


def _ensure_file_exists() -> None:
    """Ensure the golden dataset directory and file exist."""

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    if not GOLDEN_FILE.exists():
        GOLDEN_FILE.touch()


def load_all_golden_cases() -> list[GoldenCase]:
    """Load all golden cases from the JSONL file.

    Malformed lines are ignored rather than failing the whole load.
    """

    if not GOLDEN_FILE.exists():
        return []

    cases: list[GoldenCase] = []
    with GOLDEN_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            cases.append(GoldenCase.from_dict(raw))
    return cases


def write_all_golden_cases(cases: Iterable[GoldenCase]) -> None:
    """Write all golden cases back to the JSONL file."""

    _ensure_file_exists()
    with GOLDEN_FILE.open("w", encoding="utf-8") as f:
        for case in cases:
            json.dump(case.to_dict(), f, ensure_ascii=False)
            f.write("\n")


def upsert_golden_cases(new_cases: Iterable[GoldenCase]) -> None:
    """Upsert a batch of golden cases by id.

    Existing cases with the same id are replaced; others are appended.
    """

    existing = {case.id: case for case in load_all_golden_cases()}
    for case in new_cases:
        existing[case.id] = case
    write_all_golden_cases(existing.values())


def filter_golden_cases(
    *,
    status: GoldenStatus | None = None,
    source: str | None = None,
    skill: str | None = None,
) -> list[GoldenCase]:
    """Return golden cases matching simple filters.

    - `status`: pending_review | approved | rejected
    - `source`: arbitrary string match (e.g. "generated", "production")
    - `skill`: matches entries where the skill is present in `skills` or in
      any `expected_assessments[].skill_slug`.
    """

    cases = load_all_golden_cases()
    filtered: list[GoldenCase] = []

    for case in cases:
        if status is not None and case.status != status:
            continue
        if source is not None and case.source != source:
            continue
        if skill is not None and skill not in case.skills:
            # Fallback: check expected_assessments
            found = False
            for item in case.expected_assessments or []:
                slug = item.get("skill_slug") if isinstance(item, dict) else None
                if slug == skill:
                    found = True
                    break
            if not found:
                continue
        filtered.append(case)

    return filtered


def find_golden_case(case_id: str) -> GoldenCase | None:
    """Find a single golden case by id, if present."""

    for case in load_all_golden_cases():
        if case.id == case_id:
            return case
    return None


def dedupe_by_source_interaction(new_cases: Iterable[GoldenCase]) -> list[GoldenCase]:
    """Return only new cases whose `source_interaction_id` is not already present.

    This is used by the production import endpoint to avoid creating
    duplicate golden entries for the same interaction.
    """

    existing = load_all_golden_cases()
    existing_ids = {
        case.source_interaction_id for case in existing if case.source_interaction_id is not None
    }

    unique_new: list[GoldenCase] = []
    for case in new_cases:
        if case.source_interaction_id and case.source_interaction_id in existing_ids:
            continue
        unique_new.append(case)
    return unique_new
