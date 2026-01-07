"""Assessment pipeline helpers for chat and voice flows.

Provides both background (non-blocking) and foreground (blocking) modes
for running triage + assessment based on pipeline_mode setting.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.factory import get_llm_provider
from app.api.ws.manager import ConnectionManager
from app.config import get_settings
from app.database import get_session_context
from app.domains.assessment.service import AssessmentService
from app.domains.assessment.triage import TriageService
from app.domains.skills.service import SkillService
from app.models import Interaction
from app.models.assessment import Assessment, TriageLog
from app.models.observability import ProviderCall
from app.schemas.assessment import (
    AssessmentResponse,
    ChatMessage,
    ChatRole,
    TriageDecision,
    TriageRequest,
)

logger = logging.getLogger("assessment")


@dataclass
class ForegroundAssessmentResult:
    """Result from foreground triage + assessment.

    Used in accurate/accurate_filler modes to pass assessment data
    to LLM context building.
    """

    skipped: bool
    skip_reason: str | None = None
    assessment_response: AssessmentResponse | None = None
    interaction_id: UUID | None = None


async def backfill_interaction_id(
    db: AsyncSession,
    session_id: UUID,
    interaction_id: UUID,
) -> None:
    """Backfill interaction_id on assessment records created without it.

    Called after the interaction is committed to link orphaned triage_logs,
    assessments, and provider_calls to the interaction.
    """
    # Update triage_logs
    await db.execute(
        update(TriageLog)
        .where(
            TriageLog.session_id == session_id,
            TriageLog.interaction_id.is_(None),
        )
        .values(interaction_id=interaction_id)
    )

    # Update assessments
    await db.execute(
        update(Assessment)
        .where(
            Assessment.session_id == session_id,
            Assessment.interaction_id.is_(None),
        )
        .values(interaction_id=interaction_id)
    )

    # Update provider_calls (triage/assessment service calls)
    await db.execute(
        update(ProviderCall)
        .where(
            ProviderCall.session_id == session_id,
            ProviderCall.interaction_id.is_(None),
            ProviderCall.service.in_(["triage", "assessment"]),
        )
        .values(interaction_id=interaction_id)
    )

    logger.debug(
        "Backfilled interaction_id on assessment records",
        extra={
            "service": "assessment",
            "session_id": str(session_id),
            "interaction_id": str(interaction_id),
        },
    )


async def run_assessment_background(
    *,
    manager: ConnectionManager,
    websocket: WebSocket,
    session_id: UUID,
    user_id: UUID,
    user_message: str,
    raw_skill_ids: list[UUID] | None,
    send_status: Callable[[str, str, dict[str, Any] | None], Any] | None,
    model_id: str | None = None,
    interaction_id: UUID | None = None,
    client_interaction_id: UUID | None = None,
) -> None:
    """Run triage + assessment for a user message in the background.

    This is used by both chat and voice WebSocket handlers.

    Args:
        interaction_id: If provided, use this ID for linking records.
                        If None, records are created without interaction_id
                        and should be backfilled later via backfill_interaction_id().
        client_interaction_id: Optional ID to report to client in WebSocket messages
                               even if interaction_id is None (for uncommitted rows).
    """
    logger.warning(
        "ENTERED run_assessment_background",
        extra={"service": "assessment", "session_id": str(session_id)},
    )

    # Use client_interaction_id for reporting if available, otherwise fallback to interaction_id
    report_id = client_interaction_id or interaction_id

    settings = get_settings()
    # Clear cache to ensure we get latest test environment
    get_settings.cache_clear()
    settings = get_settings()

    if not settings.assessment_enabled:
        logger.debug("Assessment disabled, skipping", extra={"service": "assessment"})
        return

    logger.info(
        "Starting background assessment",
        extra={
            "service": "assessment",
            "session_id": str(session_id),
            "user_id": str(user_id),
            "interaction_id": str(interaction_id) if interaction_id else None,
            "client_interaction_id": str(client_interaction_id) if client_interaction_id else None,
            "beta_mode_enabled": settings.beta_mode_enabled,
        },
    )

    # Emit assessment.started status event for test compatibility
    if send_status and callable(send_status):
        await send_status(
            "assessment",
            "started",
            {
                "session_id": str(session_id),
                "user_id": str(user_id),
                "parallel": True,
            },
        )

    try:
        async with get_session_context() as db:
            # Determine which skills to assess (tracked skills for this user)
            skill_service = SkillService(db)
            print(f"DEBUG: About to call get_skill_context_for_llm with user_id={user_id}, raw_skill_ids={raw_skill_ids}")
            try:
                skill_contexts = await skill_service.get_skill_context_for_llm(
                    user_id=user_id,
                    skill_ids=raw_skill_ids,
                )
                print(f"DEBUG: Returned from get_skill_context_for_llm with {len(skill_contexts)} contexts")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to build skills context for assessment",
                    extra={
                        "service": "assessment",
                        "session_id": str(session_id),
                        "user_id": str(user_id),
                        "error": str(exc),
                    },
                    exc_info=True,
                )
                skill_contexts = []

            skill_ids = [ctx.skill_id for ctx in skill_contexts]

            print(f"DEBUG: skill_contexts_count={len(skill_contexts)}, raw_skill_ids={raw_skill_ids}")
            print(f"DEBUG: skill_ids={skill_ids}")

            logger.info(
                "Skill contexts retrieved",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                    "skill_contexts_count": len(skill_contexts),
                    "skill_ids": [str(sid) for sid in skill_ids],
                    "raw_skill_ids": raw_skill_ids,
                },
            )

            # interaction_id may be None if the interaction isn't committed yet.
            # That's OK - we proceed without it and backfill later via
            # backfill_interaction_id() after the voice pipeline commits.

            # If user has no tracked skills, skip assessment but log reason
            if not skill_ids:
                llm_provider = get_llm_provider()
                triage_service = TriageService(db, llm_provider=llm_provider)
                await triage_service._log_triage(  # type: ignore[attr-defined]
                    session_id=session_id,
                    interaction_id=interaction_id,
                    decision=TriageDecision.SKIP,
                    reason="no_tracked_skills",
                    provider_call_id=None,
                    latency_ms=None,
                    tokens_used=None,
                    cost_cents=None,
                    provider=None,
                    model=None,
                )

                # Emit assessment.completed status event
                if send_status and callable(send_status):
                    await send_status(
                        "assessment",
                        "completed",
                        {
                            "session_id": str(session_id),
                            "user_id": str(user_id),
                            "skill_count": 0,
                            "assessment_id": None,
                            "skipped": True,
                            "reason": "no_tracked_skills",
                        },
                    )

                # Send assessment.skipped message to client
                await manager.send_message(
                    websocket,
                    {
                        "type": "assessment.skipped",
                        "payload": {
                            "reason": "no_tracked_skills",
                            "interactionId": str(report_id) if report_id else None,
                        },
                    },
                )
                return

            # Build triage context from a few previous turns so the classifier
            # can use the surrounding conversation, not just the latest utterance.
            # We fetch the 4 most recent interactions before the current one.
            where_clauses = [Interaction.session_id == session_id]
            if interaction_id:
                where_clauses.append(Interaction.id != interaction_id)

            context_result = await db.execute(
                select(Interaction)
                .where(*where_clauses)
                .order_by(Interaction.created_at.desc())
                .limit(4)
            )
            previous = list(reversed(context_result.scalars().all()))

            triage_context = [
                ChatMessage(
                    role=ChatRole.USER if it.role == "user" else ChatRole.ASSISTANT,
                    content=it.content,
                )
                for it in previous
            ]

            triage_request = TriageRequest(
                session_id=session_id,
                user_response=user_message,
                context=triage_context,
            )

            llm_provider = get_llm_provider()
            triage_service = TriageService(db, llm_provider=llm_provider)  # Uses dedicated triage_model_id from settings
            triage_response = await triage_service.classify_response(
                triage_request,
                interaction_id=interaction_id,
                send_status=send_status,
            )

            if triage_response.decision is TriageDecision.SKIP:
                logger.info(
                    "Sending assessment.skipped",
                    extra={
                        "service": "assessment",
                        "session_id": str(session_id),
                        "reason": triage_response.reason,
                    },
                )
                await manager.send_message(
                    websocket,
                    {
                        "type": "assessment.skipped",
                        "payload": {
                            "reason": triage_response.reason,
                            "interactionId": str(report_id) if report_id else None,
                        },
                    },
                )
                logger.debug(
                    "assessment.skipped sent successfully",
                    extra={"service": "assessment", "session_id": str(session_id)},
                )
                return

            assessment_service = AssessmentService(db, llm_provider=get_llm_provider(), model_id=model_id)
            assessment_response = await assessment_service.assess_response(
                user_id=user_id,
                session_id=session_id,
                interaction_id=interaction_id,
                user_response=user_message,
                skill_ids=skill_ids,
                send_status=send_status,
                triage_decision=triage_response.decision.value,
            )

        # Send assessment.complete event after DB context closes
        await manager.send_message(
            websocket,
            {
                "type": "assessment.complete",
                "payload": {
                    "assessmentId": (
                        str(assessment_response.assessment_id)
                        if assessment_response.assessment_id
                        else None
                    ),
                    "sessionId": str(session_id),
                    "interactionId": str(report_id) if report_id else None,
                    "triageDecision": assessment_response.triage_decision,
                    "triageOverrideLabel": assessment_response.triage_override_label,
                    "userResponse": assessment_response.user_response,
                    "skills": [
                        {
                            "skillId": str(s.skill_id),
                            "level": s.level,
                            "confidence": s.confidence,
                            "summary": s.summary,
                            "feedback": {
                                "primaryTakeaway": s.feedback.primary_takeaway,
                                "strengths": s.feedback.strengths,
                                "improvements": s.feedback.improvements,
                                "exampleQuotes": [
                                    q.model_dump() for q in s.feedback.example_quotes
                                ],
                                "nextLevelCriteria": s.feedback.next_level_criteria,
                            },
                            "provider": s.provider,
                            "model": s.model,
                        }
                        for s in assessment_response.skills
                    ],
                    "metrics": (
                        assessment_response.metrics.model_dump()
                        if assessment_response.metrics
                        else None
                    ),
                },
            },
        )

    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Background assessment pipeline failed",
            extra={
                "service": "assessment",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "error": str(exc),
            },
            exc_info=True,
        )
        with contextlib.suppress(Exception):  # pragma: no cover - best-effort only
            await manager.send_message(
                websocket,
                {
                    "type": "status.update",
                    "payload": {
                        "service": "assessment",
                        "status": "error",
                        "metadata": {"error": str(exc)},
                    },
                },
            )


async def run_assessment_foreground(
    *,
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    user_message: str,
    raw_skill_ids: list[UUID] | None,
    send_status: Callable[[str, str, dict[str, Any] | None], Any] | None,
    model_id: str | None = None,
    interaction_id: UUID | None = None,
) -> ForegroundAssessmentResult:
    """Run triage + assessment synchronously (blocking).

    Used in accurate/accurate_filler modes where we need the assessment
    result before calling the LLM.

    Args:
        interaction_id: If provided, skip the DB query for the user interaction.
                        This allows the caller to pass the ID directly when known.

    Returns:
        ForegroundAssessmentResult with assessment data or skip reason.
    """
    settings = get_settings()
    if not settings.assessment_enabled:
        logger.info(
            "Foreground assessment disabled",
            extra={
                "service": "assessment",
                "session_id": str(session_id),
                "user_id": str(user_id),
            },
        )
        return ForegroundAssessmentResult(skipped=True, skip_reason="assessment_disabled")

    logger.info(
        "Starting foreground assessment",
        extra={
            "service": "assessment",
            "session_id": str(session_id),
            "user_id": str(user_id),
            "has_interaction_id": interaction_id is not None,
        },
    )

    try:
        skill_service = SkillService(db)

        async def _load_skill_contexts() -> list[Any]:
            try:
                return await skill_service.get_skill_context_for_llm(
                    user_id=user_id,
                    skill_ids=raw_skill_ids,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to build skills context for foreground assessment",
                    extra={
                        "service": "assessment",
                        "session_id": str(session_id),
                        "user_id": str(user_id),
                        "error": str(exc),
                    },
                    exc_info=True,
                )
                return []

        skill_contexts = await _load_skill_contexts()
        skill_ids = [ctx.skill_id for ctx in skill_contexts]

        # interaction_id may be None if the interaction isn't committed yet.
        # That's OK - we proceed without it and backfill later.

        # No tracked skills → skip
        if not skill_ids:
            llm_provider = get_llm_provider()
            triage_service = TriageService(db, llm_provider=llm_provider)
            await triage_service._log_triage(  # type: ignore[attr-defined]
                session_id=session_id,
                interaction_id=interaction_id,
                decision=TriageDecision.SKIP,
                reason="no_tracked_skills",
                provider_call_id=None,
                latency_ms=None,
                tokens_used=None,
                cost_cents=None,
                provider=None,
                model=None,
            )
            logger.info(
                "Foreground assessment skipping due to no_tracked_skills",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                },
            )
            return ForegroundAssessmentResult(
                skipped=True,
                skip_reason="no_tracked_skills",
                interaction_id=interaction_id,
            )

        # Build triage context from previous interactions (excluding current)
        where_clauses = [Interaction.session_id == session_id]
        if interaction_id:
            where_clauses.append(Interaction.id != interaction_id)

        context_result = await db.execute(
            select(Interaction)
            .where(*where_clauses)
            .order_by(Interaction.created_at.desc())
            .limit(4)
        )
        previous = list(reversed(context_result.scalars().all()))

        triage_context = [
            ChatMessage(
                role=ChatRole.USER if it.role == "user" else ChatRole.ASSISTANT,
                content=it.content,
            )
            for it in previous
        ]

        triage_request = TriageRequest(
            session_id=session_id,
            user_response=user_message,
            context=triage_context,
        )

        # Run triage
        llm_provider = get_llm_provider()
        triage_service = TriageService(db, llm_provider=llm_provider)  # Uses dedicated triage_model_id from settings
        triage_response = await triage_service.classify_response(
            triage_request,
            interaction_id=interaction_id,
            send_status=send_status,
        )

        logger.info(
            "Foreground triage decision",
            extra={
                "service": "assessment",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "decision": triage_response.decision.value,
                "reason": triage_response.reason,
            },
        )

        if triage_response.decision is TriageDecision.SKIP:
            return ForegroundAssessmentResult(
                skipped=True,
                skip_reason=triage_response.reason,
                interaction_id=interaction_id,
            )

        # Run assessment
        assessment_service = AssessmentService(db, llm_provider=get_llm_provider(), model_id=model_id)
        assessment_response = await assessment_service.assess_response(
            user_id=user_id,
            session_id=session_id,
            interaction_id=interaction_id,
            user_response=user_message,
            skill_ids=skill_ids,
            send_status=send_status,
            triage_decision=triage_response.decision.value,
        )

        logger.info(
            "Foreground assessment complete",
            extra={
                "service": "assessment",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "interaction_id": str(interaction_id),
                "skill_count": len(assessment_response.skills),
            },
        )

        return ForegroundAssessmentResult(
            skipped=False,
            assessment_response=assessment_response,
            interaction_id=interaction_id,
        )

    except Exception as exc:
        logger.error(
            "Foreground assessment pipeline failed",
            extra={
                "service": "assessment",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "error": str(exc),
            },
            exc_info=True,
        )
        # Return skipped on error so pipeline can continue
        return ForegroundAssessmentResult(skipped=True, skip_reason=f"error: {exc}")
