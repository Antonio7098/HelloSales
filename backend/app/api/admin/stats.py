import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import LLMMessage
from app.ai.providers.factory import get_llm_provider
from app.ai.substrate import ProviderCallLogger
from app.database import get_session
from app.infrastructure.pricing import estimate_llm_cost_cents
from app.models import (
    Assessment,
    PipelineEvent,
    PipelineRun,
    ProviderCall,
    Session,
    Skill,
    SkillAssessment,
    TriageLog,
    User,
)

router = APIRouter()


async def _collect_stats(session: AsyncSession) -> dict[str, Any]:
    now = datetime.utcnow()
    start_of_day = datetime(now.year, now.month, now.day)
    week_ago = now - timedelta(days=7)

    users_result = await session.execute(select(func.count(User.id)))
    total_users = users_result.scalar_one() or 0

    sessions_result = await session.execute(select(func.count(Session.id)))
    total_sessions = sessions_result.scalar_one() or 0

    assessments_result = await session.execute(
        select(func.count(Assessment.id)).where(Assessment.deleted_at.is_(None))
    )
    total_assessments = assessments_result.scalar_one() or 0

    assessments_today_result = await session.execute(
        select(func.count(Assessment.id)).where(
            Assessment.created_at >= start_of_day,
            Assessment.deleted_at.is_(None),
        )
    )
    assessments_today = assessments_today_result.scalar_one() or 0

    assessments_week_result = await session.execute(
        select(func.count(Assessment.id)).where(
            Assessment.created_at >= week_ago,
            Assessment.deleted_at.is_(None),
        )
    )
    assessments_week = assessments_week_result.scalar_one() or 0

    triage_result = await session.execute(
        select(TriageLog.decision, func.count(TriageLog.id))
        .where(TriageLog.created_at >= week_ago)
        .group_by(TriageLog.decision)
    )
    triage_rows = triage_result.all()
    triage_by_decision: dict[str, int] = {}
    for decision, count in triage_rows:
        triage_by_decision[str(decision)] = int(count)

    return {
        "timestamp": now.isoformat() + "Z",
        "totals": {
            "users": int(total_users),
            "sessions": int(total_sessions),
            "assessments": int(total_assessments),
        },
        "assessments": {
            "today": int(assessments_today),
            "this_week": int(assessments_week),
        },
        "triage": {
            "by_decision": triage_by_decision,
        },
    }


def _serialize_provider_call(call: ProviderCall) -> dict[str, Any]:
    return {
        "id": str(call.id),
        "created_at": call.created_at.isoformat() + "Z",
        "service": call.service,
        "operation": call.operation,
        "provider": call.provider,
        "model_id": call.model_id,
        "request_id": str(call.request_id) if call.request_id else None,
        "session_id": str(call.session_id) if call.session_id else None,
        "user_id": str(call.user_id) if call.user_id else None,
        "interaction_id": str(call.interaction_id) if call.interaction_id else None,
        "prompt_messages": call.prompt_messages,
        "prompt_text": call.prompt_text,
        "output_content": call.output_content,
        "output_parsed": call.output_parsed,
        "latency_ms": call.latency_ms,
        "tokens_in": call.tokens_in,
        "tokens_out": call.tokens_out,
        "audio_duration_ms": call.audio_duration_ms,
        "cost_cents": call.cost_cents,
        "success": call.success,
        "error": call.error,
    }


def _serialize_pipeline_run(run: PipelineRun) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "created_at": run.created_at.isoformat() + "Z",
        "service": run.service,
        "status": getattr(run, "status", None),
        "mode": getattr(run, "mode", None),
        "quality_mode": getattr(run, "quality_mode", None),
        "request_id": str(run.request_id) if run.request_id else None,
        "org_id": str(run.org_id) if run.org_id else None,
        "session_id": str(run.session_id) if run.session_id else None,
        "user_id": str(run.user_id) if run.user_id else None,
        "interaction_id": str(run.interaction_id) if run.interaction_id else None,
        "total_latency_ms": run.total_latency_ms,
        "ttft_ms": run.ttft_ms,
        "ttfa_ms": run.ttfa_ms,
        "ttfc_ms": run.ttfc_ms,
        "tokens_in": run.tokens_in,
        "tokens_out": run.tokens_out,
        "input_audio_duration_ms": run.input_audio_duration_ms,
        "output_audio_duration_ms": run.output_audio_duration_ms,
        "total_cost_cents": run.total_cost_cents,
        "tokens_per_second": run.tokens_per_second,
        "success": run.success,
        "error": run.error,
        "stages": run.stages,
    }


