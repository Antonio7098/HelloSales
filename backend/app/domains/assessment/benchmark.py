"""Benchmark runner service for EVL-003.

Executes eval test suites against the existing triage/assessment stack
and records results in the eval_* tables.

This is intentionally minimal to satisfy EVL-003 core goals; it can be
extended later with richer scoring and model/config options.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.factory import get_llm_provider
from app.database import get_session_context
from app.domains.assessment.service import AssessmentService
from app.domains.assessment.triage import TriageService
from app.models import (
    EvalBenchmarkRun,
    EvalTestCase,
    EvalTestResult,
    Session,
    Skill,
    User,
)
from app.schemas.assessment import TriageDecision, TriageRequest

logger = logging.getLogger("benchmark")


@dataclass
class BenchmarkRunnerConfig:
    model_id: str
    prompt_version: str | None = None
    temperature: float | None = None
    extra: dict[str, Any] | None = None


def compute_level_accuracy(expected_level: int, actual_level: int) -> float:
    """Compute per-skill accuracy on a 0.0–1.0 scale based on level distance.

    Formula: 1.0 - |expected - actual| / 10, clipped to [0.0, 1.0].
    """

    diff = abs(int(expected_level) - int(actual_level))
    value = 1.0 - diff / 10.0
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


class BenchmarkRunner:
    """Execute a single benchmark run over all test cases in its suite."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, run_id: UUID) -> None:
        """Execute the benchmark run.

        This implementation is intentionally conservative but "real":

        - Loads the EvalBenchmarkRun and its test cases
        - Creates or reuses a synthetic benchmark user + session
        - Runs triage on each test case transcript
        - Optionally runs assessment for tracked skills when triage/ground-truth
          indicate skill practice
        - Computes simple accuracy metrics against ground truth:
          * triage correctness vs expected_triage_decision (skill_practice/general_chatter)
          * per-skill level accuracy using
            1.0 - abs(expected_level - actual_level) / 10
        - Persists an EvalTestResult row per case
        - Updates the run summary with aggregate metrics used by the
          comparison endpoint (avg accuracy, latency, cost, triage accuracy).
        """
        # Use a fresh DB session for the actual work to avoid depending on
        # request-scoped session lifetime.
        async with get_session_context() as db:
            run_result = await db.execute(
                select(EvalBenchmarkRun).where(EvalBenchmarkRun.id == run_id)
            )
            run = run_result.scalar_one_or_none()
            if run is None:
                return

            run.status = "running"
            run.started_at = datetime.utcnow()
            await db.flush()

            if run.suite_id is None:
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                run.summary = {"error": "suite_id_missing", "num_cases": 0}
                await db.flush()
                return

            case_result = await db.execute(
                select(EvalTestCase).where(EvalTestCase.suite_id == run.suite_id)
            )
            cases = list(case_result.scalars().all())

            if not cases:
                run.status = "complete"
                run.completed_at = datetime.utcnow()
                run.summary = {"num_cases": 0}
                await db.flush()
                return

            # Ensure we have a synthetic benchmark user and session.
            benchmark_subject = "eval-benchmark-user"
            user_result = await db.execute(
                select(User).where(
                    User.auth_provider == "clerk",
                    User.auth_subject == benchmark_subject,
                )
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                user = User(
                    auth_provider="clerk",
                    auth_subject=benchmark_subject,
                    clerk_id=benchmark_subject,
                    email=None,
                    display_name="Eval Benchmark User",
                )
                db.add(user)
                await db.flush()
                await db.refresh(user)

            session_obj = Session(user_id=user.id)
            db.add(session_obj)
            await db.flush()
            await db.refresh(session_obj)

            extra = run.config.get("extra") if isinstance(run.config, dict) else None
            if not isinstance(extra, dict):
                extra = {}

            triage_system_prompt = extra.get("triage_system_prompt")
            triage_model_id = extra.get("triage_model_id")
            triage_context_n = extra.get("triage_context_n", 4)
            try:
                triage_context_n = int(triage_context_n)
            except Exception:
                logger.error(f"Invalid triage_context_n value: {triage_context_n}, using default", exc_info=True)
                triage_context_n = 4
            if triage_context_n < 0:
                triage_context_n = 0
            if triage_context_n > 50:
                triage_context_n = 50

            llm_provider = get_llm_provider()
            triage_service = TriageService(
                db,
                llm_provider=llm_provider,
                model_id=triage_model_id if isinstance(triage_model_id, str) else None,
                system_prompt=triage_system_prompt
                if isinstance(triage_system_prompt, str)
                else None,
            )
            assessment_service = AssessmentService(db, llm_provider=get_llm_provider())

            # Aggregates for summary
            accuracy_sum = 0.0
            accuracy_count = 0
            latency_sum = 0.0
            latency_count = 0
            triage_correct_count = 0
            triage_total = 0
            total_cost_cents = 0.0

            for case in cases:
                request_id = uuid4()
                actual_triage_decision: str | None = None
                triage_correct: bool | None = None
                triage_latency_ms: int | None = None
                actual_assessments: list[dict[str, Any]] | None = None
                assessment_scores: list[dict[str, Any]] | None = None
                overall_accuracy: float | None = None
                total_latency_ms: int | None = None
                cost_cents: float | None = None
                raw_response: dict[str, Any] = {}
                error_text: str | None = None

                # ---------------- Triage ----------------
                triage_response = None
                try:
                    context: list[dict[str, Any]] = []
                    if isinstance(case.metadata_json, dict):
                        raw_ctx = case.metadata_json.get("triage_context_messages")
                        if isinstance(raw_ctx, list):
                            context = [x for x in raw_ctx if isinstance(x, dict)]

                    if not context and triage_context_n > 0:
                        # Fall back to building context from transcript slice when metadata isn't present.
                        context = []

                    context_slice = context[-triage_context_n:] if triage_context_n > 0 else []

                    triage_request = TriageRequest(
                        session_id=session_obj.id,
                        user_response=case.transcript,
                        context=[
                            {
                                "role": ("user" if m.get("role") == "user" else "assistant"),
                                "content": str(m.get("content") or ""),
                            }
                            for m in context_slice
                        ],
                    )
                    triage_response = await triage_service.classify_response(
                        triage_request,
                        interaction_id=None,
                        send_status=None,
                        request_id=request_id,
                        _model_id=(triage_model_id if isinstance(triage_model_id, str) else None),
                    )
                    triage_latency_ms = triage_response.latency_ms
                    # Map assess/skip → skill_practice/general_chatter
                    if triage_response.decision == TriageDecision.ASSESS:
                        actual_triage_decision = "skill_practice"
                    else:
                        actual_triage_decision = "general_chatter"

                    if case.expected_triage_decision:
                        triage_total += 1
                        triage_correct = actual_triage_decision == case.expected_triage_decision
                        if triage_correct:
                            triage_correct_count += 1

                    # Rough cost estimate (same heuristic as services)
                    if triage_response.cost_cents is not None:
                        cost_cents = float(triage_response.cost_cents)
                        total_cost_cents += cost_cents
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error(f"Triage failed: {exc}", exc_info=True)
                    error_text = f"triage_error: {exc}"

                # ---------------- Assessment ----------------
                # Decide whether to run assessment:
                should_assess = False
                if error_text is None and (
                    case.expected_triage_decision == "skill_practice"
                    or actual_triage_decision == "skill_practice"
                ):
                    should_assess = True

                assessment_response = None
                if should_assess and case.tracked_skills:
                    # Load skills by slug
                    skills_result = await db.execute(
                        select(Skill).where(Skill.slug.in_(case.tracked_skills))
                    )
                    skills = list(skills_result.scalars().all())
                    skills_by_id = {s.id: s for s in skills}

                    if skills:
                        try:
                            assessment_response = await assessment_service.assess_response(
                                user_id=user.id,
                                session_id=session_obj.id,
                                interaction_id=None,
                                user_response=case.transcript,
                                skill_ids=[s.id for s in skills],
                                send_status=None,
                                triage_decision=actual_triage_decision,
                                request_id=request_id,
                            )

                            metrics = assessment_response.metrics
                            if metrics and metrics.assessment_latency_ms is not None:
                                total_latency_ms = (
                                    triage_latency_ms or 0
                                ) + metrics.assessment_latency_ms
                            else:
                                total_latency_ms = triage_latency_ms

                            if metrics and metrics.total_cost_cents is not None:
                                if cost_cents is None:
                                    cost_cents = 0.0
                                cost_cents += float(metrics.total_cost_cents)
                                total_cost_cents += float(metrics.total_cost_cents)

                            # Normalise expected assessments as a list of dicts keyed by slug
                            expected_raw = case.expected_assessments or []
                            if isinstance(expected_raw, dict):
                                expected_list = [expected_raw]
                            elif isinstance(expected_raw, list):
                                expected_list = list(expected_raw)
                            else:
                                expected_list = []

                            expected_by_slug: dict[str, dict[str, Any]] = {}
                            for item in expected_list:
                                slug = item.get("skill_slug") if isinstance(item, dict) else None
                                if slug:
                                    expected_by_slug[slug] = item

                            actual_assessments = []
                            assessment_scores = []
                            accuracy_components: list[float] = []

                            for skill_result in assessment_response.skills:
                                skill_model = skills_by_id.get(skill_result.skill_id)
                                slug = skill_model.slug if skill_model else None

                                actual_assessments.append(
                                    {
                                        "skill_id": str(skill_result.skill_id),
                                        "skill_slug": slug,
                                        "level": skill_result.level,
                                        "confidence": skill_result.confidence,
                                        "summary": skill_result.summary,
                                        "feedback": skill_result.feedback.model_dump(),
                                    }
                                )

                                if slug and slug in expected_by_slug:
                                    expected = expected_by_slug[slug]
                                    expected_level = int(expected.get("expected_level", 0))
                                    tolerance = int(expected.get("level_tolerance", 1) or 0)
                                    level_correct = skill_result.level == expected_level
                                    within_tolerance = (
                                        abs(skill_result.level - expected_level) <= tolerance
                                    )

                                    expected_keywords = expected.get("expected_keywords") or []
                                    matched_keywords: list[str] = []
                                    if isinstance(expected_keywords, list) and expected_keywords:
                                        feedback_text_parts = [
                                            skill_result.summary or "",
                                            skill_result.feedback.primary_takeaway,
                                            *skill_result.feedback.strengths,
                                            *skill_result.feedback.improvements,
                                        ]
                                        feedback_text = " ".join(feedback_text_parts).lower()
                                        matched_keywords = [
                                            kw
                                            for kw in expected_keywords
                                            if isinstance(kw, str) and kw.lower() in feedback_text
                                        ]

                                    assessment_scores.append(
                                        {
                                            "skill_slug": slug,
                                            "level_correct": level_correct,
                                            "within_tolerance": within_tolerance,
                                            "keyword_matches": matched_keywords,
                                        }
                                    )

                                    # Per-skill accuracy component
                                    component = compute_level_accuracy(
                                        expected_level, skill_result.level
                                    )
                                    accuracy_components.append(component)

                            # Include triage as an accuracy component if available
                            if triage_correct is not None:
                                accuracy_components.append(1.0 if triage_correct else 0.0)

                            if accuracy_components:
                                overall_accuracy = sum(accuracy_components) / len(
                                    accuracy_components
                                )
                        except Exception as exc:  # pragma: no cover - defensive
                            logger.error(f"Assessment failed: {exc}", exc_info=True)
                            if error_text:
                                error_text += f"; assessment_error: {exc}"
                            else:
                                error_text = f"assessment_error: {exc}"

                # Fallbacks when assessment was skipped but triage still gives signal
                if total_latency_ms is None:
                    total_latency_ms = triage_latency_ms

                if overall_accuracy is None and triage_correct is not None:
                    overall_accuracy = 1.0 if triage_correct else 0.0

                # Aggregate metrics for run summary
                if overall_accuracy is not None:
                    accuracy_sum += overall_accuracy
                    accuracy_count += 1

                if total_latency_ms is not None:
                    latency_sum += float(total_latency_ms)
                    latency_count += 1

                if cost_cents is not None:
                    # Already added into total_cost_cents above
                    pass

                # Prepare raw_response snapshot for debugging
                if triage_response is not None:
                    raw_response["triage"] = triage_response.model_dump()
                if assessment_response is not None:
                    raw_response["assessment"] = assessment_response.model_dump()
                raw_response["request_id"] = str(request_id)

                result = EvalTestResult(
                    run_id=run.id,
                    test_case_id=case.id,
                    actual_triage_decision=actual_triage_decision,
                    triage_correct=triage_correct,
                    triage_latency_ms=triage_latency_ms,
                    actual_assessments=actual_assessments,
                    assessment_scores=assessment_scores,
                    overall_accuracy=overall_accuracy,
                    total_latency_ms=total_latency_ms,
                    tokens_in=None,
                    tokens_out=None,
                    cost_cents=cost_cents,
                    raw_response=raw_response or None,
                    error=error_text,
                    created_at=datetime.utcnow(),
                )
                db.add(result)

            # Finalise run summary
            avg_accuracy = accuracy_sum / accuracy_count if accuracy_count > 0 else None

            avg_latency_ms = latency_sum / latency_count if latency_count > 0 else None

            triage_accuracy = triage_correct_count / triage_total if triage_total > 0 else None

            run.status = "complete"
            run.completed_at = datetime.utcnow()
            run.summary = {
                "num_cases": len(cases),
                "avg_accuracy": avg_accuracy,
                "avg_latency_ms": avg_latency_ms,
                "total_cost_cents": total_cost_cents,
                "triage_accuracy": triage_accuracy,
            }
            await db.flush()
