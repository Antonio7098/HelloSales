"""Salesbook HTTP routes — onboarding, pipeline, engagement, team, exhaustive view.

/Oliviercontribution. Mirrors the entrypoints/http/routes/company_profile.py shape:
each handler is async, depends on get_salesbook_service, returns ApiEnvelope via
ok_response, and is gated by require_permissions(...).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from hello_sales_backend.entrypoints.http.dependencies import (
    get_salesbook_service,
    require_permissions,
)
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.salesbook import (
    ClientContactUpsertRequest,
    EngagementLogCreateRequest,
    OnboardingBatchSubmit,
    OnboardingResponseSubmit,
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
    SalesbookService,
    TeamMembershipCreateRequest,
)
from hello_sales_backend.modules.salesbook.permissions import (
    ENGAGEMENT_READ_PERMISSION,
    ENGAGEMENT_WRITE_PERMISSION,
    ONBOARDING_READ_PERMISSION,
    ONBOARDING_WRITE_PERMISSION,
    PIPELINE_READ_PERMISSION,
    PIPELINE_WRITE_PERMISSION,
    SALESBOOK_READ_PERMISSION,
    TEAM_READ_PERMISSION,
    TEAM_WRITE_PERMISSION,
)
from hello_sales_backend.shared.auth import APP_ACCESS_PERMISSION

router = APIRouter()


# Permission gates — re-used across handlers
OnboardingReadDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, ONBOARDING_READ_PERMISSION))]
OnboardingWriteDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, ONBOARDING_WRITE_PERMISSION))]
PipelineReadDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, PIPELINE_READ_PERMISSION))]
PipelineWriteDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, PIPELINE_WRITE_PERMISSION))]
EngagementReadDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, ENGAGEMENT_READ_PERMISSION))]
EngagementWriteDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, ENGAGEMENT_WRITE_PERMISSION))]
TeamReadDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, TEAM_READ_PERMISSION))]
TeamWriteDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, TEAM_WRITE_PERMISSION))]
SalesbookReadDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, SALESBOOK_READ_PERMISSION))]
ExecReadDep = Annotated[
    object,
    Depends(require_permissions(APP_ACCESS_PERMISSION, ENGAGEMENT_READ_PERMISSION, SALESBOOK_READ_PERMISSION)),
]


# ────────────────────────────────────────────────────────────────────────────
# Client contact extension (sibling of company_profile)
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/contact", response_model=ApiEnvelope)
async def get_client_contact(
    profile_id: str,
    _auth: OnboardingReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.get_client_contact(profile_id))


@router.put("/clients/{profile_id}/contact", response_model=ApiEnvelope)
async def upsert_client_contact(
    profile_id: str,
    request: ClientContactUpsertRequest,
    _auth: OnboardingWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.upsert_client_contact(profile_id, request))


# ────────────────────────────────────────────────────────────────────────────
# Onboarding
# ────────────────────────────────────────────────────────────────────────────


@router.get("/onboarding/registry", response_model=ApiEnvelope)
async def get_onboarding_registry(
    _auth: OnboardingReadDep,
    phase: int | None = Query(default=None, ge=1, le=3),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response({"questions": service.get_onboarding_registry(phase=phase)})


@router.get("/clients/{profile_id}/onboarding/progress", response_model=ApiEnvelope)
async def get_onboarding_progress(
    profile_id: str,
    _auth: OnboardingReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.get_onboarding_progress(profile_id))


@router.get("/clients/{profile_id}/onboarding/responses", response_model=ApiEnvelope)
async def list_onboarding_responses(
    profile_id: str,
    _auth: OnboardingReadDep,
    phase: int | None = Query(default=None, ge=1, le=3),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.list_responses(profile_id, phase=phase))


@router.post("/clients/{profile_id}/onboarding/responses", response_model=ApiEnvelope)
async def submit_onboarding_response(
    profile_id: str,
    request: OnboardingResponseSubmit,
    _auth: OnboardingWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.submit_response(profile_id, request))


@router.post("/clients/{profile_id}/onboarding/batch", response_model=ApiEnvelope)
async def submit_onboarding_batch(
    profile_id: str,
    request: OnboardingBatchSubmit,
    _auth: OnboardingWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.submit_batch(profile_id, request))


# ────────────────────────────────────────────────────────────────────────────
# Salesbook exhaustive view (drives the searchable frontend viewer)
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/salesbook", response_model=ApiEnvelope)
async def get_salesbook_exhaustive(
    profile_id: str,
    _auth: SalesbookReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.get_exhaustive_view(profile_id))


# ────────────────────────────────────────────────────────────────────────────
# Pipeline
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/pipeline", response_model=ApiEnvelope)
async def list_deals(
    profile_id: str,
    _auth: PipelineReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.list_deals(profile_id))


@router.post("/clients/{profile_id}/pipeline", response_model=ApiEnvelope)
async def create_deal(
    profile_id: str,
    request: PipelineDealCreateRequest,
    _auth: PipelineWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.create_deal(profile_id, request))


@router.patch("/pipeline/{deal_id}", response_model=ApiEnvelope)
async def update_deal(
    deal_id: str,
    request: PipelineDealUpdateRequest,
    _auth: PipelineWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.update_deal(deal_id, request))


# ────────────────────────────────────────────────────────────────────────────
# Engagement log
# ────────────────────────────────────────────────────────────────────────────


@router.post("/engagement-log", response_model=ApiEnvelope)
async def log_engagement(
    request: EngagementLogCreateRequest,
    _auth: EngagementWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.log_engagement(request))


@router.get("/clients/{profile_id}/engagement-log", response_model=ApiEnvelope)
async def list_engagements_for_profile(
    profile_id: str,
    _auth: EngagementReadDep,
    deal_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.list_engagements(profile_id, deal_id=deal_id, limit=limit))


@router.get("/engagement-log/all", response_model=ApiEnvelope)
async def list_all_engagements(
    _auth: ExecReadDep,
    limit: int = Query(default=200, ge=1, le=1000),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.list_all_engagements(limit=limit))


# ────────────────────────────────────────────────────────────────────────────
# Team
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/team", response_model=ApiEnvelope)
async def list_team(
    profile_id: str,
    _auth: TeamReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.list_team(profile_id))


@router.post("/clients/{profile_id}/team", response_model=ApiEnvelope)
async def add_team_member(
    profile_id: str,
    request: TeamMembershipCreateRequest,
    _auth: TeamWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(await service.add_team_member(profile_id, request))


@router.delete("/team/{membership_id}", response_model=ApiEnvelope)
async def remove_team_member(
    membership_id: str,
    _auth: TeamWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    await service.remove_team_member(membership_id)
    return ok_response({"removed": True, "membership_id": membership_id})
