"""Assessment service for evaluating user responses against skills.

Responsibilities:
- Call LLM to evaluate a user's response for one or more skills
- Persist Assessment and SkillAssessment records
- Compute basic latency / token / cost metrics
- Optionally trigger level progression via SkillLevelHistory + UserSkill

This service is used by:
- Chat/Voice services (after triage decides to ASSESS)
- Dev/test HTTP endpoints for assessment
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import LLMMessage, LLMProvider
from app.ai.providers.factory import get_llm_provider
from app.ai.substrate import ProviderCallLogger
from app.infrastructure.pricing import estimate_llm_cost_cents
from app.models import (
    Assessment,
    Skill,
    SkillAssessment,
    SkillLevelHistory,
    TriageLog,
    UserSkill,
)
from app.schemas.assessment import (
    AssessmentMetrics,
    AssessmentResponse,
    LevelChangeEvent,
    SkillAssessmentResponse,
    SkillFeedback,
)

logger = logging.getLogger("assessment")


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    return value


# Single-skill assessment prompt (simpler, more reliable JSON output)
SINGLE_SKILL_SYSTEM_PROMPT = """You are an expert communication coach.
You evaluate how well a user's response demonstrates a specific speaking skill.

You MUST:
- Score the skill on a 0–10 integer scale
- Provide a short summary (1–2 sentences)
- Provide structured feedback: strengths, improvements, example quotes, next steps

IMPORTANT:
- Focus on how the user SPOKE (clarity, structure, examples, fillers), not on
  whether their idea is correct.
- Be kind but honest — identify 1–3 concrete areas to improve.

Output format (STRICT):
Return ONLY a single JSON object:
{
  "skill_id": "<uuid>",
  "level": <int 0-10>,
  "confidence": <float 0-1>,
  "summary": "<short 1-2 sentence summary>",
  "feedback": {
    "primary_takeaway": "<one sentence>",
    "strengths": ["..."],
    "improvements": ["..."],
    "example_quotes": [
      { "quote": "...", "annotation": "...", "type": "strength" | "improvement" }
    ],
    "next_level_criteria": "<what they should focus on for next level>"
  }
}

