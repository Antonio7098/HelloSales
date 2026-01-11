"""Pulse API endpoints - observability dashboard data."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.auth.context import AuthContext, get_optional_auth
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.observability import (
    DeadLetterQueueModel,
    PipelineEventModel,
    PipelineRunModel,
    ProviderCallModel,
)

router = APIRouter(prefix="/pulse", tags=["pulse"])


# Response models
class PipelineRunSummary(BaseModel):
    """Summary of a pipeline run."""

    id: UUID
    service: str
    request_id: str | None
    session_id: UUID | None
    user_id: UUID | None
    org_id: UUID | None
    success: bool
    error: str | None
    total_latency_ms: int | None
    tokens_in: int | None
    tokens_out: int | None
    total_cost_cents: int | None
    started_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class PipelineRunDetail(PipelineRunSummary):
    """Detailed pipeline run with events."""

    topology: str | None
    ttft_ms: int | None
    ttfa_ms: int | None
    stages: dict[str, Any]
    run_metadata: dict[str, Any]
    events: list[dict[str, Any]]


class PipelineEvent(BaseModel):
    """Pipeline event."""

    id: UUID
    event_type: str
    event_data: dict[str, Any]
    occurred_at: datetime

    class Config:
        from_attributes = True


class ProviderCallSummary(BaseModel):
    """Summary of a provider call."""

    id: UUID
    service: str
    operation: str
    provider: str
    model_id: str | None
    success: bool
    latency_ms: int | None
    tokens_in: int | None
    tokens_out: int | None
    cost_cents: int | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class DLQEntry(BaseModel):
    """Dead letter queue entry."""

    id: UUID
    pipeline_run_id: UUID | None
    error_type: str
    error_message: str | None
    failed_stage: str | None
    status: str
    retry_count: int
    max_retries: int
    created_at: datetime
    next_retry_at: datetime | None

    class Config:
        from_attributes = True


class PulseStats(BaseModel):
    """Aggregate pulse statistics."""

    total_pipeline_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_latency_ms: float | None
    total_tokens_in: int
    total_tokens_out: int
    total_cost_cents: int
    dlq_pending_count: int


class TimeSeriesPoint(BaseModel):
    """Time series data point."""

    timestamp: datetime
    value: float


# Endpoints
@router.get("/stats", response_model=PulseStats)
async def get_pulse_stats(
    hours: int = Query(24, ge=1, le=168),
    org_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> PulseStats:
    """Get aggregate statistics for the time period."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    # Base query conditions
    conditions = [PipelineRunModel.started_at >= since]
    if org_id:
        conditions.append(PipelineRunModel.org_id == org_id)

    # Total runs
    total_stmt = select(func.count(PipelineRunModel.id)).where(*conditions)
    total_result = await db.execute(total_stmt)
    total_runs = total_result.scalar() or 0

    # Successful runs
    success_stmt = select(func.count(PipelineRunModel.id)).where(
        *conditions, PipelineRunModel.success == True  # noqa: E712
    )
    success_result = await db.execute(success_stmt)
    successful_runs = success_result.scalar() or 0

    # Failed runs
    failed_runs = total_runs - successful_runs

    # Success rate
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0

    # Average latency
    latency_stmt = select(func.avg(PipelineRunModel.total_latency_ms)).where(
        *conditions, PipelineRunModel.total_latency_ms.is_not(None)
    )
    latency_result = await db.execute(latency_stmt)
    avg_latency = latency_result.scalar()

    # Token totals
    tokens_stmt = select(
        func.coalesce(func.sum(PipelineRunModel.tokens_in), 0),
        func.coalesce(func.sum(PipelineRunModel.tokens_out), 0),
    ).where(*conditions)
    tokens_result = await db.execute(tokens_stmt)
    tokens_row = tokens_result.one()
    total_tokens_in = tokens_row[0] or 0
    total_tokens_out = tokens_row[1] or 0

    # Cost total
    cost_stmt = select(
        func.coalesce(func.sum(PipelineRunModel.total_cost_cents), 0)
    ).where(*conditions)
    cost_result = await db.execute(cost_stmt)
    total_cost = cost_result.scalar() or 0

    # DLQ pending count
    dlq_stmt = select(func.count(DeadLetterQueueModel.id)).where(
        DeadLetterQueueModel.status == "pending"
    )
    if org_id:
        dlq_stmt = dlq_stmt.where(DeadLetterQueueModel.org_id == org_id)
    dlq_result = await db.execute(dlq_stmt)
    dlq_count = dlq_result.scalar() or 0

    return PulseStats(
        total_pipeline_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        avg_latency_ms=float(avg_latency) if avg_latency else None,
        total_tokens_in=total_tokens_in,
        total_tokens_out=total_tokens_out,
        total_cost_cents=total_cost,
        dlq_pending_count=dlq_count,
    )


