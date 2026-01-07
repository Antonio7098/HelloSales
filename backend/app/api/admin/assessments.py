from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import (
    Assessment,
    Interaction,
    Skill,
    SkillAssessment,
    TriageLog,
)

router = APIRouter()


def _apply_assessment_filters(
    query,
    *,
    user_id: UUID | None,
    session_id: UUID | None,
    interaction_id: UUID | None,
    skill_slug: str | None,
    min_level: int | None,
    max_level: int | None,
    start_date: date | None,
    end_date: date | None,
    triage_decision: str | None,
):
    """Apply common filters for assessment list queries."""

    if user_id is not None:
        query = query.where(Assessment.user_id == user_id)

    if session_id is not None:
        query = query.where(Assessment.session_id == session_id)

    if interaction_id is not None:
        query = query.where(Assessment.interaction_id == interaction_id)

    if triage_decision:
        query = query.where(Assessment.triage_decision == triage_decision)

    if start_date is not None:
        start_dt = datetime.combine(start_date, datetime.min.time())
        query = query.where(Assessment.created_at >= start_dt)

    if end_date is not None:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.where(Assessment.created_at <= end_dt)

    # Skill/level-based filters require joining through SkillAssessment/Skill
    if skill_slug or min_level is not None or max_level is not None:
        query = query.join(SkillAssessment, SkillAssessment.assessment_id == Assessment.id)

        if skill_slug:
            query = query.join(Skill, Skill.id == SkillAssessment.skill_id).where(
                Skill.slug == skill_slug
            )

        if min_level is not None:
            query = query.where(SkillAssessment.level >= min_level)

        if max_level is not None:
            query = query.where(SkillAssessment.level <= max_level)

        query = query.distinct(Assessment.id)

    return query


def _serialize_assessment_list_item(assessment: Assessment) -> dict[str, Any]:
    """Serialize an Assessment into the list item shape for the admin viewer."""

    skills_payload: list[dict[str, Any]] = []
    for sa in assessment.skill_assessments:
        skill = sa.skill
        skills_payload.append(
            {
                "skillSlug": skill.slug if skill else None,
                "level": sa.level,
                "confidence": sa.confidence,
            }
        )

    user = assessment.user

    return {
        "id": str(assessment.id),
        "createdAt": (assessment.created_at.isoformat() if assessment.created_at else None),
        "userId": str(assessment.user_id),
        "userEmail": getattr(user, "email", None) if user is not None else None,
        "sessionId": str(assessment.session_id),
        "triageDecision": assessment.triage_decision,
        "deletedAt": (
            assessment.deleted_at.isoformat() if getattr(assessment, "deleted_at", None) else None
        ),
        "deletedReason": getattr(assessment, "deleted_reason", None),
        "skills": skills_payload,
    }


def _serialize_assessment_detail(
    assessment: Assessment,
    triage_log: TriageLog | None,
) -> dict[str, Any]:
    """Serialize a single Assessment into the detailed view shape."""

    interaction = assessment.interaction
    interaction_payload: dict[str, Any] | None = None
    if interaction is not None:
        interaction_payload = {
            "id": str(interaction.id),
            "content": interaction.content,
            "transcript": interaction.transcript,
        }

    skill_items: list[dict[str, Any]] = []
    for sa in assessment.skill_assessments:
        skill = sa.skill
        fb = sa.feedback or {}
        strengths = fb.get("strengths") or []
        improvements = fb.get("improvements") or []
        example_quotes = fb.get("example_quotes") or []

        examples: list[str] = []
        for item in example_quotes:
            quote = item.get("quote") or ""
            annotation = item.get("annotation") or ""
            if annotation:
                examples.append(f"{quote} — {annotation}")
            else:
                examples.append(quote)

        skill_items.append(
            {
                "skillSlug": skill.slug if skill else None,
                "skillTitle": skill.title if skill else None,
                "level": sa.level,
                "confidence": sa.confidence,
                "summary": sa.summary,
                "feedback": {
                    "strengths": strengths,
                    "improvements": improvements,
                    "examples": examples,
                },
            }
        )

    triage_payload: dict[str, Any] | None = None
    if triage_log is not None:
        call = triage_log.provider_call
        latency_ms: int | None = None
        if call is not None:
            latency_ms = call.latency_ms

        triage_payload = {
            "decision": triage_log.decision,
            "reason": triage_log.reason,
            "latencyMs": latency_ms,
        }

    return {
        "id": str(assessment.id),
        "createdAt": (assessment.created_at.isoformat() if assessment.created_at else None),
        "userId": str(assessment.user_id),
        "userEmail": (getattr(assessment.user, "email", None) if assessment.user else None),
        "sessionId": str(assessment.session_id),
        "triageDecision": assessment.triage_decision,
        "deletedAt": (
            assessment.deleted_at.isoformat() if getattr(assessment, "deleted_at", None) else None
        ),
        "deletedReason": getattr(assessment, "deleted_reason", None),
        "interaction": interaction_payload,
        "skillAssessments": skill_items,
        "triageLog": triage_payload,
    }