Do NOT add any extra text before or after the JSON object.
"""

# Legacy multi-skill prompt (kept for reference, but no longer used)
ASSESSMENT_SYSTEM_PROMPT = SINGLE_SKILL_SYSTEM_PROMPT


class AssessmentService:
    """Service for LLM-based skill assessment and progression logic."""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider,
        model_id: str | None = None,
    ):
        """Initialize assessment service.

        Args:
            db: Database session (required)
            llm_provider: LLM provider for assessment (required - no factory fallback)
            model_id: Optional model ID override
        """
        if llm_provider is None:
            raise ValueError("llm_provider is required. Use explicit injection or get_llm_provider() at the call site.")
        self.db = db
        self.llm = llm_provider
        self._default_model_id = model_id or self._get_default_model_id()
        self._provider_call_db_lock = asyncio.Lock()
        self.call_logger = ProviderCallLogger(db, db_lock=self._provider_call_db_lock)

    @staticmethod
    def _get_configured_llm_provider() -> LLMProvider:
        """Get LLM provider configured with the default model choice."""
        from app.config import get_settings

        get_settings()
        provider = get_llm_provider()  # Use default provider
        return provider

    @staticmethod
    def _get_default_model_id() -> str:
        """Get the default model ID based on env configuration."""
        from app.config import get_settings

        settings = get_settings()
        choice = settings.llm_model_choice
        return settings.llm_model1_id if choice == "model1" else settings.llm_model2_id

    async def assess_response(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        interaction_id: UUID | None,
        user_response: str,
        skill_ids: list[UUID],
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        triage_decision: str | None = None,
        request_id: UUID | None = None,
        pipeline_run_id: UUID | None = None,
        _model_id: str | None = None,
    ) -> AssessmentResponse:
        """Run assessment for a set of skills and persist results.

        Args:
            user_id: User ID
            session_id: Session ID
            interaction_id: Interaction that triggered assessment (may be None)
            user_response: The user's spoken/text response to evaluate
            skill_ids: List of skills to assess
            send_status: Optional callback for status events (service, status, metadata)
            triage_decision: Optional triage decision that led to this assessment

        Returns:
            AssessmentResponse with per-skill results and metrics.
        """

        if not skill_ids:
            logger.info(
                "Assessment skipped - no skills provided",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                },
            )
            return AssessmentResponse(
                assessment_id=None,
                session_id=session_id,
                interaction_id=interaction_id,
                triage_decision=triage_decision,
                user_response=user_response,
                skills=[],
                metrics=AssessmentMetrics(
                    triage_latency_ms=None,
                    assessment_latency_ms=0,
                    total_cost_cents=0,
                ),
            )

        start_time = time.time()

        # Determine if this assessment should carry an override label
        triage_override_label = await self._compute_triage_override_label(
            session_id=session_id,
            interaction_id=interaction_id,
            triage_decision=triage_decision,
        )

        # Fetch skills and user progress
        skills_by_id, user_skills_by_id = await self._load_skills_and_progress(
            user_id=user_id,
            skill_ids=skill_ids,
        )

        if send_status:
            await send_status(
                "assessment",
                "started",
                {
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "skill_count": len(skill_ids),
                    "parallel": True,
                },
            )

        # Run parallel per-skill assessments
        assessment_tasks = [
            self._assess_single_skill(
                user_response=user_response,
                skill=skills_by_id[skill_id],
                user_skill=user_skills_by_id.get(skill_id),
                session_id=session_id,
                user_id=user_id,
                request_id=request_id,
            )
            for skill_id in skill_ids
            if skill_id in skills_by_id
        ]

        parallel_results = await asyncio.gather(*assessment_tasks, return_exceptions=True)

        # Collect successful results
        parsed_results: list[dict[str, Any]] = []
        total_tokens = 0
        total_cost = 0
        max_latency = 0
        errors: list[str] = []
        provider_call_ids: dict[UUID, UUID | None] = {}
        metrics_by_skill: dict[UUID, dict[str, Any]] = {}

        for result in parallel_results:
            if isinstance(result, Exception):
                errors.append(str(result))
                continue
            if result is None:
                continue
            parsed = result["parsed"]
            parsed_results.append(parsed)
            skill_id_for_result = parsed["skill_id"]
            provider_call_ids[skill_id_for_result] = result.get("provider_call_id")

            # Aggregate overall metrics
            tokens_for_result = result.get("tokens_used", 0) or 0
            cost_for_result = result.get("cost_cents", 0) or 0
            latency_for_result = result.get("latency_ms", 0) or 0

            total_tokens += tokens_for_result
            total_cost += cost_for_result
            max_latency = max(max_latency, latency_for_result)

            # Store per-skill metrics for constructing SkillAssessmentResponse
            metrics_by_skill[skill_id_for_result] = {
                "latency_ms": latency_for_result or None,
                "tokens_used": tokens_for_result or None,
                "cost_cents": cost_for_result or None,
            }

        assessment_latency_ms = max_latency
        tokens_used = total_tokens
        cost_cents = total_cost

        if errors:
            logger.warning(
                "Some skill assessments failed",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "errors": errors,
                    "successful_count": len(parsed_results),
                },
            )

        if not parsed_results:
            # All assessments failed
            error_msg = "; ".join(errors) if errors else "All skill assessments failed"
            logger.error(
                "All parallel assessments failed",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "errors": errors,
                },
            )
            if send_status:
                await send_status("assessment", "error", {"error": error_msg})
            raise ValueError(error_msg)

        logger.info(
            "Parallel assessment complete",
            extra={
                "service": "assessment",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "skill_count": len(parsed_results),
                "total_tokens": tokens_used,
                "max_latency_ms": assessment_latency_ms,
                "cost_cents": cost_cents,
                "provider": self.llm.name,
            },
        )

        # Persist Assessment + SkillAssessments in a single transaction to
        # avoid multiple sequential commits that can block the event loop.
        assessment = await self._create_assessment_record(
            user_id=user_id,
            session_id=session_id,
            interaction_id=interaction_id,
            triage_decision=triage_decision,
            triage_override_label=triage_override_label,
            pipeline_run_id=pipeline_run_id,
            commit=False,
        )

        skill_responses: list[SkillAssessmentResponse] = []
        level_events: list[LevelChangeEvent] = []

        for item in parsed_results:
            skill_id = item["skill_id"]
            skill = skills_by_id.get(skill_id)
            if not skill:
                # Ignore results for unknown/unexpected skills
                continue

            per_skill_metrics = metrics_by_skill.get(skill_id, {})
            per_skill_latency_ms: int | None = per_skill_metrics.get("latency_ms")
            per_skill_tokens_used: int | None = per_skill_metrics.get("tokens_used")
            per_skill_cost_cents: int | None = per_skill_metrics.get("cost_cents")

            sa_model = await self._create_skill_assessment_record(
                assessment=assessment,
                skill=skill,
                item=item,
                latency_ms=per_skill_latency_ms,
                tokens_used=per_skill_tokens_used,
                cost_cents=per_skill_cost_cents,
                provider_call_id=provider_call_ids.get(skill_id),
                commit=False,
            )

            # Resolve per-skill metrics without triggering lazy loads in async
            # contexts. Prefer the metrics captured from the LLM call, falling
            # back to attributes on the SkillAssessment instance when tests
            # construct in-memory objects without a ProviderCall.
            latency_value: int | None = getattr(sa_model, "latency_ms", None)
            tokens_used_value: int | None = getattr(sa_model, "tokens_used", None)
            cost_cents_value: int | None = getattr(sa_model, "cost_cents", None)
            provider_value: str | None = getattr(sa_model, "provider", None)
            model_value: str | None = getattr(sa_model, "model_id", None)

            if latency_value is None:
                latency_value = per_skill_latency_ms
            if tokens_used_value is None:
                tokens_used_value = per_skill_tokens_used
            if cost_cents_value is None:
                cost_cents_value = per_skill_cost_cents

            skill_responses.append(
                SkillAssessmentResponse(
                    skill_id=sa_model.skill_id,
                    level=sa_model.level,
                    confidence=sa_model.confidence,
                    summary=sa_model.summary,
                    feedback=SkillFeedback(**sa_model.feedback),
                    latency_ms=latency_value,
                    tokens_used=tokens_used_value,
                    cost_cents=cost_cents_value,
                    provider=provider_value,
                    model=model_value,
                )
            )

            event = await self.check_level_progression(
                user_id=user_id,
                skill_id=sa_model.skill_id,
                send_status=send_status,
            )
            if event:
                level_events.append(event)
                if send_status:
                    await send_status(
                        "level",
                        "changed",
                        {
                            "user_id": str(event.user_id),
                            "skill_id": str(event.skill_id),
                            "from_level": event.from_level,
                            "to_level": event.to_level,
                            "reason": event.reason,
                        },
                    )

        total_duration_ms = int((time.time() - start_time) * 1000)

        if send_status:
            await send_status(
                "assessment",
                "complete",
                {
                    "assessment_id": str(assessment.id),
                    "skill_count": len(skill_responses),
                    "latency_ms": assessment_latency_ms,
                    "cost_cents": cost_cents,
                    "duration_ms": total_duration_ms,
                    "provider": self.llm.name,
                },
            )

        # Commit all Assessment / SkillAssessment / level progression changes
        # in a single transaction to minimize event loop blocking.
        await self.db.commit()

        metrics = AssessmentMetrics(
            triage_latency_ms=None,
            assessment_latency_ms=assessment_latency_ms,
            total_cost_cents=cost_cents,
        )

        return AssessmentResponse(
            assessment_id=assessment.id,
            session_id=session_id,
            interaction_id=interaction_id,
            triage_decision=triage_decision,
            triage_override_label=triage_override_label,
            user_response=user_response,
            skills=skill_responses,
            metrics=metrics,
        )

    async def _compute_triage_override_label(
        self,
        *,
        session_id: UUID,
        interaction_id: UUID | None,
        triage_decision: str | None,
    ) -> str | None:
        """Compute override label for general_chatter → manual assess cases.

        Rules (from SPR-006):
        - When triage logged decision='skip' and reason='general_chatter' for an
          interaction.
        - And a subsequent manual assessment is triggered for the same
          interaction (triage_decision == "manual").
        - Then label = 'general_chatter_manual_assess'.
        """

        if triage_decision != "manual" or interaction_id is None:
            return None

        result = await self.db.execute(
            select(TriageLog)
            .where(
                TriageLog.session_id == session_id,
                TriageLog.interaction_id == interaction_id,
                TriageLog.decision == "skip",
                TriageLog.reason == "general_chatter",
            )
            .order_by(TriageLog.created_at.desc())
            .limit(1)
        )
        triage_row = result.scalar_one_or_none()
        if not triage_row:
            return None

        label = "general_chatter_manual_assess"
        logger.info(
            "Triage override detected (general_chatter → manual assess)",
            extra={
                "service": "assessment",
                "session_id": str(session_id),
                "interaction_id": str(interaction_id),
                "triage_override_label": label,
            },
        )
        return label

    async def _load_skills_and_progress(
        self,
        *,
        user_id: UUID,
        skill_ids: list[UUID],
    ) -> tuple[dict[UUID, Skill], dict[UUID, UserSkill]]:
        """Load Skill and UserSkill rows for the given IDs."""

        skills_result = await self.db.execute(select(Skill).where(Skill.id.in_(skill_ids)))
        skills: list[Skill] = list(skills_result.scalars().all())
        skills_by_id = {s.id: s for s in skills}

        user_skills_result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id.in_(skill_ids),
            )
        )
        user_skills: list[UserSkill] = list(user_skills_result.scalars().all())
        user_skills_by_id = {us.skill_id: us for us in user_skills}

        return skills_by_id, user_skills_by_id

    async def _assess_single_skill(
        self,
        *,
        user_response: str,
        skill: Skill,
        user_skill: UserSkill | None,
        session_id: UUID,
        user_id: UUID,
        request_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Assess a single skill in parallel with fallback to backup provider.

        Returns dict with 'parsed', 'tokens_used', 'cost_cents', 'latency_ms'
        or raises an exception on failure (after trying backup if configured).
        """
        from app.config import get_settings

        messages = self._build_single_skill_messages(user_response, skill, user_skill)
        settings = get_settings()

        # Try primary provider first
        primary_error = None
        try:
            result = await self._call_llm_for_skill(
                messages=messages,
                skill=skill,
                session_id=session_id,
                user_id=user_id,
                llm=self.llm,
                provider_name="primary",
                request_id=request_id,
            )
            return result
        except Exception as exc:
            primary_error = exc
            logger.warning(
                "Primary LLM failed for skill assessment, will try backup",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "skill_id": str(skill.id),
                    "skill_slug": skill.slug,
                    "error": str(exc),
                    "backup_provider": settings.assessment_backup_provider,
                },
            )

        # Try backup provider if configured
        backup_provider_name = settings.assessment_backup_provider
        if backup_provider_name and backup_provider_name != self.llm.name:
            try:
                backup_llm = get_llm_provider(backup_provider_name)
                result = await self._call_llm_for_skill(
                    messages=messages,
                    skill=skill,
                    session_id=session_id,
                    user_id=user_id,
                    llm=backup_llm,
                    provider_name=f"backup ({backup_provider_name})",
                    request_id=request_id,
                )
                logger.info(
                    "Backup LLM succeeded for skill assessment",
                    extra={
                        "service": "assessment",
                        "session_id": str(session_id),
                        "skill_id": str(skill.id),
                        "skill_slug": skill.slug,
                        "backup_provider": backup_provider_name,
                    },
                )
                return result
            except Exception as backup_exc:
                logger.error(
                    "Backup LLM also failed for skill assessment",
                    extra={
                        "service": "assessment",
                        "session_id": str(session_id),
                        "user_id": str(user_id),
                        "skill_id": str(skill.id),
                        "skill_slug": skill.slug,
                        "primary_error": str(primary_error),
                        "backup_error": str(backup_exc),
                        "backup_provider": backup_provider_name,
                    },
                )
                # Raise the backup error (more recent)
                raise backup_exc from primary_error

        # No backup configured or backup is same as primary - raise original error
        raise primary_error  # type: ignore[misc]

    async def _call_llm_for_skill(
        self,
        *,
        messages: list[LLMMessage],
        skill: Skill,
        session_id: UUID,
        user_id: UUID,
        llm: LLMProvider,
        provider_name: str,
        request_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Call a specific LLM provider for skill assessment.

        Returns dict with 'parsed', 'tokens_used', 'cost_cents', 'latency_ms'.
        Raises on LLM or parse failure.
        """
        llm_start = time.time()
        model_to_use = (
            self._default_model_id if getattr(llm, "name", "").lower() == "groq" else None
        )
        prompt_payload = [{"role": m.role, "content": m.content} for m in messages]

        try:
            response, call_row = await self.call_logger.call_llm_generate(
                service="assessment",
                provider=llm.name,
                model_id=model_to_use,
                prompt_messages=prompt_payload,
                call=lambda: llm.generate(
                    messages,
                    model=model_to_use,
                    max_tokens=400,
                    temperature=0.3,
                ),
                session_id=session_id,
                user_id=user_id,
                interaction_id=None,
                request_id=request_id,
            )
            latency_ms = call_row.latency_ms or int((time.time() - llm_start) * 1000)
        except Exception as exc:
            logger.error(
                f"LLM call failed ({provider_name})",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "skill_id": str(skill.id),
                    "provider": provider_name,
                    "error": str(exc),
                },
            )
            raise

        try:
            parsed = self._parse_single_result(response.content, skill.id)
        except Exception as exc:
            logger.error(
                f"Failed to parse skill assessment ({provider_name})",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "skill_id": str(skill.id),
                    "provider": provider_name,
                    "raw_response": response.content[:500],
                    "error": str(exc),
                },
            )
            raise

        tokens_used = response.tokens_in + response.tokens_out
        # Cost estimate: Groq ~$2.7/1M tokens, Gemini Flash ~$0.075/1M tokens
        cost_cents = estimate_llm_cost_cents(
            provider=llm.name,
            model=response.model,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )

        logger.debug(
            "Single skill assessment complete",
            extra={
                "service": "assessment",
                "skill_id": str(skill.id),
                "skill_slug": skill.slug,
                "level": parsed.get("level"),
                "latency_ms": latency_ms,
                "provider": provider_name,
            },
        )

        await self.call_logger.update_provider_call(
            call_row,
            output_parsed=_json_safe(parsed),
            cost_cents=cost_cents,
        )

        return {
            "parsed": parsed,
            "tokens_used": tokens_used,
            "cost_cents": cost_cents,
            "latency_ms": latency_ms,
            "provider_call_id": call_row.id,
        }

    def _build_single_skill_messages(
        self,
        user_response: str,
        skill: Skill,
        user_skill: UserSkill | None,
    ) -> list[LLMMessage]:
        """Build LLM messages for single-skill assessment."""
        current_level = user_skill.current_level if user_skill else 0

        skill_json = json.dumps(
            {
                "skill_id": str(skill.id),
                "slug": skill.slug,
                "title": skill.title,
                "current_level": current_level,
                "levels": skill.levels,
            },
            ensure_ascii=False,
        )

        user_prompt = (
            f"Assess the user's response for this skill:\n\n"
            f"User response:\n{user_response}\n\n"
            f"Skill (JSON):\n{skill_json}\n\n"
            "Return a single JSON object as specified in the system prompt."
        )

        return [
            LLMMessage(role="system", content=SINGLE_SKILL_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

    @staticmethod
    def _parse_single_result(raw: str, expected_skill_id: UUID) -> dict[str, Any]:
        """Parse single-skill LLM JSON assessment result."""
        text = raw.strip()

        # Strip markdown code fences if present
        if "```" in text:
            fence_start = text.find("```")
            fence_end = text.rfind("```")
            inner = (
                text[fence_start + 3 : fence_end]
                if fence_end > fence_start
                else text[fence_start + 3 :]
            )
            inner = inner.lstrip()
            if inner.lower().startswith("json"):
                inner = inner[4:].lstrip()
            text = inner

        # Extract JSON object
        if "{" in text and "}" in text:
            start = text.index("{")
            end = text.rfind("}") + 1
            text = text[start:end]

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Single skill assessment must be a JSON object")

        # Validate skill_id matches
        skill_id_raw = data.get("skill_id")
        try:
            UUID(str(skill_id_raw))
        except Exception:
            # Use the expected skill_id if parsing fails
            skill_id_raw = str(expected_skill_id)

        level = int(data.get("level", 0))
        level = max(0, min(10, level))

        confidence_raw = data.get("confidence")
        confidence = None
        if confidence_raw is not None:
            try:
                confidence = float(confidence_raw)
                confidence = max(0.0, min(1.0, confidence))
            except Exception:
                confidence = None

        summary = data.get("summary") or None
        feedback = data.get("feedback") or {}

        return {
            "skill_id": expected_skill_id,  # Always use expected ID for safety
            "level": level,
            "confidence": confidence,
            "summary": summary,
            "feedback": feedback,
        }

    def _build_messages(
        self,
        user_response: str,
        skills_by_id: dict[UUID, Skill],
        user_skills_by_id: dict[UUID, UserSkill],
    ) -> list[LLMMessage]:
        """Build LLM messages for assessment prompt.

        Encodes skill rubric context and user progress into a compact JSON
        structure, then asks the model to return a JSON array of assessments.
        """

        skill_payload: list[dict[str, Any]] = []
        for skill_id, skill in skills_by_id.items():
            user_skill = user_skills_by_id.get(skill_id)
            current_level = user_skill.current_level if user_skill else 0

            skill_payload.append(
                {
                    "skill_id": str(skill.id),
                    "slug": skill.slug,
                    "title": skill.title,
                    "current_level": current_level,
                    "levels": skill.levels,
                }
            )

        context_json = json.dumps(skill_payload, ensure_ascii=False)

        user_prompt = (
            "You will assess the user's response for the following skills.\n\n"
            f"User response:\n{user_response}\n\n"
            "Skills (JSON):\n"
            f"{context_json}\n\n"
            "Return a JSON array as specified in the system prompt, containing one"
            " object per skill in the same order they appear in the Skills JSON."
        )

        return [
            LLMMessage(role="system", content=ASSESSMENT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

    @staticmethod
    def _parse_results(raw: str, expected_skill_ids: list[UUID]) -> list[dict[str, Any]]:
        """Parse LLM JSON assessment results.

        Returns list of dicts with keys matching the expected output schema.
        Filters out any skills not in expected_skill_ids.
        """

        text = raw.strip()
        if "```" in text:
            fence_start = text.find("```")
            fence_end = text.rfind("```")
            inner = (
                text[fence_start + 3 : fence_end]
                if fence_end > fence_start
                else text[fence_start + 3 :]
            )
            inner = inner.lstrip()
            if inner.lower().startswith("json"):
                inner = inner[4:].lstrip()
            text = inner

        if "[" in text and "]" in text:
            start = text.index("[")
            end = text.rfind("]") + 1
            text = text[start:end]

        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("Assessment response JSON must be an array")

        expected_set = set(expected_skill_ids)
        results: list[dict[str, Any]] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            skill_id_raw = item.get("skill_id")
            try:
                skill_id = UUID(str(skill_id_raw))
            except Exception:
                continue

            if skill_id not in expected_set:
                continue

            level = int(item.get("level", 0))
            level = max(0, min(10, level))
            confidence_raw = item.get("confidence")
            confidence = None
            if confidence_raw is not None:
                try:
                    confidence = float(confidence_raw)
                    confidence = max(0.0, min(1.0, confidence))
                except Exception:  # pragma: no cover - defensive
                    confidence = None

            summary = item.get("summary") or None
            feedback = item.get("feedback") or {}

            results.append(
                {
                    "skill_id": skill_id,
                    "level": level,
                    "confidence": confidence,
                    "summary": summary,
                    "feedback": feedback,
                }
            )

        return results

    async def _create_assessment_record(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        interaction_id: UUID | None,
        triage_decision: str | None,
        triage_override_label: str | None = None,
        pipeline_run_id: UUID | None = None,
        commit: bool = True,
    ) -> Assessment:
        """Create and persist an Assessment group record."""

        assessment = Assessment(
            user_id=user_id,
            session_id=session_id,
            interaction_id=interaction_id,
            pipeline_run_id=pipeline_run_id,
            group_id=uuid4(),
            triage_decision=triage_decision,
            triage_override_label=triage_override_label,
        )
        self.db.add(assessment)
        if commit:
            await self.db.commit()
            await self.db.refresh(assessment)
        else:
            # Flush so that primary key fields are populated without
            # committing the transaction yet.
            await self.db.flush()

        logger.debug(
            "Assessment record created",
            extra={
                "service": "assessment",
                "assessment_id": str(assessment.id),
                "session_id": str(session_id),
                "user_id": str(user_id),
            },
        )

        return assessment

    async def _create_skill_assessment_record(
        self,
        *,
        assessment: Assessment,
        skill: Skill,
        item: dict[str, Any],
        latency_ms: int | None,
        tokens_used: int | None,
        cost_cents: int | None,
        provider_call_id: UUID | None,
        commit: bool = True,
    ) -> SkillAssessment:
        """Create and persist a SkillAssessment row."""

        sa_model = SkillAssessment(
            assessment_id=assessment.id,
            skill_id=skill.id,
            level=item["level"],
            confidence=item["confidence"],
            summary=item["summary"],
            feedback=item["feedback"],
            provider=self.llm.name,
            model_id=self._default_model_id,
            tokens_used=tokens_used,
            cost_cents=cost_cents,
            latency_ms=latency_ms,
            provider_call_id=provider_call_id,
        )
        self.db.add(sa_model)
        if commit:
            await self.db.commit()
            await self.db.refresh(sa_model)
        else:
            # Flush so that generated fields (e.g. primary key) are
            # available without committing yet.
            await self.db.flush()

        logger.debug(
            "Skill assessment record created",
            extra={
                "service": "assessment",
                "assessment_id": str(assessment.id),
                "skill_id": str(skill.id),
                "level": sa_model.level,
                "provider_call_id": str(sa_model.provider_call_id)
                if sa_model.provider_call_id
                else None,
            },
        )

        return sa_model

    async def check_level_progression(
        self,
        *,
        user_id: UUID,
        skill_id: UUID,
        history_window: int = 5,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
    ) -> LevelChangeEvent | None:
        """Check if user should level up for a skill based on recent assessments.

        Rules (from SPR-004):
        - Look at last N assessments (N=5) for this user+skill
        - Calculate average score
        - If average >= threshold for next level → level up

        Thresholds (simple):
        - Level 0-2: avg >= 3 → level 3
        - Level 3-4: avg >= 5 → level 5
        - Level 5-6: avg >= 7 → level 7
        - Level 7-8: avg >= 9 → level 9
        - Level 9:   avg >= 10 (3 times) → level 10
        """

        # Get UserSkill row
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill_id,
            )
        )
        user_skill = result.scalar_one_or_none()
        if not user_skill:
            return None

        current_level = user_skill.current_level

        # Fetch last N SkillAssessment scores for this user+skill
        sa_result = await self.db.execute(
            select(SkillAssessment)
            .join(Assessment, SkillAssessment.assessment_id == Assessment.id)
            .where(
                Assessment.user_id == user_id,
                SkillAssessment.skill_id == skill_id,
            )
            .order_by(SkillAssessment.created_at.desc())
            .limit(history_window)
        )
        recent = list(sa_result.scalars().all())
        if not recent:
            return None

        scores = [sa.level for sa in recent]
        avg_score = sum(scores) / len(scores)

        new_level = current_level

        # Require at least ``history_window`` assessments before considering a level up
        if len(scores) < history_window:
            will_level_up = False
            if send_status:
                with contextlib.suppress(Exception):
                    await send_status(
                        "level",
                        "checked",
                        {
                            "user_id": str(user_id),
                            "skill_id": str(skill_id),
                            "history_window": history_window,
                            "current_level": current_level,
                            "scores": scores,
                            "avg_score": avg_score,
                            "new_level": new_level,
                            "will_level_up": will_level_up,
                        },
                    )
            return None

        if current_level <= 2 and avg_score >= 3:
            new_level = max(new_level, 3)
        elif 3 <= current_level <= 4 and avg_score >= 5:
            new_level = max(new_level, 5)
        elif 5 <= current_level <= 6 and avg_score >= 7:
            new_level = max(new_level, 7)
        elif 7 <= current_level <= 8 and avg_score >= 9:
            new_level = max(new_level, 9)
        elif current_level == 9:
            # Level 10 requires at least 3 assessments with level 10
            tens = sum(1 for s in scores if s == 10)
            if tens >= 3:
                new_level = 10

        will_level_up = new_level > current_level

        if send_status:
            with contextlib.suppress(Exception):
                await send_status(
                    "level",
                    "checked",
                    {
                        "user_id": str(user_id),
                        "skill_id": str(skill_id),
                        "history_window": history_window,
                        "current_level": current_level,
                        "scores": scores,
                        "avg_score": avg_score,
                        "new_level": new_level,
                        "will_level_up": will_level_up,
                    },
                )

        if not will_level_up:
            return None

        # Apply level up without committing here; callers should batch
        # commits to avoid event loop blocking from many small transactions.
        old_level = current_level
        user_skill.current_level = new_level

        # Commit the UserSkill update first
        await self.db.commit()

        history = SkillLevelHistory(
            user_id=user_id,
            skill_id=skill_id,
            from_level=old_level,
            to_level=new_level,
            reason="avg_threshold",
        )
        self.db.add(history)
        # Flush so defaults (e.g. created_at) are populated without forcing
        # a transaction boundary here.
        await self.db.flush()

        # Commit the history transaction and refresh to get database defaults
        await self.db.commit()
        await self.db.refresh(history)

        logger.info(
            "Skill level updated",
            extra={
                "service": "assessment",
                "user_id": str(user_id),
                "skill_id": str(skill_id),
                "from_level": old_level,
                "to_level": new_level,
                "avg_score": avg_score,
            },
        )

        return LevelChangeEvent(
            user_id=user_id,
            skill_id=skill_id,
            from_level=old_level,
            to_level=new_level,
            reason=history.reason,
            source_assessment_id=None,
            created_at=datetime.now(UTC),
        )
