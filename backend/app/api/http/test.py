from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.providers.factory import get_llm_provider
from app.config import get_settings
from app.database import get_session_context
from app.domains.assessment.service import AssessmentService
from app.domains.assessment.triage import TriageService
from app.domains.skills.service import SkillService
from app.models.session import Session
from app.schemas.assessment import AssessmentResponse, TriageRequest, TriageResponse
from app.schemas.skill import SkillResponse, TrackedSkillResponse

router = APIRouter(tags=["test"], prefix="/api/v1/test")


class AssessmentTestRequest(BaseModel):
    session_id: UUID
    user_response: str
    skill_ids: list[UUID]


@router.post("/triage", response_model=TriageResponse)
async def test_triage(payload: TriageRequest) -> TriageResponse:
    settings = get_settings()
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")

    async with get_session_context() as db:
        service = TriageService(db, llm_provider=get_llm_provider())
        return await service.classify_response(payload)


@router.post("/assess", response_model=AssessmentResponse)
async def test_assess(payload: AssessmentTestRequest) -> AssessmentResponse:
    settings = get_settings()
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")

    async with get_session_context() as db:
        result = await db.execute(select(Session).where(Session.id == payload.session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=400, detail="Session not found")

        service = AssessmentService(db, llm_provider=get_llm_provider())
        return await service.assess_response(
            user_id=session.user_id,
            session_id=session.id,
            interaction_id=None,
            user_response=payload.user_response,
            skill_ids=payload.skill_ids,
            send_status=None,
            triage_decision=None,
        )


@router.get("/skills", response_model=list[SkillResponse])
async def test_list_skills(user_id: UUID) -> list[SkillResponse]:
    settings = get_settings()
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")

    async with get_session_context() as db:
        service = SkillService(db)
        return await service.list_skills(user_id)


@router.get("/skills/tracked", response_model=list[TrackedSkillResponse])
async def test_tracked_skills(user_id: UUID) -> list[TrackedSkillResponse]:
    settings = get_settings()
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")

    async with get_session_context() as db:
        service = SkillService(db)
        return await service.get_tracked_skills(user_id)
