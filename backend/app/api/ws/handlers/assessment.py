"""WebSocket handlers for assessment-related messages."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.providers.factory import get_llm_provider
from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.config import get_settings
from app.database import get_session_context
from app.domains.assessment.service import AssessmentService
from app.domains.skills.service import SkillService
from app.models import Interaction, Session
from app.models.assessment import Assessment, SkillAssessment

logger = logging.getLogger("assessment.ws")

router = get_router()


async def _send_error(
    websocket: WebSocket,
    manager: ConnectionManager,
    code: str,
    message: str,
    request_id: str | None,
) -> None:
    await manager.send_message(
        websocket,
        {
            "type": "error",
            "payload": {
                "code": code,
                "message": message,
                "requestId": request_id,
            },
        },
    )


@router.handler("assessment.trigger")
async def handle_assessment_trigger(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle manual assessment trigger from the client."""

    conn = manager.get_connection(websocket)
    request_id = payload.get("requestId")

    if not conn or not conn.authenticated or not conn.user_id:
        await _send_error(
            websocket,
            manager,
            "NOT_AUTHENTICATED",
            "Must authenticate before triggering assessment",
            request_id,
        )
        return

    settings = get_settings()
    if not settings.assessment_enabled:
        await _send_error(
            websocket,
            manager,
            "ASSESSMENT_DISABLED",
            "Assessment feature is disabled",
            request_id,
        )
        return

    session_id_str = payload.get("sessionId")
    interaction_id_str = payload.get("interactionId")

    if not session_id_str:
        await _send_error(
            websocket,
            manager,
            "INVALID_PAYLOAD",
            "sessionId is required",
            request_id,
        )
        return

    try:
        session_id = uuid.UUID(session_id_str)
    except ValueError as exc:  # pragma: no cover - defensive
        await _send_error(
            websocket,
            manager,
            "INVALID_PAYLOAD",
            f"Invalid sessionId UUID format: {exc}",
            request_id,
        )
        return

    interaction_id: uuid.UUID | None = None
    if interaction_id_str:
        try:
            interaction_id = uuid.UUID(interaction_id_str)
        except ValueError as exc:  # pragma: no cover - defensive
            await _send_error(
                websocket,
                manager,
                "INVALID_PAYLOAD",
                f"Invalid interactionId UUID format: {exc}",
                request_id,
            )
            return

    async def send_status(service: str, status: str, metadata: dict[str, Any] | None) -> None:
        await manager.send_message(
            websocket,
            {
                "type": "status.update",
                "payload": {
                    "service": service,
                    "status": status,
                    "metadata": metadata or {},
                },
            },
        )

    async def run_manual_assessment() -> None:
        try:
            async with get_session_context() as db:
                result = await db.execute(select(Session).where(Session.id == session_id))
                session = result.scalar_one_or_none()

                if not session or session.user_id != conn.user_id:
                    await _send_error(
                        websocket,
                        manager,
                        "NOT_FOUND",
                        "Session not found for current user",
                        request_id,
                    )
                    return

                if interaction_id is not None:
                    result_int = await db.execute(
                        select(Interaction).where(
                            Interaction.id == interaction_id,
                            Interaction.session_id == session_id,
                        )
                    )
                else:
                    result_int = await db.execute(
                        select(Interaction)
                        .where(
                            Interaction.session_id == session_id,
                            Interaction.role == "user",
                        )
                        .order_by(Interaction.created_at.desc())
                        .limit(1)
                    )

                interaction = result_int.scalar_one_or_none()
                if not interaction:
                    await _send_error(
                        websocket,
                        manager,
                        "NO_INTERACTION",
                        "No user interaction found to assess",
                        request_id,
                    )
                    return

                user_message = interaction.content

                skill_service = SkillService(db)
                try:
                    skill_contexts = await skill_service.get_skill_context_for_llm(
                        user_id=conn.user_id,
                        skill_ids=None,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(
                        "Failed to build skills context for manual assessment",
                        extra={
                            "service": "assessment",
                            "session_id": str(session_id),
                            "user_id": str(conn.user_id),
                            "error": str(exc),
                        },
                        exc_info=True,
                    )
                    skill_contexts = []

                skill_ids = [ctx.skill_id for ctx in skill_contexts]

                if not skill_ids:
                    await manager.send_message(
                        websocket,
                        {
                            "type": "assessment.skipped",
                            "payload": {
                                "reason": "no_tracked_skills",
                                "interactionId": str(interaction.id),
                            },
                        },
                    )
                    return

                # Use the same effective model ID as the rest of the connection
                model_id = manager.get_model_id(websocket)

                service = AssessmentService(db, llm_provider=get_llm_provider(), model_id=model_id)
                assessment_response = await service.assess_response(
                    user_id=conn.user_id,
                    session_id=session_id,
                    interaction_id=interaction.id,
                    user_response=user_message,
                    skill_ids=skill_ids,
                    send_status=send_status,
                    triage_decision="manual",
                )

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
                        "interactionId": str(interaction.id),
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
                "Manual assessment pipeline failed",
                extra={
                    "service": "assessment",
                    "session_id": str(session_id),
                    "user_id": str(conn.user_id),
                    "error": str(exc),
                },
                exc_info=True,
            )
            await send_status("assessment", "error", {"error": str(exc)})

    asyncio.create_task(run_manual_assessment())