@router.get("/assessments")
async def list_assessments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID | None = Query(None),
    session_id: UUID | None = Query(None),
    interaction_id: UUID | None = Query(None),
    skill_slug: str | None = Query(None),
    min_level: int | None = Query(None, ge=0, le=10),
    max_level: int | None = Query(None, ge=0, le=10),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    triage_decision: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Paginated assessment list for admin viewer."""

    base_query = select(Assessment).options(
        selectinload(Assessment.user),
        selectinload(Assessment.session),
        selectinload(Assessment.skill_assessments).selectinload(SkillAssessment.skill),
        selectinload(Assessment.interaction),
    )

    base_query = _apply_assessment_filters(
        base_query,
        user_id=user_id,
        session_id=session_id,
        interaction_id=interaction_id,
        skill_slug=skill_slug,
        min_level=min_level,
        max_level=max_level,
        start_date=start_date,
        end_date=end_date,
        triage_decision=triage_decision,
    )

    count_query = select(func.count(func.distinct(Assessment.id))).select_from(Assessment)
    count_query = _apply_assessment_filters(
        count_query,
        user_id=user_id,
        session_id=session_id,
        interaction_id=interaction_id,
        skill_slug=skill_slug,
        min_level=min_level,
        max_level=max_level,
        start_date=start_date,
        end_date=end_date,
        triage_decision=triage_decision,
    )

    total_result = await session.execute(count_query)
    total = int(total_result.scalar_one() or 0)

    offset = (page - 1) * limit
    result = await session.execute(
        base_query.order_by(Assessment.created_at.desc()).offset(offset).limit(limit)
    )
    assessments = result.scalars().unique().all()

    items = [_serialize_assessment_list_item(a) for a in assessments]

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
    }


@router.get("/assessments/{assessment_id}")
async def get_assessment_detail(
    assessment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Detailed assessment view with transcript, skills, and triage log."""

    query = (
        select(Assessment)
        .options(
            selectinload(Assessment.user),
            selectinload(Assessment.session),
            selectinload(Assessment.skill_assessments).selectinload(SkillAssessment.skill),
            selectinload(Assessment.interaction),
        )
        .where(Assessment.id == assessment_id)
    )

    result = await session.execute(query)
    assessment = result.scalar_one_or_none()

    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")

    triage_query = (
        select(TriageLog)
        .where(
            TriageLog.session_id == assessment.session_id,
            TriageLog.interaction_id == assessment.interaction_id,
        )
        .order_by(TriageLog.created_at.desc())
        .limit(1)
    )

    triage_result = await session.execute(triage_query)
    triage_log = triage_result.scalar_one_or_none()

    return _serialize_assessment_detail(assessment, triage_log)