@router.get("/pipeline-runs", response_model=list[PipelineRunSummary])
async def list_pipeline_runs(
    hours: int = Query(24, ge=1, le=168),
    service: str | None = None,
    success: bool | None = None,
    org_id: UUID | None = None,
    session_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> list[PipelineRunSummary]:
    """List pipeline runs with filters."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    stmt = select(PipelineRunModel).where(PipelineRunModel.started_at >= since)

    if service:
        stmt = stmt.where(PipelineRunModel.service == service)
    if success is not None:
        stmt = stmt.where(PipelineRunModel.success == success)
    if org_id:
        stmt = stmt.where(PipelineRunModel.org_id == org_id)
    if session_id:
        stmt = stmt.where(PipelineRunModel.session_id == session_id)

    stmt = stmt.order_by(PipelineRunModel.started_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    runs = result.scalars().all()

    return [PipelineRunSummary.model_validate(run) for run in runs]


@router.get("/pipeline-runs/{run_id}", response_model=PipelineRunDetail)
async def get_pipeline_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> PipelineRunDetail:
    """Get detailed pipeline run with events."""
    stmt = select(PipelineRunModel).where(PipelineRunModel.id == run_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Pipeline run not found")

    # Get events
    events_stmt = (
        select(PipelineEventModel)
        .where(PipelineEventModel.pipeline_run_id == run_id)
        .order_by(PipelineEventModel.occurred_at)
    )
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    event_dicts = [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "event_data": e.event_data,
            "occurred_at": e.occurred_at.isoformat(),
        }
        for e in events
    ]

    return PipelineRunDetail(
        id=run.id,
        service=run.service,
        topology=run.topology,
        request_id=run.request_id,
        session_id=run.session_id,
        user_id=run.user_id,
        org_id=run.org_id,
        success=run.success,
        error=run.error,
        total_latency_ms=run.total_latency_ms,
        ttft_ms=run.ttft_ms,
        ttfa_ms=run.ttfa_ms,
        tokens_in=run.tokens_in,
        tokens_out=run.tokens_out,
        total_cost_cents=run.total_cost_cents,
        stages=run.stages or {},
        run_metadata=run.run_metadata or {},
        events=event_dicts,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("/provider-calls", response_model=list[ProviderCallSummary])
async def list_provider_calls(
    hours: int = Query(24, ge=1, le=168),
    provider: str | None = None,
    operation: str | None = None,
    success: bool | None = None,
    org_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> list[ProviderCallSummary]:
    """List provider calls with filters."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    stmt = select(ProviderCallModel).where(ProviderCallModel.started_at >= since)

    if provider:
        stmt = stmt.where(ProviderCallModel.provider == provider)
    if operation:
        stmt = stmt.where(ProviderCallModel.operation == operation)
    if success is not None:
        stmt = stmt.where(ProviderCallModel.success == success)
    if org_id:
        stmt = stmt.where(ProviderCallModel.org_id == org_id)

    stmt = stmt.order_by(ProviderCallModel.started_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    calls = result.scalars().all()

    return [ProviderCallSummary.model_validate(call) for call in calls]


@router.get("/dlq", response_model=list[DLQEntry])
async def list_dlq_entries(
    status: str = Query("pending", regex="^(pending|retrying|resolved|failed)$"),
    org_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> list[DLQEntry]:
    """List dead letter queue entries."""
    stmt = select(DeadLetterQueueModel).where(DeadLetterQueueModel.status == status)

    if org_id:
        stmt = stmt.where(DeadLetterQueueModel.org_id == org_id)

    stmt = stmt.order_by(DeadLetterQueueModel.created_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    return [DLQEntry.model_validate(entry) for entry in entries]


@router.get("/latency-series", response_model=list[TimeSeriesPoint])
async def get_latency_time_series(
    hours: int = Query(24, ge=1, le=168),
    service: str | None = None,
    org_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext | None = Depends(get_optional_auth),
) -> list[TimeSeriesPoint]:
    """Get latency time series data (hourly buckets)."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    # Build conditions
    conditions = [
        PipelineRunModel.started_at >= since,
        PipelineRunModel.total_latency_ms.is_not(None),
    ]
    if service:
        conditions.append(PipelineRunModel.service == service)
    if org_id:
        conditions.append(PipelineRunModel.org_id == org_id)

    # Group by hour
    stmt = (
        select(
            func.date_trunc("hour", PipelineRunModel.started_at).label("bucket"),
            func.avg(PipelineRunModel.total_latency_ms).label("avg_latency"),
        )
        .where(*conditions)
        .group_by("bucket")
        .order_by("bucket")
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        TimeSeriesPoint(timestamp=row.bucket, value=float(row.avg_latency))
        for row in rows
    ]
