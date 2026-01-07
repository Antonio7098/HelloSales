"""Admin APIs for eval/benchmarking (test suites & runs).

Implements part of EVL-003: basic test suite CRUD and stubs for runs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.domains.assessment.benchmark import BenchmarkRunner
from app.infrastructure.golden_dataset import (
    GoldenCase,
    dedupe_by_source_interaction,
    filter_golden_cases,
    find_golden_case,
    upsert_golden_cases,
)
from app.models import (
    Assessment,
    EvalBenchmarkRun,
    EvalTestCase,
    EvalTestResult,
    EvalTestSuite,
    Interaction,
    Session,
    Skill,
    SkillAssessment,
    TriageLog,
)
from app.schemas.eval import (
    EvalBenchmarkRunCreate,
    EvalBenchmarkRunResponse,
    EvalRunComparisonResponse,
    EvalTestCaseCreate,
    EvalTestCaseResponse,
    EvalTestCaseUpdate,
    EvalTestResultResponse,
    EvalTestSuiteCreate,
    EvalTestSuiteResponse,
    EvalTestSuiteWithCasesResponse,
    GoldenCaseListResponse,
    GoldenCaseResponse,
    GoldenCaseUpdateRequest,
    GoldenImportResponse,
    PaginatedTestResultsResponse,
)

router = APIRouter(prefix="/eval", tags=["eval"])


# ---------------------------------------------------------------------------
# Test suites
# ---------------------------------------------------------------------------


@router.get("/suites", response_model=list[EvalTestSuiteResponse])
async def list_eval_suites(
    session: AsyncSession = Depends(get_session),
) -> list[EvalTestSuiteResponse]:
    """List all eval test suites (no pagination for now) with case counts."""

    result = await session.execute(
        select(EvalTestSuite, func.count(EvalTestCase.id).label("case_count"))
        .outerjoin(EvalTestCase, EvalTestCase.suite_id == EvalTestSuite.id)
        .group_by(EvalTestSuite.id)
        .order_by(EvalTestSuite.created_at.desc())
    )
    items: list[EvalTestSuiteResponse] = []
    for suite, case_count in result.all():
        items.append(
            EvalTestSuiteResponse(
                id=suite.id,
                name=suite.name,
                description=suite.description,
                created_by=suite.created_by,
                created_at=suite.created_at,
                case_count=int(case_count or 0),
            )
        )
    return items


@router.post("/suites", response_model=EvalTestSuiteResponse)
async def create_eval_suite(
    payload: EvalTestSuiteCreate,
    session: AsyncSession = Depends(get_session),
) -> EvalTestSuiteResponse:
    """Create a new eval test suite."""

    suite = EvalTestSuite(
        name=payload.name,
        description=payload.description,
    )
    session.add(suite)
    await session.flush()
    await session.refresh(suite)
    return EvalTestSuiteResponse.model_validate(suite)


@router.get("/suites/{suite_id}", response_model=EvalTestSuiteWithCasesResponse)
async def get_eval_suite_detail(
    suite_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EvalTestSuiteWithCasesResponse:
    """Get a test suite and all its test cases."""

    result = await session.execute(select(EvalTestSuite).where(EvalTestSuite.id == suite_id))
    suite = result.scalar_one_or_none()
    if suite is None:
        raise HTTPException(status_code=404, detail="Suite not found")

    case_result = await session.execute(
        select(EvalTestCase)
        .where(EvalTestCase.suite_id == suite_id)
        .order_by(EvalTestCase.created_at.asc())
    )
    cases = list(case_result.scalars().all())

    return EvalTestSuiteWithCasesResponse(
        id=suite.id,
        name=suite.name,
        description=suite.description,
        created_by=suite.created_by,
        created_at=suite.created_at,
        case_count=len(cases),
        test_cases=[
            EvalTestCaseResponse(
                id=c.id,
                suite_id=c.suite_id,
                name=c.name,
                transcript=c.transcript,
                context_summary=c.context_summary,
                tracked_skills=c.tracked_skills,
                expected_triage_decision=c.expected_triage_decision,
                triage_notes=c.triage_notes,
                expected_assessments=c.expected_assessments,
                metadata=c.metadata_json,
                source_interaction_id=c.source_interaction_id,
                source_session_id=c.source_session_id,
                labeled_by=c.labeled_by,
                labeled_at=c.labeled_at,
                created_at=c.created_at,
            )
            for c in cases
        ],
    )


@router.delete(
    "/suites/{suite_id}",
    status_code=204,
    response_class=Response,
    response_model=None,
)
async def delete_eval_suite(
    suite_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a test suite and its cases/runs."""

    result = await session.execute(select(EvalTestSuite).where(EvalTestSuite.id == suite_id))
    suite = result.scalar_one_or_none()
    if suite is None:
        raise HTTPException(status_code=404, detail="Suite not found")

    await session.delete(suite)

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@router.post("/suites/{suite_id}/cases", response_model=EvalTestCaseResponse)
async def add_eval_test_case(
    suite_id: UUID,
    payload: EvalTestCaseCreate,
    session: AsyncSession = Depends(get_session),
) -> EvalTestCaseResponse:
    """Add a single test case to a suite."""

    result = await session.execute(select(EvalTestSuite).where(EvalTestSuite.id == suite_id))
    suite = result.scalar_one_or_none()
    if suite is None:
        raise HTTPException(status_code=404, detail="Suite not found")

    case = EvalTestCase(
        suite_id=suite.id,
        name=payload.name,
        transcript=payload.transcript,
        context_summary=payload.context_summary,
        tracked_skills=payload.tracked_skills,
        expected_triage_decision=payload.expected_triage_decision,
        triage_notes=payload.triage_notes,
        expected_assessments=[a.model_dump() for a in (payload.expected_assessments or [])],
        metadata_json=payload.metadata or {},
    )
    session.add(case)
    await session.flush()
    await session.refresh(case)

    return EvalTestCaseResponse(
        id=case.id,
        suite_id=case.suite_id,
        name=case.name,
        transcript=case.transcript,
        context_summary=case.context_summary,
        tracked_skills=case.tracked_skills,
        expected_triage_decision=case.expected_triage_decision,
        triage_notes=case.triage_notes,
        expected_assessments=case.expected_assessments,
        metadata=case.metadata_json,
        source_interaction_id=case.source_interaction_id,
        source_session_id=case.source_session_id,
        labeled_by=case.labeled_by,
        labeled_at=case.labeled_at,
        created_at=case.created_at,
    )