@router.get("/interactions/{interaction_id}")
async def get_interaction_detail(
    interaction_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Fetch a single interaction/message (admin only)."""

    result = await session.execute(select(Interaction).where(Interaction.id == interaction_id))
    interaction = result.scalar_one_or_none()
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")

    return {
        "id": str(interaction.id),
        "session_id": str(interaction.session_id),
        "message_id": str(interaction.message_id),
        "role": interaction.role,
        "input_type": interaction.input_type,
        "content": interaction.content,
        "transcript": interaction.transcript,
        "audio_url": interaction.audio_url,
        "audio_duration_ms": interaction.audio_duration_ms,
        "created_at": interaction.created_at.isoformat(),
    }


@router.get("/triage-log")
async def get_latest_triage_log(
    session_id: UUID = Query(...),
    interaction_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Fetch the latest triage log entry for a specific session+interaction (admin only)."""

    triage_query = (
        select(TriageLog)
        .options(selectinload(TriageLog.provider_call))
        .where(TriageLog.session_id == session_id, TriageLog.interaction_id == interaction_id)
        .order_by(TriageLog.created_at.desc())
        .limit(1)
    )
    triage_result = await session.execute(triage_query)
    triage_log = triage_result.scalar_one_or_none()

    if triage_log is None:
        raise HTTPException(status_code=404, detail="Triage log not found")

    latency_ms: int | None = None
    if triage_log.provider_call is not None:
        latency_ms = triage_log.provider_call.latency_ms

    return {
        "id": str(triage_log.id),
        "session_id": str(triage_log.session_id),
        "interaction_id": str(triage_log.interaction_id) if triage_log.interaction_id else None,
        "decision": triage_log.decision,
        "reason": triage_log.reason,
        "latencyMs": latency_ms,
        "created_at": triage_log.created_at.isoformat() if triage_log.created_at else None,
    }


@router.get("/triage-logs")
async def list_triage_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    decision: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Paginated triage decision log for admin viewer."""

    # Base query with optional filters
    triage_query = select(TriageLog).options(
        selectinload(TriageLog.session),
        selectinload(TriageLog.interaction),
        selectinload(TriageLog.provider_call),
    )

    if decision:
        triage_query = triage_query.where(TriageLog.decision == decision)

    start_dt = None
    if start_date is not None:
        start_dt = datetime.combine(start_date, datetime.min.time())
        triage_query = triage_query.where(TriageLog.created_at >= start_dt)

    end_dt = None
    if end_date is not None:
        end_dt = datetime.combine(end_date, datetime.max.time())
        triage_query = triage_query.where(TriageLog.created_at <= end_dt)

    # Total count with the same filters
    count_query = select(func.count(TriageLog.id))

    if decision:
        count_query = count_query.where(TriageLog.decision == decision)

    if start_dt is not None:
        count_query = count_query.where(TriageLog.created_at >= start_dt)

    if end_dt is not None:
        count_query = count_query.where(TriageLog.created_at <= end_dt)

    total_result = await session.execute(count_query)
    total = int(total_result.scalar_one() or 0)

    offset = (page - 1) * limit
    result = await session.execute(
        triage_query.order_by(TriageLog.created_at.desc()).offset(offset).limit(limit)
    )
    logs = result.scalars().unique().all()

    items: list[dict[str, Any]] = []
    for log in logs:
        interaction = log.interaction
        snippet: str | None = None
        if interaction is not None and interaction.content:
            snippet = interaction.content[:200]

        call = log.provider_call
        latency_ms: int | None = None
        tokens_used: int | None = None
        cost_cents: int | None = None
        if call is not None:
            latency_ms = call.latency_ms
            if call.tokens_in is not None or call.tokens_out is not None:
                tokens_used = (call.tokens_in or 0) + (call.tokens_out or 0)
            cost_cents = call.cost_cents

        items.append(
            {
                "id": str(log.id),
                "createdAt": log.created_at.isoformat() if log.created_at else None,
                "sessionId": str(log.session_id),
                "interactionId": (str(log.interaction_id) if log.interaction_id else None),
                "decision": log.decision,
                "reason": log.reason,
                "latencyMs": latency_ms,
                "tokensUsed": tokens_used,
                "costCents": cost_cents,
                "interactionSnippet": snippet,
            }
        )

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
    }


@router.get("/assessments/export")
async def export_assessments_csv(
    format: str = Query("csv"),
    user_id: UUID | None = Query(None),
    session_id: UUID | None = Query(None),
    interaction_id: UUID | None = Query(None),
    skill_slug: str | None = Query(None),
    min_level: int | None = Query(None, ge=0, le=10),
    max_level: int | None = Query(None, ge=0, le=10),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    triage_decision: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Export assessments as CSV for the current filter set."""

    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail="Only CSV export is supported")

    query = select(Assessment).options(
        selectinload(Assessment.user),
        selectinload(Assessment.skill_assessments).selectinload(SkillAssessment.skill),
    )
    query = _apply_assessment_filters(
        query,
        user_id=user_id,
        session_id=session_id,
        interaction_id=interaction_id,
        skill_slug=skill_slug,
        min_level=min_level,
        max_level=max_level,
        start_date=start_date,
        end_date=end_date,
        triage_decision=triage_decision,
    )
    query = query.order_by(Assessment.created_at.desc())

    result = await session.execute(query)
    assessments = result.scalars().unique().all()

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "user_email",
            "session_id",
            "triage_decision",
            "skill_slugs",
            "levels",
            "confidences",
            "deleted_at",
            "deleted_reason",
        ]
    )

    for a in assessments:
        user_email = getattr(a.user, "email", None) if a.user else None
        slugs: list[str] = []
        levels: list[str] = []
        confidences: list[str] = []
        for sa in a.skill_assessments:
            slug = sa.skill.slug if sa.skill else ""
            slugs.append(str(slug))
            levels.append(str(sa.level))
            confidences.append("" if sa.confidence is None else str(sa.confidence))

        writer.writerow(
            [
                str(a.id),
                a.created_at.isoformat() if a.created_at else "",
                user_email or "",
                str(a.session_id),
                a.triage_decision or "",
                ";".join(slugs),
                ";".join(levels),
                ";".join(confidences),
                a.deleted_at.isoformat() if getattr(a, "deleted_at", None) else "",
                getattr(a, "deleted_reason", "") or "",
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8")

    from fastapi.responses import Response

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=assessments.csv",
        },
    )