@router.handler("assessment.history")
async def handle_assessment_history(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Return assessment history for the current user."""

    conn = manager.get_connection(websocket)
    request_id = payload.get("requestId")

    if not conn or not conn.authenticated or not conn.user_id:
        await _send_error(
            websocket,
            manager,
            "NOT_AUTHENTICATED",
            "Must authenticate before requesting assessment history",
            request_id,
        )
        return

    settings = get_settings()
    if not settings.assessment_enabled:
        await _send_error(
            websocket,
            manager,
            "ASSESSMENT_DISABLED",
            "Assessment feature is disabled",
            request_id,
        )
        return

    session_id_str = payload.get("sessionId")
    skill_id_str = payload.get("skillId")
    limit_raw = payload.get("limit")

    session_id: uuid.UUID | None = None
    skill_id: uuid.UUID | None = None

    if session_id_str:
        try:
            session_id = uuid.UUID(session_id_str)
        except ValueError as exc:  # pragma: no cover - defensive
            await _send_error(
                websocket,
                manager,
                "INVALID_PAYLOAD",
                f"Invalid sessionId UUID format: {exc}",
                request_id,
            )
            return

    if skill_id_str:
        try:
            skill_id = uuid.UUID(skill_id_str)
        except ValueError as exc:  # pragma: no cover - defensive
            await _send_error(
                websocket,
                manager,
                "INVALID_PAYLOAD",
                f"Invalid skillId UUID format: {exc}",
                request_id,
            )
            return

    try:
        limit = int(limit_raw) if limit_raw is not None else 10
    except (TypeError, ValueError):  # pragma: no cover - defensive
        limit = 10

    if limit <= 0:
        limit = 1
    if limit > 50:
        limit = 50

    async with get_session_context() as db:
        query = select(Assessment).where(
            Assessment.user_id == conn.user_id,
            Assessment.deleted_at.is_(None),
        )

        if session_id is not None:
            query = query.where(Assessment.session_id == session_id)

        query = query.options(
            selectinload(Assessment.skill_assessments).selectinload(SkillAssessment.provider_call),
            selectinload(Assessment.interaction),
        )
        query = query.order_by(Assessment.created_at.desc()).limit(limit)

        result = await db.execute(query)
        assessments = list(result.scalars().all())

        items: list[dict[str, Any]] = []

        for assessment in assessments:
            skills_payload = []
            for sa in assessment.skill_assessments:
                if skill_id is not None and sa.skill_id != skill_id:
                    continue

                call = sa.provider_call
                provider = call.provider if call is not None else getattr(sa, "provider", None)
                model = call.model_id if call is not None else getattr(sa, "model_id", None)

                fb = sa.feedback or {}
                skills_payload.append(
                    {
                        "skillId": str(sa.skill_id),
                        "level": sa.level,
                        "confidence": sa.confidence,
                        "summary": sa.summary,
                        "feedback": {
                            "primaryTakeaway": fb.get("primary_takeaway", ""),
                            "strengths": fb.get("strengths", []),
                            "improvements": fb.get("improvements", []),
                            "exampleQuotes": fb.get("example_quotes", []),
                            "nextLevelCriteria": fb.get("next_level_criteria"),
                        },
                        "provider": provider,
                        "model": model,
                    }
                )

            if not skills_payload:
                continue

            items.append(
                {
                    "assessmentId": str(assessment.id),
                    "sessionId": str(assessment.session_id),
                    "interactionId": (
                        str(assessment.interaction_id) if assessment.interaction_id else None
                    ),
                    "triageDecision": assessment.triage_decision,
                    "triageOverrideLabel": getattr(assessment, "triage_override_label", None),
                    "createdAt": assessment.created_at.isoformat(),
                    "userResponse": (
                        assessment.interaction.content
                        if assessment.interaction is not None
                        else None
                    ),
                    "skills": skills_payload,
                }
            )

    await manager.send_message(
        websocket,
        {
            "type": "assessment.history.list",
            "payload": {
                "assessments": items,
                "total": len(items),
                "hasMore": False,
            },
        },
    )


@router.handler("assessment.delete")
async def handle_assessment_delete(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Soft-delete an assessment for the current user."""

    conn = manager.get_connection(websocket)
    request_id = payload.get("requestId")

    if not conn or not conn.authenticated or not conn.user_id:
        await _send_error(
            websocket,
            manager,
            "NOT_AUTHENTICATED",
            "Must authenticate before deleting assessment",
            request_id,
        )
        return

    assessment_id_str = payload.get("assessmentId")
    reason_raw = payload.get("reason")

    if not assessment_id_str:
        await _send_error(
            websocket,
            manager,
            "INVALID_PAYLOAD",
            "assessmentId is required",
            request_id,
        )
        return

    try:
        assessment_id = uuid.UUID(assessment_id_str)
    except ValueError as exc:  # pragma: no cover - defensive
        await _send_error(
            websocket,
            manager,
            "INVALID_PAYLOAD",
            f"Invalid assessmentId UUID format: {exc}",
            request_id,
        )
        return

    async with get_session_context() as db:
        result = await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.user_id == conn.user_id,
            )
        )
        assessment = result.scalar_one_or_none()

        if not assessment:
            await _send_error(
                websocket,
                manager,
                "NOT_FOUND",
                "Assessment not found for current user",
                request_id,
            )
            return

        # Idempotent soft delete
        if getattr(assessment, "deleted_at", None) is None:
            assessment.deleted_at = datetime.utcnow()
            if isinstance(reason_raw, str):
                reason = reason_raw.strip()
                if reason:
                    if len(reason) > 255:
                        reason = reason[:255]
                    assessment.deleted_reason = reason
            await db.commit()
            await db.refresh(assessment)

        deleted_at = assessment.deleted_at

    await manager.send_message(
        websocket,
        {
            "type": "assessment.deleted",
            "payload": {
                "assessmentId": str(assessment.id),
                "sessionId": str(assessment.session_id),
                "interactionId": (
                    str(assessment.interaction_id) if assessment.interaction_id else None
                ),
                "deletedAt": deleted_at.isoformat() if deleted_at else None,
                "reason": assessment.deleted_reason,
            },
        },
    )