def _serialize_pipeline_event(event: PipelineEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "pipeline_run_id": str(event.pipeline_run_id),
        "type": event.type,
        "timestamp": event.timestamp.isoformat() + "Z",
        "data": event.data,
        "request_id": str(event.request_id) if event.request_id else None,
        "session_id": str(event.session_id) if event.session_id else None,
        "user_id": str(event.user_id) if event.user_id else None,
        "org_id": str(event.org_id) if event.org_id else None,
    }


class ProviderCallRetryRequest(BaseModel):
    model_id: str


async def _collect_assessment_stats(session: AsyncSession) -> dict[str, Any]:
    """Aggregate assessment metrics for charts.

    Returns counts grouped by skill and level, plus simple daily/weekly trends and
    an overall average confidence across all skill assessments.
    """

    now = datetime.utcnow()
    window_start = now - timedelta(days=30)

    # Count assessments by skill slug
    by_skill_rows = await session.execute(
        select(Skill.slug, func.count(SkillAssessment.id))
        .join(SkillAssessment, Skill.id == SkillAssessment.skill_id)
        .join(Assessment, Assessment.id == SkillAssessment.assessment_id)
        .where(Assessment.deleted_at.is_(None))
        .group_by(Skill.slug)
    )
    by_skill: list[dict[str, Any]] = []
    for slug, count in by_skill_rows.all():
        by_skill.append({"skillSlug": str(slug), "count": int(count)})

    # Count assessments by assessed level
    by_level_rows = await session.execute(
        select(SkillAssessment.level, func.count(SkillAssessment.id))
        .join(Assessment, Assessment.id == SkillAssessment.assessment_id)
        .where(Assessment.deleted_at.is_(None))
        .group_by(SkillAssessment.level)
        .order_by(SkillAssessment.level)
    )
    by_level: list[dict[str, Any]] = []
    for level, count in by_level_rows.all():
        by_level.append({"level": int(level), "count": int(count)})

    # Average confidence across all skill assessments
    avg_conf_result = await session.execute(select(func.avg(SkillAssessment.confidence)))
    avg_conf_raw = avg_conf_result.scalar()
    avg_confidence: float | None = float(avg_conf_raw) if avg_conf_raw is not None else None

    # Daily assessment counts over the last 30 days
    daily_rows = await session.execute(
        select(
            func.date_trunc("day", Assessment.created_at).label("day"),
            func.count(Assessment.id),
        )
        .where(
            Assessment.created_at >= window_start,
            Assessment.deleted_at.is_(None),
        )
        .group_by("day")
        .order_by("day")
    )
    daily: list[dict[str, Any]] = []
    for day, count in daily_rows.all():
        # date_trunc returns a datetime; convert to date ISO string for charts
        daily.append({"date": day.date().isoformat(), "count": int(count)})

    # Weekly assessment counts over the last 30 days
    weekly_rows = await session.execute(
        select(
            func.date_trunc("week", Assessment.created_at).label("week"),
            func.count(Assessment.id),
        )
        .where(
            Assessment.created_at >= window_start,
            Assessment.deleted_at.is_(None),
        )
        .group_by("week")
        .order_by("week")
    )
    weekly: list[dict[str, Any]] = []
    for week_start, count in weekly_rows.all():
        weekly.append({"weekStart": week_start.date().isoformat(), "count": int(count)})

    return {
        "by_skill": by_skill,
        "by_level": by_level,
        "avg_confidence": avg_confidence,
        "daily": daily,
        "weekly": weekly,
    }


