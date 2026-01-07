"""Unit tests for AssessmentService."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.providers.base import LLMResponse
from app.domains.assessment.service import AssessmentService
from app.models.assessment import Assessment, SkillAssessment
from app.models.skill import Skill, UserSkill
from app.schemas.assessment import AssessmentResponse, SkillFeedback


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession-like object."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_llm():
    """Create a mock LLM provider for assessment."""
    llm = AsyncMock()
    llm.name = "mock-assessment"
    return llm


@pytest.fixture
def assessment_service(mock_db, mock_llm):
    """Create an AssessmentService with mocked dependencies."""
    service = AssessmentService(db=mock_db, llm_provider=mock_llm)
    return service


@pytest.mark.asyncio
async def test_assess_response_skips_when_no_skills(assessment_service, mock_db):
    """If called with no skill IDs, assessment should short-circuit with empty result."""

    user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    response = await assessment_service.assess_response(
        user_id=user_id,
        session_id=session_id,
        interaction_id=None,
        user_response="Some response",
        skill_ids=[],
        send_status=None,
        triage_decision="assess",
    )

    assert isinstance(response, AssessmentResponse)
    assert response.assessment_id is None
    assert response.session_id == session_id
    assert response.skills == []
    assert response.metrics is not None
    assert response.metrics.assessment_latency_ms == 0
    assert response.metrics.total_cost_cents == 0

    # No DB writes should occur in this path
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_assess_response_happy_path_single_skill(assessment_service, mock_llm):
    """LLM JSON for a single skill is parsed and persisted into responses."""

    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    interaction_id = uuid.uuid4()

    # Prepare a Skill and UserSkill to be returned by _load_skills_and_progress
    skill = Skill(
        id=uuid.uuid4(),
        slug="clarity",
        title="Clarity",
        description="Test clarity skill",
        levels=[{"level": 0, "criteria": "", "examples": []}],
        category="test",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    user_skill = UserSkill(
        id=uuid.uuid4(),
        user_id=user_id,
        skill_id=skill.id,
        current_level=0,
        is_tracked=True,
        track_order=1,
        started_at=datetime.utcnow(),
        last_tracked_at=datetime.utcnow(),
    )

    skills_by_id = {skill.id: skill}
    user_skills_by_id = {skill.id: user_skill}

    # Patch _load_skills_and_progress to avoid real DB queries
    assessment_service._load_skills_and_progress = AsyncMock(
        return_value=(skills_by_id, user_skills_by_id)
    )

    # Mock LLM response content (single object for parallel per-skill assessment)
    llm_payload = {
        "skill_id": str(skill.id),
        "level": 4,
        "confidence": 0.9,
        "summary": "Good structure overall.",
        "feedback": {
            "primary_takeaway": "You are mostly clear but can tighten wording.",
            "strengths": ["Clear main point"],
            "improvements": ["Reduce filler words"],
            "example_quotes": [
                {
                    "quote": "I think the main idea is...",
                    "annotation": "Hesitation and filler phrase.",
                    "type": "improvement",
                }
            ],
            "next_level_criteria": "State your main point more directly.",
        },
    }

    mock_llm.generate.return_value = LLMResponse(
        content=__import__("json").dumps(llm_payload),
        model="mock-assessment",
        tokens_in=100,
        tokens_out=50,
    )

    # Patch persistence helpers to avoid real DB interaction while still
    # returning realistic model instances
    assessment = Assessment(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id,
        interaction_id=interaction_id,
        group_id=uuid.uuid4(),
        triage_decision="assess",
        created_at=datetime.utcnow(),
    )
    assessment_service._create_assessment_record = AsyncMock(return_value=assessment)

    sa_model = SkillAssessment(
        id=uuid.uuid4(),
        assessment_id=assessment.id,
        skill_id=skill.id,
        level=4,
        confidence=0.9,
        summary="Good structure overall.",
        feedback={
            "primary_takeaway": "You are mostly clear but can tighten wording.",
            "strengths": ["Clear main point"],
            "improvements": ["Reduce filler words"],
            "example_quotes": [],
            "next_level_criteria": "State your main point more directly.",
        },
        provider="mock-assessment",
        model_id="mock-model",
        tokens_used=150,
        cost_cents=1,
        latency_ms=500,
        created_at=datetime.utcnow(),
    )
    assessment_service._create_skill_assessment_record = AsyncMock(return_value=sa_model)

    # Don't test level progression logic here; just ensure it's invoked safely
    assessment_service.check_level_progression = AsyncMock(return_value=None)

    status_updates: list[tuple[str, str]] = []

    async def track_status(service: str, status: str, _meta):
        status_updates.append((service, status))

    response = await assessment_service.assess_response(
        user_id=user_id,
        session_id=session_id,
        interaction_id=interaction_id,
        user_response="The solution is straightforward...",
        skill_ids=[skill.id],
        send_status=track_status,
        triage_decision="assess",
    )

    # Top-level response
    assert isinstance(response, AssessmentResponse)
    assert response.assessment_id == assessment.id
    assert response.session_id == session_id
    assert response.interaction_id == interaction_id
    assert response.triage_decision == "assess"
    assert response.metrics is not None
    assert response.metrics.assessment_latency_ms is not None
    assert response.metrics.total_cost_cents is not None

    # Per-skill response
    assert len(response.skills) == 1
    skill_resp = response.skills[0]
    assert skill_resp.skill_id == skill.id
    assert skill_resp.level == 4
    assert skill_resp.confidence == 0.9
    assert skill_resp.summary == "Good structure overall."
    assert isinstance(skill_resp.feedback, SkillFeedback)
    assert "Clear main point" in skill_resp.feedback.strengths

    # Per-skill observability metrics should be populated from SkillAssessment
    assert skill_resp.latency_ms == sa_model.latency_ms
    assert skill_resp.tokens_used == sa_model.tokens_used
    assert skill_resp.cost_cents == sa_model.cost_cents

    # Status events
    assert ("assessment", "started") in status_updates
    assert ("assessment", "complete") in status_updates

    # LLM was called and persistence helpers invoked
    mock_llm.generate.assert_awaited_once()
    assessment_service._create_assessment_record.assert_awaited_once()
    assessment_service._create_skill_assessment_record.assert_awaited_once()


def test_parse_results_filters_and_clamps(assessment_service):
    """_parse_results should ignore unknown/invalid skills and clamp values."""

    from uuid import uuid4

    s1 = uuid4()
    s2 = uuid4()
    expected = [s1, s2]

    raw_payload = [
        {
            "skill_id": str(s1),
            "level": 13,  # should clamp to 10
            "confidence": 1.5,  # should clamp to 1.0
            "summary": "Overflow level",
            "feedback": {},
        },
        {
            "skill_id": str(s2),
            "level": -5,  # should clamp to 0
            "confidence": -0.2,  # should clamp to 0.0
            "summary": "Underflow level",
            "feedback": {},
        },
        {
            "skill_id": str(uuid4()),  # not in expected list → ignored
            "level": 7,
            "confidence": 0.7,
            "summary": "Unknown skill",
            "feedback": {},
        },
        {
            "skill_id": "not-a-uuid",  # invalid UUID → ignored
            "level": 5,
            "confidence": 0.5,
            "summary": "Bad UUID",
            "feedback": {},
        },
    ]

    import json as _json

    raw = _json.dumps(raw_payload)

    results = assessment_service._parse_results(raw, expected_skill_ids=expected)

    # Should only get 2 results, matching expected skill IDs
    assert len(results) == 2
    by_id = {item["skill_id"]: item for item in results}

    r1 = by_id[s1]
    assert r1["level"] == 10
    assert r1["confidence"] == 1.0

    r2 = by_id[s2]
    assert r2["level"] == 0
    assert r2["confidence"] == 0.0