@router.put("/suites/{suite_id}/cases/{case_id}", response_model=EvalTestCaseResponse)
async def update_eval_test_case(
    suite_id: UUID,
    case_id: UUID,
    payload: EvalTestCaseUpdate,
    session: AsyncSession = Depends(get_session),
) -> EvalTestCaseResponse:
    """Update fields on a single test case in a suite."""

    result = await session.execute(
        select(EvalTestCase).where(
            EvalTestCase.id == case_id,
            EvalTestCase.suite_id == suite_id,
        )
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Test case not found")

    if payload.name is not None:
        case.name = payload.name
    if payload.transcript is not None:
        case.transcript = payload.transcript
    if payload.context_summary is not None:
        case.context_summary = payload.context_summary
    if payload.tracked_skills is not None:
        case.tracked_skills = payload.tracked_skills
    if payload.expected_triage_decision is not None:
        case.expected_triage_decision = payload.expected_triage_decision
    if payload.triage_notes is not None:
        case.triage_notes = payload.triage_notes
    if payload.expected_assessments is not None:
        case.expected_assessments = [a.model_dump() for a in payload.expected_assessments]
    if payload.metadata is not None:
        case.metadata_json = payload.metadata

    await session.flush()
    await session.refresh(case)

    return EvalTestCaseResponse(
        id=case.id,
        suite_id=case.suite_id,
        name=case.name,
        transcript=case.transcript,
        context_summary=case.context_summary,
        tracked_skills=case.tracked_skills,
        expected_triage_decision=case.expected_triage_decision,
        triage_notes=case.triage_notes,
        expected_assessments=case.expected_assessments,
        metadata=case.metadata_json,
        source_interaction_id=case.source_interaction_id,
        source_session_id=case.source_session_id,
        labeled_by=case.labeled_by,
        labeled_at=case.labeled_at,
        created_at=case.created_at,
    )


@router.delete(
    "/suites/{suite_id}/cases/{case_id}",
    status_code=204,
    response_class=Response,
    response_model=None,
)
async def delete_eval_test_case(
    suite_id: UUID,
    case_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a single test case from a suite."""

    result = await session.execute(
        select(EvalTestCase).where(EvalTestCase.id == case_id, EvalTestCase.suite_id == suite_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Test case not found")

    await session.delete(case)

    return Response(status_code=204)


class EvalTestCasesImportBody(BaseModel):
    """Request body for importing multiple test cases.

    Only JSON import is supported for now; CSV can be added later.
    """

    cases: list[EvalTestCaseCreate]


@router.post("/suites/{suite_id}/import")
async def import_eval_test_cases(
    suite_id: UUID,
    payload: EvalTestCasesImportBody | None = None,
    source: str | None = Query(  # type: ignore[assignment]
        None,
        description="Import source: leave empty for JSON payload, or 'golden' to import from golden dataset",
    ),
    skills: str | None = Query(
        None,
        description="Comma-separated list of skill slugs when importing from golden dataset",
    ),
    triage_decision: str | None = Query(
        None,
        description="Filter golden cases by expected_triage_decision when importing from golden dataset",
    ),
    min_level: int | None = Query(
        None,
        ge=0,
        le=10,
        description="Minimum expected_level when importing from golden dataset",
    ),
    max_level: int | None = Query(
        None,
        ge=0,
        le=10,
        description="Maximum expected_level when importing from golden dataset",
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Bulk import test cases into a suite.

    Accepts a JSON body with a list of cases. Returns the number of
    successfully imported cases.
    """

    result = await session.execute(select(EvalTestSuite).where(EvalTestSuite.id == suite_id))
    suite = result.scalar_one_or_none()
    if suite is None:
        raise HTTPException(status_code=404, detail="Suite not found")

    # Import from golden dataset into this suite
    if source == "golden":
        cases = filter_golden_cases(status="approved")

        # Optional filters
        if skills:
            skill_slugs = [s.strip() for s in skills.split(",") if s.strip()]

            def _matches_skills(g: GoldenCase) -> bool:
                if any(slug in (g.skills or []) for slug in skill_slugs):
                    return True
                for item in g.expected_assessments or []:
                    slug = item.get("skill_slug") if isinstance(item, dict) else None
                    if slug in skill_slugs:
                        return True
                return False

            cases = [g for g in cases if _matches_skills(g)]

        if triage_decision:
            cases = [g for g in cases if g.expected_triage_decision == triage_decision]

        if min_level is not None or max_level is not None:

            def _in_level_range(g: GoldenCase) -> bool:
                levels: list[int] = []
                for item in g.expected_assessments or []:
                    if not isinstance(item, dict):
                        continue
                    try:
                        levels.append(int(item.get("expected_level", 0)))
                    except Exception:
                        continue
                if not levels:
                    return False
                min_lv = min(levels)
                max_lv = max(levels)
                if min_level is not None and max_lv < min_level:
                    return False
                return not (max_level is not None and min_lv > max_level)

            cases = [g for g in cases if _in_level_range(g)]

        imported = 0
        for golden in cases:
            # Prefer explicit skills list; fall back to expected_assessments
            tracked_skills = list(golden.skills)
            if not tracked_skills:
                tracked_skills = [
                    item.get("skill_slug")
                    for item in (golden.expected_assessments or [])
                    if isinstance(item, dict) and item.get("skill_slug")
                ]

            name = golden.metadata.get("name") if isinstance(golden.metadata, dict) else None
            if not name:
                if golden.scenario:
                    name = f"Golden: {golden.scenario}"
                else:
                    name = f"Golden case {golden.id[:8]}"

            source_interaction_uuid = None
            if golden.source_interaction_id:
                try:
                    source_interaction_uuid = UUID(golden.source_interaction_id)
                except Exception:
                    source_interaction_uuid = None

            source_session_uuid = None
            if golden.source_session_id:
                try:
                    source_session_uuid = UUID(golden.source_session_id)
                except Exception:
                    source_session_uuid = None

            case = EvalTestCase(
                suite_id=suite.id,
                name=name,
                transcript=golden.transcript,
                context_summary=None,
                tracked_skills=tracked_skills or None,
                expected_triage_decision=golden.expected_triage_decision,
                triage_notes=golden.notes,
                expected_assessments=golden.expected_assessments or [],
                metadata_json=golden.metadata or {},
                source_interaction_id=source_interaction_uuid,
                source_session_id=source_session_uuid,
            )
            session.add(case)
            imported += 1

        await session.flush()
        return {"imported": imported}

    # Default: import from JSON payload
    if payload is None:
        raise HTTPException(status_code=400, detail="Missing import payload")

    imported = 0
    for item in payload.cases:
        case = EvalTestCase(
            suite_id=suite.id,
            name=item.name,
            transcript=item.transcript,
            context_summary=item.context_summary,
            tracked_skills=item.tracked_skills,
            expected_triage_decision=item.expected_triage_decision,
            triage_notes=item.triage_notes,
            expected_assessments=[a.model_dump() for a in (item.expected_assessments or [])],
            metadata_json=item.metadata or {},
        )
        session.add(case)
        imported += 1

    await session.flush()
    return {"imported": imported}


# ---------------------------------------------------------------------------
# Benchmark runs (stubs)
# ---------------------------------------------------------------------------


@router.post("/runs", response_model=EvalBenchmarkRunResponse)
async def start_benchmark_run(
    payload: EvalBenchmarkRunCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> EvalBenchmarkRunResponse:
    """Start a benchmark run for a suite.

    For now this only creates a run record with status=pending.
    The actual runner service will be implemented in a later step.
    """

    # Ensure suite exists
    result = await session.execute(
        select(EvalTestSuite).where(EvalTestSuite.id == payload.suite_id)
    )
    suite = result.scalar_one_or_none()
    if suite is None:
        raise HTTPException(status_code=404, detail="Suite not found")

    run = EvalBenchmarkRun(
        suite_id=payload.suite_id,
        name=payload.name,
        config=payload.config.model_dump(),
        status="pending",
    )
    session.add(run)
    await session.flush()
    await session.refresh(run)

    # Kick off the benchmark runner in the background.
    runner = BenchmarkRunner(session)
    background_tasks.add_task(runner.run, run.id)

    return EvalBenchmarkRunResponse.model_validate(run)


@router.get("/runs/{run_id}", response_model=EvalBenchmarkRunResponse)
async def get_benchmark_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> EvalBenchmarkRunResponse:
    """Get a benchmark run status + summary."""

    result = await session.execute(select(EvalBenchmarkRun).where(EvalBenchmarkRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return EvalBenchmarkRunResponse.model_validate(run)


@router.get("/runs/{run_id}/results", response_model=PaginatedTestResultsResponse)
async def list_benchmark_run_results(
    run_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> PaginatedTestResultsResponse:
    """List results for a benchmark run (paginated)."""

    # Ensure run exists
    run_result = await session.execute(
        select(EvalBenchmarkRun).where(EvalBenchmarkRun.id == run_id)
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    total_result = await session.execute(
        select(func.count(EvalTestResult.id)).where(EvalTestResult.run_id == run_id)
    )
    total = int(total_result.scalar_one() or 0)

    offset = (page - 1) * limit
    rows_result = await session.execute(
        select(EvalTestResult)
        .where(EvalTestResult.run_id == run_id)
        .order_by(EvalTestResult.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    items = [EvalTestResultResponse.model_validate(row) for row in rows_result.scalars().all()]

    return PaginatedTestResultsResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
    )


@router.get("/compare", response_model=EvalRunComparisonResponse)
async def compare_benchmark_runs(
    run_ids: str = Query(..., description="Comma-separated list of run IDs to compare"),
    session: AsyncSession = Depends(get_session),
) -> EvalRunComparisonResponse:
    """Compare multiple runs side-by-side for shared test cases.

    This is a minimal implementation that aggregates accuracy/latency/cost
    per run and aligns results by test_case_id.
    """

    try:
        run_id_list = [UUID(part.strip()) for part in run_ids.split(",") if part.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_ids format")

    if not run_id_list:
        raise HTTPException(status_code=400, detail="No run_ids provided")

    runs_result = await session.execute(
        select(EvalBenchmarkRun).where(EvalBenchmarkRun.id.in_(run_id_list))
    )
    runs = list(runs_result.scalars().all())
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found")

    # Load all results for these runs, joined with test cases
    joined_result = await session.execute(
        select(EvalTestResult, EvalTestCase)
        .join(EvalTestCase, EvalTestResult.test_case_id == EvalTestCase.id)
        .where(EvalTestResult.run_id.in_(run_id_list))
    )

    # Build summaries and per-case comparison
    from app.schemas.eval import (
        EvalBenchmarkRunSummary,
        EvalRunComparisonPerCase,
        EvalTestResultResponse,
    )

    run_summaries: dict[str, EvalBenchmarkRunSummary] = {}
    per_run_accumulator: dict[UUID, dict[str, Any]] = {}
    cases_map: dict[UUID, EvalRunComparisonPerCase] = {}

    for result_row, case in joined_result.all():
        run_id_val: UUID = result_row.run_id
        run_key = str(run_id_val)

        # Accumulate metrics per run
        acc = per_run_accumulator.setdefault(
            run_id_val,
            {
                "accuracy_sum": 0.0,
                "accuracy_count": 0,
                "latency_sum": 0.0,
                "latency_count": 0,
                "triage_correct_count": 0,
                "triage_total": 0,
                "cost_sum": 0.0,
            },
        )

        if result_row.overall_accuracy is not None:
            acc["accuracy_sum"] += float(result_row.overall_accuracy)
            acc["accuracy_count"] += 1

        if result_row.total_latency_ms is not None:
            acc["latency_sum"] += float(result_row.total_latency_ms)
            acc["latency_count"] += 1

        if result_row.triage_correct is not None:
            acc["triage_total"] += 1
            if result_row.triage_correct:
                acc["triage_correct_count"] += 1

        if result_row.cost_cents is not None:
            acc["cost_sum"] += float(result_row.cost_cents)

        # Build per-case comparison entry
        case_entry = cases_map.get(case.id)
        if case_entry is None:
            case_entry = EvalRunComparisonPerCase(
                test_case_id=case.id,
                case_name=case.name,
                expected_triage_decision=case.expected_triage_decision,
                expected_assessments=case.expected_assessments or None,
                per_run={},
            )
            cases_map[case.id] = case_entry

        case_entry.per_run[run_key] = EvalTestResultResponse.model_validate(result_row)

    # Finalize summaries
    for run in runs:
        acc = per_run_accumulator.get(run.id, {})
        accuracy_count = acc.get("accuracy_count", 0) or 0
        latency_count = acc.get("latency_count", 0) or 0
        triage_total = acc.get("triage_total", 0) or 0

        avg_accuracy = acc.get("accuracy_sum", 0.0) / accuracy_count if accuracy_count > 0 else None
        avg_latency_ms = acc.get("latency_sum", 0.0) / latency_count if latency_count > 0 else None
        triage_accuracy = (
            acc.get("triage_correct_count", 0) / triage_total if triage_total > 0 else None
        )
        total_cost_cents = acc.get("cost_sum", 0.0) if acc else None

        run_summaries[str(run.id)] = EvalBenchmarkRunSummary(
            avg_accuracy=avg_accuracy,
            avg_latency_ms=avg_latency_ms,
            total_cost_cents=total_cost_cents,
            triage_accuracy=triage_accuracy,
            assessment_accuracy=None,
        )

    return EvalRunComparisonResponse(
        run_summaries=run_summaries,
        cases=list(cases_map.values()),
    )


# ---------------------------------------------------------------------------
# Golden dataset
# ---------------------------------------------------------------------------


@router.post("/golden/import", response_model=GoldenImportResponse)
async def import_golden_from_production(
    start_date: datetime | None = Query(
        None,
        description="Only include assessments created at or after this datetime (ISO8601)",
    ),
    end_date: datetime | None = Query(
        None,
        description="Only include assessments created before this datetime (ISO8601)",
    ),
    user_id: UUID | None = Query(None, description="Optional user ID filter"),
    session_id: UUID | None = Query(None, description="Optional session ID filter"),
    session: AsyncSession = Depends(get_session),
) -> GoldenImportResponse:
    """Import production interactions into the golden dataset.

    This endpoint reads existing Assessment / SkillAssessment / TriageLog data
    and creates golden dataset entries with `source = "production"` and
    `status = "pending_review"`. Entries are deduplicated by
    `source_interaction_id`.
    """

    query = (
        select(Assessment, Interaction, Session)
        .join(Session, Assessment.session_id == Session.id)
        .join(Interaction, Assessment.interaction_id == Interaction.id)
    )

    if start_date is not None:
        query = query.where(Assessment.created_at >= start_date)
    if end_date is not None:
        query = query.where(Assessment.created_at <= end_date)
    if user_id is not None:
        query = query.where(Assessment.user_id == user_id)
    if session_id is not None:
        query = query.where(Assessment.session_id == session_id)

    rows = (await session.execute(query)).all()
    if not rows:
        return GoldenImportResponse(imported=0)

    golden_cases: list[GoldenCase] = []

    for assessment, interaction, sess in rows:
        # Load per-skill results with their Skill rows
        sa_result = await session.execute(
            select(SkillAssessment, Skill)
            .join(Skill, SkillAssessment.skill_id == Skill.id)
            .where(SkillAssessment.assessment_id == assessment.id)
        )
        sa_rows = list(sa_result.all())
        skills: list[str] = []
        expected_assessments: list[dict[str, Any]] = []

        for sa, skill in sa_rows:
            skills.append(skill.slug)
            expected_assessments.append(
                {
                    "skill_slug": skill.slug,
                    "expected_level": int(sa.level),
                    "level_tolerance": 1,
                    "expected_keywords": [],
                    "notes": None,
                }
            )

        level_range = None
        if expected_assessments:
            levels = [int(item["expected_level"]) for item in expected_assessments]
            level_range = {"min": min(levels), "max": max(levels)}

        # Prefer transcript over content for speech-based interactions
        transcript = interaction.transcript or interaction.content or ""

        # Use assessment triage_decision when available; fall back to latest triage log
        expected_triage_decision = assessment.triage_decision
        if expected_triage_decision is None:
            triage_result = await session.execute(
                select(TriageLog)
                .where(
                    TriageLog.session_id == sess.id,
                    TriageLog.interaction_id == interaction.id,
                )
                .order_by(TriageLog.created_at.desc())
                .limit(1)
            )
            triage = triage_result.scalar_one_or_none()
            if triage is not None:
                # Map triage decisions into the eval triage labels when possible
                if triage.decision == "assess":
                    expected_triage_decision = "skill_practice"
                elif triage.decision == "skip":
                    expected_triage_decision = "general_chatter"

        metadata: dict[str, Any] = {
            "user_id": str(assessment.user_id),
            "session_id": str(sess.id),
            "interaction_id": str(interaction.id),
            "assessment_id": str(assessment.id),
        }

        raw = {
            "id": str(uuid4()),
            "transcript": transcript,
            "skills": skills,
            "level_range": level_range,
            "scenario": None,
            "expected_triage_decision": expected_triage_decision,
            "expected_assessments": expected_assessments,
            "source": "production",
            "status": "pending_review",
            "source_interaction_id": str(interaction.id),
            "source_session_id": str(sess.id),
            "notes": None,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
            "reviewed_by": None,
            "reviewed_at": None,
        }

        golden_cases.append(GoldenCase.from_dict(raw))

    unique_cases = dedupe_by_source_interaction(golden_cases)
    if not unique_cases:
        return GoldenImportResponse(imported=0)

    upsert_golden_cases(unique_cases)
    return GoldenImportResponse(imported=len(unique_cases))


@router.get("/golden", response_model=GoldenCaseListResponse)
async def list_golden_cases(
    status: str | None = Query(
        None,
        description="Filter by status: pending_review, approved, or rejected.",
    ),
    source: str | None = Query(
        None,
        description="Filter by source (e.g. 'generated' or 'production').",
    ),
    skill: str | None = Query(
        None,
        description="Filter by skill slug present in skills/expected_assessments.",
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> GoldenCaseListResponse:
    """List golden dataset cases with basic filters and pagination."""

    valid_status = {"pending_review", "approved", "rejected"}
    status_filter = status if status in valid_status else None

    cases = filter_golden_cases(status=status_filter, source=source, skill=skill)
    total = len(cases)

    start = (page - 1) * limit
    end = start + limit
    page_items = cases[start:end]

    items = [
        GoldenCaseResponse(
            id=case.id,
            transcript=case.transcript,
            skills=case.skills,
            level_range=case.level_range,
            scenario=case.scenario,
            expected_triage_decision=case.expected_triage_decision,
            expected_assessments=case.expected_assessments,
            source=case.source,
            status=case.status,
            source_interaction_id=case.source_interaction_id,
            source_session_id=case.source_session_id,
            notes=case.notes,
            metadata=case.metadata,
            created_at=case.created_at,
            reviewed_by=case.reviewed_by,
            reviewed_at=case.reviewed_at,
        )
        for case in page_items
    ]

    return GoldenCaseListResponse(items=items, page=page, limit=limit, total=total)


@router.put("/golden/{case_id}", response_model=GoldenCaseResponse)
async def update_golden_case(
    case_id: str,
    payload: GoldenCaseUpdateRequest,
) -> GoldenCaseResponse:
    """Update status and ground truth for a golden dataset case."""

    case = find_golden_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Golden case not found")

    if payload.status is not None:
        valid_status = {"pending_review", "approved", "rejected"}
        if payload.status not in valid_status:
            raise HTTPException(status_code=400, detail="Invalid status value")
        case.status = payload.status  # type: ignore[assignment]
        case.reviewed_at = datetime.utcnow().isoformat()

    if payload.expected_triage_decision is not None:
        case.expected_triage_decision = payload.expected_triage_decision

    if payload.expected_assessments is not None:
        case.expected_assessments = [a.model_dump() for a in payload.expected_assessments]

    if payload.notes is not None:
        case.notes = payload.notes

    upsert_golden_cases([case])

    return GoldenCaseResponse(
        id=case.id,
        transcript=case.transcript,
        skills=case.skills,
        level_range=case.level_range,
        scenario=case.scenario,
        expected_triage_decision=case.expected_triage_decision,
        expected_assessments=case.expected_assessments,
        source=case.source,
        status=case.status,
        source_interaction_id=case.source_interaction_id,
        source_session_id=case.source_session_id,
        notes=case.notes,
        metadata=case.metadata,
        created_at=case.created_at,
        reviewed_by=case.reviewed_by,
        reviewed_at=case.reviewed_at,
    )
