"""HTTP endpoints for feedback events (flags + reports)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.http.dependencies import get_current_user
from app.database import get_session
from app.domains.feedback.service import FeedbackService
from app.models import User
from app.schemas.feedback import (
    FeedbackEventRead,
    FeedbackListResponse,
    FeedbackMessageFlagCreate,
    FeedbackReportCreate,
)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("/message_flag", response_model=FeedbackEventRead)
async def create_feedback_message_flag(
    payload: FeedbackMessageFlagCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FeedbackEventRead:
    """Create a per-message feedback flag via HTTP.

    This mirrors the `feedback.message_flag` WebSocket handler but is useful
    for tools or future non-WS clients.
    """

    service = FeedbackService(session)
    event = await service.create_message_flag(user_id=user.id, data=payload)
    return FeedbackEventRead.model_validate(event)


@router.post("/report", response_model=FeedbackEventRead)
async def create_feedback_report(
    payload: FeedbackReportCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FeedbackEventRead:
    """Create a high-level feedback report via HTTP."""

    service = FeedbackService(session)
    event = await service.create_report(user_id=user.id, data=payload)
    return FeedbackEventRead.model_validate(event)


@router.get("", response_model=FeedbackListResponse)
async def list_recent_feedback(
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FeedbackListResponse:
    """Return recent feedback events for the current user."""

    service = FeedbackService(session)
    events = await service.list_recent_feedback(user_id=user.id, limit=limit)
    items = [FeedbackEventRead.model_validate(e) for e in events]
    return FeedbackListResponse(items=items, total=len(items))