@router.get("/stats")
async def get_admin_stats(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    return await _collect_stats(session)


@router.get("/stats/assessments")
async def get_assessment_stats(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Assessment-specific aggregate metrics for the admin dashboard."""

    return await _collect_assessment_stats(session)


@router.get("/stats/provider-calls")
async def get_provider_calls(
    service: str | None = None,
    operation: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    success: bool | None = None,
    since_minutes: int = 60,
    limit: int = 100,
    request_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return recent provider_calls for observability dashboards.

    This is primarily used by the eval/monitoring app. Results are ordered by
    newest first and limited to a reasonable maximum to avoid overloading the UI.
    """

    now = datetime.utcnow()
    since: datetime | None = None
    if since_minutes and since_minutes > 0:
        since = now - timedelta(minutes=since_minutes)

    query = select(ProviderCall).order_by(ProviderCall.created_at.desc())

    if since is not None:
        query = query.where(ProviderCall.created_at >= since)
    if service:
        query = query.where(ProviderCall.service == service)
    if operation:
        query = query.where(ProviderCall.operation == operation)
    if provider:
        query = query.where(ProviderCall.provider == provider)
    if model:
        query = query.where(ProviderCall.model_id == model)
    if success is not None:
        query = query.where(ProviderCall.success == success)
    if request_id is not None:
        query = query.where(ProviderCall.request_id == request_id)

    # Hard cap on limit to keep responses manageable
    effective_limit = max(1, min(limit, 500))
    query = query.limit(effective_limit)

    result = await session.execute(query)
    rows = list(result.scalars().all())

    items: list[dict[str, Any]] = []
    for call in rows:
        items.append(_serialize_provider_call(call))

    return {
        "timestamp": now.isoformat() + "Z",
        "count": len(items),
        "items": items,
        "since": since.isoformat() + "Z" if since is not None else None,
    }


@router.get("/stats/pipeline-metrics")
async def get_pipeline_metrics(
    since_minutes: int = 60 * 24,
    service: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    now = datetime.utcnow()
    since: datetime | None = None
    if since_minutes and since_minutes > 0:
        since = now - timedelta(minutes=since_minutes)

    base_where = []
    if since is not None:
        base_where.append(PipelineRun.created_at >= since)
    if service:
        base_where.append(PipelineRun.service == service)

    status_rows = await session.execute(
        select(
            PipelineRun.service,
            func.count(PipelineRun.id).label("count"),
            func.count(PipelineRun.id).filter(PipelineRun.success.is_(True)).label("success"),
            func.count(PipelineRun.id).filter(PipelineRun.success.is_(False)).label("failed"),
        )
        .where(*base_where)
        .group_by(PipelineRun.service)
        .order_by(PipelineRun.service)
    )

    by_service: list[dict[str, Any]] = []
    total_success = 0
    total_failed = 0
    total_count = 0
    for svc, count, success_count, failed_count in status_rows.all():
        svc_count = int(count or 0)
        svc_success = int(success_count or 0)
        svc_failed = int(failed_count or 0)
        by_service.append(
            {
                "service": str(svc),
                "count": svc_count,
                "success": svc_success,
                "failed": svc_failed,
            }
        )
        total_count += svc_count
        total_success += svc_success
        total_failed += svc_failed

    bucket_expr = case(
        (PipelineRun.total_latency_ms < 250, "0-250"),
        (PipelineRun.total_latency_ms < 500, "250-500"),
        (PipelineRun.total_latency_ms < 1000, "500-1000"),
        (PipelineRun.total_latency_ms < 2000, "1000-2000"),
        (PipelineRun.total_latency_ms < 5000, "2000-5000"),
        else_="5000+",
    ).label("bucket")

    hist_where = list(base_where)
    hist_where.append(PipelineRun.total_latency_ms.is_not(None))

    hist_rows = await session.execute(
        select(bucket_expr, func.count(PipelineRun.id)).where(*hist_where).group_by(bucket_expr)
    )

    bucket_order = ["0-250", "250-500", "500-1000", "1000-2000", "2000-5000", "5000+"]
    bucket_counts: dict[str, int] = dict.fromkeys(bucket_order, 0)
    for bucket, count in hist_rows.all():
        if bucket is None:
            continue
        bucket_counts[str(bucket)] = int(count or 0)

    histogram = [{"bucket_ms": b, "count": bucket_counts[b]} for b in bucket_order]

    return {
        "timestamp": now.isoformat() + "Z",
        "since": since.isoformat() + "Z" if since is not None else None,
        "service": service,
        "totals": {
            "count": total_count,
            "success": total_success,
            "failed": total_failed,
        },
        "by_service": by_service,
        "total_latency_ms_histogram": histogram,
    }


@router.get("/stats/policy-denials")
async def get_policy_denials(
    since_minutes: int = 60 * 24,
    limit: int = 5000,
    pipeline_run_id: UUID | None = None,
    request_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    now = datetime.utcnow()
    since: datetime | None = None
    if since_minutes and since_minutes > 0:
        since = now - timedelta(minutes=since_minutes)

    query = select(PipelineEvent.data).where(PipelineEvent.type == "policy.decision")
    if since is not None:
        query = query.where(PipelineEvent.timestamp >= since)
    if pipeline_run_id is not None:
        query = query.where(PipelineEvent.pipeline_run_id == pipeline_run_id)
    if request_id is not None:
        query = query.where(PipelineEvent.request_id == request_id)

    effective_limit = max(1, min(limit, 20000))
    query = query.order_by(PipelineEvent.timestamp.desc()).limit(effective_limit)

    result = await session.execute(query)
    rows = list(result.scalars().all())

    total = 0
    denied_total = 0
    denied_by_reason: dict[str, int] = {}
    denied_by_intent: dict[str, int] = {}
    denied_by_checkpoint: dict[str, int] = {}
    denied_by_intent_reason: dict[str, int] = {}

    for data in rows:
        if not isinstance(data, dict):
            continue
        total += 1
        decision = str(data.get("decision") or "")
        if decision == "allow":
            continue

        denied_total += 1
        reason = str(data.get("reason") or "unknown")
        intent = str(data.get("intent") or "unknown")
        checkpoint = str(data.get("checkpoint") or "unknown")

        denied_by_reason[reason] = denied_by_reason.get(reason, 0) + 1
        denied_by_intent[intent] = denied_by_intent.get(intent, 0) + 1
        denied_by_checkpoint[checkpoint] = denied_by_checkpoint.get(checkpoint, 0) + 1
        key = f"{intent}::{reason}"
        denied_by_intent_reason[key] = denied_by_intent_reason.get(key, 0) + 1

    return {
        "timestamp": now.isoformat() + "Z",
        "since": since.isoformat() + "Z" if since is not None else None,
        "limit": effective_limit,
        "total_policy_decisions": total,
        "denied_total": denied_total,
        "denied_by_reason": denied_by_reason,
        "denied_by_intent": denied_by_intent,
        "denied_by_checkpoint": denied_by_checkpoint,
        "denied_by_intent_reason": denied_by_intent_reason,
    }


@router.get("/stats/policy-triggers")
async def get_policy_triggers(
    since_minutes: int = 60 * 24,
    pipeline_run_id: UUID | None = None,
    request_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    now = datetime.utcnow()
    since: datetime | None = None
    if since_minutes and since_minutes > 0:
        since = now - timedelta(minutes=since_minutes)

    trigger_types = [
        "policy.budget.exceeded",
        "policy.quota.exceeded",
    ]

    query = (
        select(PipelineEvent.type, func.count(PipelineEvent.id))
        .where(PipelineEvent.type.in_(trigger_types))
        .group_by(PipelineEvent.type)
    )
    if since is not None:
        query = query.where(PipelineEvent.timestamp >= since)
    if pipeline_run_id is not None:
        query = query.where(PipelineEvent.pipeline_run_id == pipeline_run_id)
    if request_id is not None:
        query = query.where(PipelineEvent.request_id == request_id)

    result = await session.execute(query)
    rows = result.all()
    by_type: dict[str, int] = dict.fromkeys(trigger_types, 0)
    for t, count in rows:
        by_type[str(t)] = int(count or 0)

    total = sum(by_type.values())

    return {
        "timestamp": now.isoformat() + "Z",
        "since": since.isoformat() + "Z" if since is not None else None,
        "total": total,
        "by_type": by_type,
    }


@router.get("/stats/pipeline-events")
async def get_pipeline_events(
    pipeline_run_id: UUID,
    limit: int = 500,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return pipeline_events for a specific pipeline_run.

    This is the primary endpoint used by the eval Central Pulse viewer.
    Events are ordered oldest first to support timeline rendering.
    """

    query = (
        select(PipelineEvent)
        .where(PipelineEvent.pipeline_run_id == pipeline_run_id)
        .order_by(PipelineEvent.timestamp.asc())
    )

    effective_limit = max(1, min(limit, 2000))
    query = query.limit(effective_limit)

    result = await session.execute(query)
    rows = list(result.scalars().all())

    items: list[dict[str, Any]] = []
    for event in rows:
        items.append(_serialize_pipeline_event(event))

    return {
        "pipeline_run_id": str(pipeline_run_id),
        "count": len(items),
        "items": items,
    }


@router.get("/stats/pipeline-runs/{run_id}")
async def get_pipeline_run_detail(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    run = await session.get(PipelineRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="PipelineRun not found")

    events_result = await session.execute(
        select(PipelineEvent)
        .where(PipelineEvent.pipeline_run_id == run_id)
        .order_by(PipelineEvent.timestamp.asc())
    )
    events = list(events_result.scalars().all())

    return {
        "run": _serialize_pipeline_run(run),
        "events": [_serialize_pipeline_event(e) for e in events],
    }


@router.post("/stats/provider-calls/{call_id}/retry")
async def retry_provider_call(
    call_id: UUID,
    payload: ProviderCallRetryRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    result = await session.execute(select(ProviderCall).where(ProviderCall.id == call_id))
    call = result.scalar_one_or_none()
    if call is None:
        raise HTTPException(status_code=404, detail="ProviderCall not found")
    if call.operation != "llm":
        raise HTTPException(status_code=400, detail="Retry is only supported for LLM calls")

    prompt_messages = call.prompt_messages
    if not prompt_messages:
        raise HTTPException(status_code=400, detail="Original call has no prompt to replay")

    if isinstance(prompt_messages, dict) and "messages" in prompt_messages:
        messages_raw: Any = prompt_messages["messages"]
    else:
        messages_raw = prompt_messages

    if not isinstance(messages_raw, list):
        raise HTTPException(
            status_code=400,
            detail="Original prompt_messages format is not supported for replay",
        )

    messages: list[LLMMessage] = []
    for item in messages_raw:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip() or "user"
        content = str(item.get("content") or "")
        messages.append(LLMMessage(role=role, content=content))

    if not messages:
        raise HTTPException(
            status_code=400,
            detail="Original prompt is empty and cannot be replayed",
        )

    provider_name = (call.provider or "").lower() or "groq"
    llm = get_llm_provider(provider_name)

    model_id = payload.model_id.strip() or None

    start = time.time()
    response = await llm.generate(messages, model=model_id)
    latency_ms = int((time.time() - start) * 1000)

    cost_cents = estimate_llm_cost_cents(
        provider=llm.name,
        model=response.model,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
    )

    call_logger = ProviderCallLogger(session)
    replay_call = await call_logger.log_llm_call(
        service=call.service,
        provider=llm.name,
        model_id=response.model,
        prompt_messages=prompt_messages,
        output_content=response.content,
        output_parsed=None,
        latency_ms=latency_ms,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_cents=cost_cents,
        success=True,
        session_id=call.session_id,
        user_id=call.user_id,
        interaction_id=call.interaction_id,
        request_id=call.request_id,
    )

    return _serialize_provider_call(replay_call)


@router.get("/stats/pipeline-runs")
async def get_pipeline_runs(
    service: str | None = None,
    success: bool | None = None,
    since_minutes: int = 60,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return recent pipeline_runs for observability dashboards.

    This provides access to end-to-end pipeline metrics, primarily for voice
    processing pipelines. Results are ordered by newest first and limited to
    a reasonable maximum to avoid overloading the UI.
    """

    now = datetime.utcnow()
    since: datetime | None = None
    if since_minutes and since_minutes > 0:
        since = now - timedelta(minutes=since_minutes)

    query = select(PipelineRun).order_by(PipelineRun.created_at.desc())

    if since is not None:
        query = query.where(PipelineRun.created_at >= since)
    if service:
        query = query.where(PipelineRun.service == service)
    if success is not None:
        query = query.where(PipelineRun.success == success)

    # Hard cap on limit to keep responses manageable
    effective_limit = max(1, min(limit, 500))
    query = query.limit(effective_limit)

    result = await session.execute(query)
    rows = list(result.scalars().all())

    items: list[dict[str, Any]] = []
    for run in rows:
        items.append(_serialize_pipeline_run(run))

    return {
        "timestamp": now.isoformat() + "Z",
        "count": len(items),
        "items": items,
        "since": since.isoformat() + "Z" if since is not None else None,
    }


@router.get("/health")
async def admin_health() -> dict[str, str]:
    return {"status": "ok", "service": "eloquence-admin-api"}
