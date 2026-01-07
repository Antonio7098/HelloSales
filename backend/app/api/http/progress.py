"""HTTP endpoints for progress dashboard data."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.http.dependencies import get_current_user
from app.database import get_session
from app.domains.assessment.progress import ProgressService
from app.models import User
from app.schemas.assessment import AssessmentResponse
from app.schemas.progress import SessionHistoryItem, SkillProgressResponse

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("/skills", response_model=list[SkillProgressResponse])
async def get_skill_progress(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SkillProgressResponse]:
    service = ProgressService(session)
    return await service.get_skill_progress(user.id)


@router.get("/sessions", response_model=list[SessionHistoryItem])
async def get_session_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
) -> list[SessionHistoryItem]:
    service = ProgressService(session)
    return await service.get_session_history(user.id, limit=limit)


@router.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment_details(
    assessment_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AssessmentResponse:
    service = ProgressService(session)
    details = await service.get_assessment_details(user_id=user.id, assessment_id=assessment_id)
    if details is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return details
