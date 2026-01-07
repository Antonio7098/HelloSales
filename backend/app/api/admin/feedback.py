"""Admin API for feedback management."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.dependencies import require_admin
from app.database import get_session
from app.domains.feedback.service import FeedbackService
from app.schemas.feedback import FeedbackEventRead, FeedbackListResponse

router = APIRouter()


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_all_feedback(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> FeedbackListResponse:
    """Return all feedback events (admin only)."""

    service = FeedbackService(session)
    events = await service.list_all_feedback(limit=limit, offset=offset)
    items = [FeedbackEventRead.model_validate(e) for e in events]
    return FeedbackListResponse(items=items, total=len(items))
