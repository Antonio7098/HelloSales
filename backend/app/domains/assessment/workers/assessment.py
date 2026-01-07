"""Assessment worker for evaluating user responses against skills.

This worker runs in the parallel phase alongside the agent to assess
how well the user's response demonstrates specific speaking skills.
"""
from __future__ import annotations

from contextlib import suppress
from uuid import UUID

from app.ai.providers.factory import get_llm_provider
from app.ai.substrate.agent.context_snapshot import ContextSnapshot
from app.ai.substrate.protocols.worker import WorkerResult
from app.ai.substrate.stages import register_worker
from app.database import get_session_factory
from app.domains.assessment.service import AssessmentService


@register_worker(name="assessment", description="Evaluates user responses against speaking skills")
class AssessmentWorker:
    """Worker that assesses user responses against speaking skills.

    This worker uses LLM-based evaluation to score how well the user's
    response demonstrates specific speaking skills (clarity, structure, etc.).

    Runs in the parallel phase alongside the agent so assessment doesn't
    block the response.
    """

    id = "worker.assessment"

    def __init__(self, llm_provider_name: str | None = None) -> None:
        """Initialize the assessment worker.

        Args:
            llm_provider_name: Optional LLM provider name override
        """
        self._llm_provider_name = llm_provider_name

    async def process(self, snapshot: ContextSnapshot) -> WorkerResult:
        """Process the context snapshot and assess user response.

        Args:
            snapshot: The context snapshot containing messages and user input

        Returns:
            WorkerResult with assessment results in data
        """
        user_input = snapshot.input_text
        if not user_input:
            return WorkerResult(
                data={
                    "assessment_skipped": True,
                    "assessment_reason": "no_input",
                }
            )

        session_id = snapshot.session_id
        user_id = snapshot.user_id
        if session_id is None or user_id is None:
            return WorkerResult(
                data={
                    "assessment_skipped": True,
                    "assessment_reason": "missing_session_or_user",
                }
            )

        skill_ids = self._get_skill_ids(snapshot)
        if not skill_ids:
            return WorkerResult(
                data={
                    "assessment_skipped": True,
                    "assessment_reason": "no_skills",
                }
            )

        skip_assessment = snapshot.assessment_state.get("skip_assessment", False)
        if skip_assessment:
            return WorkerResult(
                data={
                    "assessment_skipped": True,
                    "assessment_reason": "triage_skipped",
                }
            )

        session_factory = get_session_factory()
        async with session_factory() as db:
            llm_provider = get_llm_provider(self._llm_provider_name) if self._llm_provider_name else get_llm_provider()
            assessment_service = AssessmentService(db, llm_provider=llm_provider)

            try:
                assessment_response = await assessment_service.assess_response(
                    user_id=user_id,
                    session_id=session_id,
                    interaction_id=snapshot.interaction_id,
                    user_response=user_input,
                    skill_ids=skill_ids,
                    request_id=snapshot.request_id,
                    pipeline_run_id=snapshot.pipeline_run_id,
                )

                return WorkerResult(
                    data={
                        "assessment_skipped": False,
                        "assessment_id": str(assessment_response.assessment_id) if assessment_response.assessment_id else None,
                        "assessment_skills": [
                            {
                                "skill_id": str(s.skill_id),
                                "level": s.level,
                                "confidence": s.confidence,
                                "summary": s.summary,
                            }
                            for s in assessment_response.skills
                        ],
                        "assessment_metrics": {
                            "latency_ms": assessment_response.metrics.assessment_latency_ms if assessment_response.metrics else None,
                            "total_cost_cents": assessment_response.metrics.total_cost_cents if assessment_response.metrics else None,
                        },
                    }
                )
            except Exception as exc:
                return WorkerResult(
                    data={
                        "assessment_skipped": True,
                        "assessment_reason": f"error: {str(exc)}",
                    }
                )

    def _get_skill_ids(self, snapshot: ContextSnapshot) -> list[UUID]:
        """Extract skill IDs from the snapshot.

        Args:
            snapshot: The context snapshot

        Returns:
            List of skill UUIDs to assess
        """
        skill_ids: list[UUID] = []

        skills_enrichment = snapshot.skills
        if skills_enrichment:
            for skill_id_str in skills_enrichment.active_skill_ids:
                with suppress(ValueError):
                    skill_ids.append(UUID(skill_id_str))

        assessment_skills = snapshot.assessment_state.get("skill_ids", [])
        for skill_id_str in assessment_skills:
            with suppress(ValueError):
                skill_ids.append(UUID(skill_id_str))

        return list(set(skill_ids))


__all__ = ["AssessmentWorker"]
