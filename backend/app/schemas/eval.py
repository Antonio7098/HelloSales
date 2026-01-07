"""Pydantic schemas for eval/benchmarking APIs (EVL-003)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


class EvalTestCaseExpectedAssessment(BaseModel):
    """Expected per-skill assessment ground truth for a test case."""

    skill_slug: str
    expected_level: int = Field(..., ge=0, le=10)
    level_tolerance: int | None = Field(default=1, ge=0, le=10)
    expected_keywords: list[str] | None = None
    notes: str | None = None


class EvalTestCaseBase(BaseModel):
    name: str
    transcript: str
    context_summary: str | None = None
    tracked_skills: list[str] | None = None
    expected_triage_decision: str | None = None
    triage_notes: str | None = None
    expected_assessments: list[EvalTestCaseExpectedAssessment] | None = None
    metadata: dict[str, Any] | None = None


class EvalTestCaseCreate(EvalTestCaseBase):
    pass


class EvalTestCaseUpdate(BaseModel):
    name: str | None = None
    transcript: str | None = None
    context_summary: str | None = None
    tracked_skills: list[str] | None = None
    expected_triage_decision: str | None = None
    triage_notes: str | None = None
    expected_assessments: list[EvalTestCaseExpectedAssessment] | None = None
    metadata: dict[str, Any] | None = None


class EvalTestCaseResponse(EvalTestCaseBase):
    id: UUID
    suite_id: UUID
    source_interaction_id: UUID | None = None
    source_session_id: UUID | None = None
    labeled_by: str | None = None
    labeled_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class EvalTestSuiteBase(BaseModel):
    name: str
    description: str | None = None


class EvalTestSuiteCreate(EvalTestSuiteBase):
    pass


class EvalTestSuiteResponse(EvalTestSuiteBase):
    id: UUID
    created_by: str | None = None
    created_at: datetime
    case_count: int | None = None

    class Config:
        from_attributes = True


class EvalTestSuiteWithCasesResponse(EvalTestSuiteResponse):
    test_cases: list[EvalTestCaseResponse]


# ---------------------------------------------------------------------------
# Benchmark runs & results
# ---------------------------------------------------------------------------


class EvalBenchmarkConfig(BaseModel):
    model_id: str
    prompt_version: str | None = None
    temperature: float | None = None
    extra: dict[str, Any] | None = None


class EvalBenchmarkRunCreate(BaseModel):
    suite_id: UUID
    name: str | None = None
    config: EvalBenchmarkConfig


class EvalBenchmarkRunSummary(BaseModel):
    avg_accuracy: float | None = None
    avg_latency_ms: float | None = None
    total_cost_cents: float | None = None
    triage_accuracy: float | None = None
    assessment_accuracy: float | None = None


class EvalBenchmarkRunResponse(BaseModel):
    id: UUID
    suite_id: UUID | None
    name: str | None
    config: dict[str, Any]
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    summary: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


class EvalTestResultAssessmentScore(BaseModel):
    skill_slug: str
    level_correct: bool | None = None
    within_tolerance: bool | None = None
    keyword_matches: list[str] | None = None


class EvalTestResultResponse(BaseModel):
    id: UUID
    run_id: UUID
    test_case_id: UUID
    actual_triage_decision: str | None
    triage_correct: bool | None
    triage_latency_ms: int | None
    actual_assessments: list[dict[str, Any]] | None = None
    assessment_scores: list[EvalTestResultAssessmentScore] | None = None
    overall_accuracy: float | None
    total_latency_ms: int | None
    tokens_in: int | None
    tokens_out: int | None
    cost_cents: float | None
    raw_response: dict[str, Any] | None
    error: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedTestResultsResponse(BaseModel):
    items: list[EvalTestResultResponse]
    page: int
    limit: int
    total: int


# ---------------------------------------------------------------------------
# Compare runs
# ---------------------------------------------------------------------------


class EvalRunComparisonPerCase(BaseModel):
    test_case_id: UUID
    case_name: str
    expected_triage_decision: str | None
    expected_assessments: list[EvalTestCaseExpectedAssessment] | None = None
    per_run: dict[str, EvalTestResultResponse]


class EvalRunComparisonResponse(BaseModel):
    run_summaries: dict[str, EvalBenchmarkRunSummary]
    cases: list[EvalRunComparisonPerCase]


# ---------------------------------------------------------------------------
# Golden dataset
# ---------------------------------------------------------------------------


class GoldenCaseBase(BaseModel):
    """Golden dataset entry stored in the JSONL golden file.

    This mirrors the structure defined in EVL-003 and the golden_dataset
    service. It is intentionally flexible and may contain additional fields
    in `metadata`.
    """

    id: str
    transcript: str
    skills: list[str]
    level_range: dict[str, Any] | None = None
    scenario: str | None = None
    expected_triage_decision: str | None = None
    expected_assessments: list[EvalTestCaseExpectedAssessment] | None = None
    source: str
    status: str
    source_interaction_id: str | None = None
    source_session_id: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class GoldenCaseResponse(GoldenCaseBase):
    pass


class GoldenCaseListResponse(BaseModel):
    items: list[GoldenCaseResponse]
    page: int
    limit: int
    total: int


class GoldenCaseUpdateRequest(BaseModel):
    status: str | None = None
    expected_triage_decision: str | None = None
    expected_assessments: list[EvalTestCaseExpectedAssessment] | None = None
    notes: str | None = None


class GoldenImportResponse(BaseModel):
    imported: int
