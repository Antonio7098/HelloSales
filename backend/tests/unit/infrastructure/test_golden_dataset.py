from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.infrastructure import golden_dataset as gd


def _setup_temp_golden(monkeypatch, tmp_path: Path) -> None:
    golden_dir = tmp_path / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)
    golden_file = golden_dir / "golden-cases.jsonl"
    monkeypatch.setattr(gd, "GOLDEN_DIR", golden_dir)
    monkeypatch.setattr(gd, "GOLDEN_FILE", golden_file)


def test_upsert_and_load_roundtrip(monkeypatch, tmp_path) -> None:
    _setup_temp_golden(monkeypatch, tmp_path)

    case = gd.GoldenCase(
        id=str(uuid4()),
        transcript="Example transcript",
        expected_triage_decision="skill_practice",
        expected_assessments=[
            {
                "skill_slug": "clarity",
                "expected_level": 6,
                "level_tolerance": 1,
                "expected_keywords": ["structure"],
                "notes": None,
            }
        ],
        skills=["clarity"],
        level_range={"min": 5, "max": 7},
        scenario="elevator_pitch",
        source="generated",
        status="pending_review",  # type: ignore[arg-type]
        source_interaction_id=None,
        source_session_id=None,
        notes=None,
        metadata={"name": "Clarity – elevator pitch"},
        created_at=datetime.utcnow().isoformat(),
        reviewed_by=None,
        reviewed_at=None,
    )

    gd.upsert_golden_cases([case])
    loaded = gd.load_all_golden_cases()

    assert len(loaded) == 1
    loaded_case = loaded[0]
    assert loaded_case.id == case.id
    assert loaded_case.transcript == case.transcript
    assert loaded_case.expected_triage_decision == "skill_practice"
    assert loaded_case.skills == ["clarity"]


def test_filter_golden_cases_by_status_and_skill(monkeypatch, tmp_path) -> None:
    _setup_temp_golden(monkeypatch, tmp_path)

    base_kwargs = {
        "transcript": "t",
        "expected_triage_decision": "skill_practice",
        "expected_assessments": [],
        "skills": ["clarity"],
        "level_range": None,
        "scenario": None,
        "source": "generated",
        "source_interaction_id": None,
        "source_session_id": None,
        "notes": None,
        "metadata": {},
        "created_at": datetime.utcnow().isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
    }

    case_pending = gd.GoldenCase(id="pending-1", status="pending_review", **base_kwargs)  # type: ignore[arg-type]
    case_approved = gd.GoldenCase(id="approved-1", status="approved", **base_kwargs)  # type: ignore[arg-type]

    gd.write_all_golden_cases([case_pending, case_approved])

    pending = gd.filter_golden_cases(status="pending_review")
    assert len(pending) == 1
    assert pending[0].id == "pending-1"

    approved = gd.filter_golden_cases(status="approved")
    assert len(approved) == 1
    assert approved[0].id == "approved-1"

    clarity = gd.filter_golden_cases(skill="clarity")
    assert {c.id for c in clarity} == {"pending-1", "approved-1"}


def test_dedupe_by_source_interaction(monkeypatch, tmp_path) -> None:
    _setup_temp_golden(monkeypatch, tmp_path)

    base_kwargs = {
        "transcript": "t",
        "expected_triage_decision": "skill_practice",
        "expected_assessments": [],
        "skills": ["clarity"],
        "level_range": None,
        "scenario": None,
        "source": "production",
        "status": "pending_review",  # type: ignore[arg-type]
        "source_session_id": None,
        "notes": None,
        "metadata": {},
        "created_at": datetime.utcnow().isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
    }

    existing = gd.GoldenCase(
        id="existing",
        source_interaction_id="interaction-1",
        **base_kwargs,
    )
    new_same = gd.GoldenCase(
        id="new-same",
        source_interaction_id="interaction-1",
        **base_kwargs,
    )
    new_other = gd.GoldenCase(
        id="new-other",
        source_interaction_id="interaction-2",
        **base_kwargs,
    )

    gd.write_all_golden_cases([existing])
    unique = gd.dedupe_by_source_interaction([new_same, new_other])

    # Only the case with a new interaction id should be kept
    assert [c.id for c in unique] == ["new-other"]
