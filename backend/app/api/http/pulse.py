"""Pulse API - Enterprise Edition (WorkOS only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.http.dependencies import get_identity_claims
from app.database import get_session
from app.domains.organization.service import OrganizationService
from app.models import OrganizationMembership, PipelineEvent, PipelineRun, User

router = APIRouter(prefix="/api/v1/pulse", tags=["pulse"])


@dataclass(frozen=True)
class PulseAccessContext:
    """Access context for enterprise pulse endpoints."""
    user_id: UUID
    org_id: UUID  # Enterprise: always required


async def _get_pulse_access_context(
    session: AsyncSession = Depends(get_session),
    identity=Depends(get_identity_claims),
) -> PulseAccessContext:
    """Get pulse access context - enterprise requires org membership."""
    subject = identity.subject
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    # Enterprise: org_id is required
    if not identity.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization context required for enterprise access",
        )

    # Find or create user
    result = await session.execute(
        select(User).where(User.auth_subject == subject)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            auth_provider="workos",
            auth_subject=subject,
            email=identity.email,
            display_name=(identity.email or "").split("@")[0] if identity.email else None,
        )
        session.add(user)
        await session.flush()

    # Get or create organization and membership
    org_id_str = str(identity.org_id)
    org_service = OrganizationService(session)
    org = await org_service.upsert_organization(
        org_id=org_id_str,
        user_id=user.id,
    )

    membership = await session.get(
        OrganizationMembership,
        {"user_id": user.id, "organization_id": org.id},
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership required",
        )

    return PulseAccessContext(user_id=user.id, org_id=org.id)


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


@router.get("/pipeline-runs")
async def get_pulse_pipeline_runs(
    service: str | None = None,
    success: bool | None = None,
    since_minutes: int = 60,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    ctx: PulseAccessContext = Depends(_get_pulse_access_context),
) -> dict[str, Any]:
    """Get pipeline runs for the enterprise organization."""
    now = datetime.utcnow()
    since: datetime | None = None
    if since_minutes and since_minutes > 0:
        since = now - timedelta(minutes=since_minutes)

    # Enterprise: scope to organization
    query = (
        select(PipelineRun)
        .where(PipelineRun.org_id == ctx.org_id)
        .order_by(PipelineRun.created_at.desc())
    )

    if since is not None:
        query = query.where(PipelineRun.created_at >= since)
    if service:
        query = query.where(PipelineRun.service == service)
    if success is not None:
        query = query.where(PipelineRun.success == success)

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


@router.get("/pipeline-runs/{run_id}")
async def get_pulse_pipeline_run_detail(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    ctx: PulseAccessContext = Depends(_get_pulse_access_context),
) -> dict[str, Any]:
    """Get details for a specific pipeline run."""
    run = await session.get(PipelineRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="PipelineRun not found")

    # Enterprise: verify org access
    if run.org_id != ctx.org_id:
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


@router.get("/pipeline-events")
async def get_pulse_pipeline_events(
    pipeline_run_id: UUID,
    limit: int = 500,
    session: AsyncSession = Depends(get_session),
    ctx: PulseAccessContext = Depends(_get_pulse_access_context),
) -> dict[str, Any]:
    """Get events for a specific pipeline run."""
    run = await session.get(PipelineRun, pipeline_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="PipelineRun not found")

    # Enterprise: verify org access
    if run.org_id != ctx.org_id:
        raise HTTPException(status_code=404, detail="PipelineRun not found")

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
