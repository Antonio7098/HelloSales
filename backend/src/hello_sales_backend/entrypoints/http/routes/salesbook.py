"""Salesbook HTTP routes — onboarding, pipeline, engagement, team, exhaustive view.

/Oliviercontribution. Mirrors the entrypoints/http/routes/company_profile.py shape:
each handler is async, depends on get_salesbook_service, returns ApiEnvelope via
ok_response, and is gated by require_permissions(...).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from hello_sales_backend.entrypoints.http.dependencies import (
    get_salesbook_service,
    require_permissions,
)
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.salesbook import (
    COMMENT_APPROVE_PERMISSION,
    COMMENT_WRITE_PERMISSION,
    ENGAGEMENT_READ_PERMISSION,
    ENGAGEMENT_WRITE_PERMISSION,
    ONBOARDING_READ_PERMISSION,
    ONBOARDING_WRITE_PERMISSION,
    PIN_READ_PERMISSION,
    PIN_WRITE_PERMISSION,
    PIPELINE_READ_PERMISSION,
    PIPELINE_WRITE_PERMISSION,
    SALESBOOK_READ_PERMISSION,
    TEAM_READ_PERMISSION,
    TEAM_WRITE_PERMISSION,
    ClientContactUpsertRequest,
    EngagementLogCreateRequest,
    OnboardingBatchSubmit,
    OnboardingResponseSubmit,
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
    SalesbookCommentApproveRequest,
    SalesbookCommentCreateRequest,
    SalesbookPinRequest,
    SalesbookService,
    TeamMembershipCreateRequest,
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
CommentWriteDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, COMMENT_WRITE_PERMISSION))]
CommentApproveDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, COMMENT_APPROVE_PERMISSION))]
PinReadDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, PIN_READ_PERMISSION))]
PinWriteDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, PIN_WRITE_PERMISSION))]


# ────────────────────────────────────────────────────────────────────────────
# Client contact extension (sibling of company_profile)
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/contact", response_model=ApiEnvelope)
async def get_client_contact(
    profile_id: str,
    request: Request,
    _auth: OnboardingReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.get_client_contact(
            profile_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.put("/clients/{profile_id}/contact", response_model=ApiEnvelope)
async def upsert_client_contact(
    profile_id: str,
    http_request: Request,
    body: ClientContactUpsertRequest,
    _auth: OnboardingWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.upsert_client_contact(
            profile_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


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
    request: Request,
    _auth: OnboardingReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.get_onboarding_progress(
            profile_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.get("/clients/{profile_id}/onboarding/responses", response_model=ApiEnvelope)
async def list_onboarding_responses(
    profile_id: str,
    request: Request,
    _auth: OnboardingReadDep,
    phase: int | None = Query(default=None, ge=1, le=3),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.list_responses(
            profile_id,
            phase=phase,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.post("/clients/{profile_id}/onboarding/responses", response_model=ApiEnvelope)
async def submit_onboarding_response(
    profile_id: str,
    http_request: Request,
    body: OnboardingResponseSubmit,
    _auth: OnboardingWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.submit_response(
            profile_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


@router.post("/clients/{profile_id}/onboarding/batch", response_model=ApiEnvelope)
async def submit_onboarding_batch(
    profile_id: str,
    http_request: Request,
    body: OnboardingBatchSubmit,
    _auth: OnboardingWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.submit_batch(
            profile_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


# ────────────────────────────────────────────────────────────────────────────
# Salesbook exhaustive view (drives the searchable frontend viewer)
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/salesbook", response_model=ApiEnvelope)
async def get_salesbook_exhaustive(
    profile_id: str,
    request: Request,
    _auth: SalesbookReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.get_exhaustive_view(
            profile_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


# ────────────────────────────────────────────────────────────────────────────
# Pipeline
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/pipeline", response_model=ApiEnvelope)
async def list_deals(
    profile_id: str,
    request: Request,
    _auth: PipelineReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.list_deals(
            profile_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.post("/clients/{profile_id}/pipeline", response_model=ApiEnvelope)
async def create_deal(
    profile_id: str,
    http_request: Request,
    body: PipelineDealCreateRequest,
    _auth: PipelineWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.create_deal(
            profile_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


@router.patch("/pipeline/{deal_id}", response_model=ApiEnvelope)
async def update_deal(
    deal_id: str,
    http_request: Request,
    body: PipelineDealUpdateRequest,
    _auth: PipelineWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.update_deal(
            deal_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


# ────────────────────────────────────────────────────────────────────────────
# Engagement log
# ────────────────────────────────────────────────────────────────────────────


@router.post("/engagement-log", response_model=ApiEnvelope)
async def log_engagement(
    http_request: Request,
    body: EngagementLogCreateRequest,
    _auth: EngagementWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.log_engagement(
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


@router.get("/clients/{profile_id}/engagement-log", response_model=ApiEnvelope)
async def list_engagements_for_profile(
    profile_id: str,
    request: Request,
    _auth: EngagementReadDep,
    deal_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.list_engagements(
            profile_id,
            deal_id=deal_id,
            limit=limit,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.get("/engagement-log/all", response_model=ApiEnvelope)
async def list_all_engagements(
    request: Request,
    _auth: ExecReadDep,
    limit: int = Query(default=200, ge=1, le=1000),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.list_all_engagements(
            limit=limit,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


# ────────────────────────────────────────────────────────────────────────────
# Team
# ────────────────────────────────────────────────────────────────────────────


@router.get("/clients/{profile_id}/team", response_model=ApiEnvelope)
async def list_team(
    profile_id: str,
    request: Request,
    _auth: TeamReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.list_team(
            profile_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.post("/clients/{profile_id}/team", response_model=ApiEnvelope)
async def add_team_member(
    profile_id: str,
    http_request: Request,
    body: TeamMembershipCreateRequest,
    _auth: TeamWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.add_team_member(
            profile_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


@router.delete("/team/{membership_id}", response_model=ApiEnvelope)
async def remove_team_member(
    membership_id: str,
    request: Request,
    _auth: TeamWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    await service.remove_team_member(
        membership_id,
        request_id=getattr(request.state, "request_id", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return ok_response({"removed": True, "membership_id": membership_id})


# ────────────────────────────────────────────────────────────────────────────
# Moderation — comments + pins (admin moderates rep contributions)
# ────────────────────────────────────────────────────────────────────────────


@router.post("/clients/{profile_id}/comments", response_model=ApiEnvelope)
async def add_comment(
    profile_id: str,
    http_request: Request,
    body: SalesbookCommentCreateRequest,
    _auth: CommentWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.add_comment(
            profile_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


@router.get("/clients/{profile_id}/comments", response_model=ApiEnvelope)
async def list_comments(
    profile_id: str,
    request: Request,
    _auth: SalesbookReadDep,
    status: str | None = Query(default=None, pattern=r"^(pending|approved|rejected)$"),
    target_id: str | None = Query(default=None),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.list_comments(
            profile_id,
            status=status,
            target_id=target_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.patch("/comments/{comment_id}/review", response_model=ApiEnvelope)
async def review_comment(
    comment_id: str,
    http_request: Request,
    body: SalesbookCommentApproveRequest,
    _auth: CommentApproveDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.review_comment(
            comment_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


@router.get("/clients/{profile_id}/pins", response_model=ApiEnvelope)
async def list_pins(
    profile_id: str,
    request: Request,
    _auth: PinReadDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.list_pins(
            profile_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
        )
    )


@router.post("/clients/{profile_id}/pins", response_model=ApiEnvelope)
async def pin_entry(
    profile_id: str,
    http_request: Request,
    body: SalesbookPinRequest,
    _auth: PinWriteDep,
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    return ok_response(
        await service.pin_entry(
            profile_id,
            body,
            request_id=getattr(http_request.state, "request_id", None),
            trace_id=getattr(http_request.state, "trace_id", None),
        )
    )


@router.delete("/clients/{profile_id}/pins", response_model=ApiEnvelope)
async def unpin_entry(
    profile_id: str,
    request: Request,
    _auth: PinWriteDep,
    target_type: str = Query(..., min_length=1),
    target_id: str = Query(..., min_length=1),
    service: SalesbookService = Depends(get_salesbook_service),
) -> ApiEnvelope:
    await service.unpin_entry(
        profile_id,
        target_type,
        target_id,
        request_id=getattr(request.state, "request_id", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return ok_response({"removed": True, "target_type": target_type, "target_id": target_id})
