"""HTTP endpoints for legal document configuration and acceptance."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.http.dependencies import get_current_user
from app.config import get_settings
from app.database import get_session
from app.models import User
from app.schemas.legal import LegalAcceptRequest, LegalConfigResponse, LegalPublicConfig

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])


@router.get("/public", response_model=LegalPublicConfig)
async def get_public_legal_config(request: Request) -> LegalPublicConfig:
    """Return public legal document configuration (no auth required)."""
    settings = get_settings()

    terms_url = settings.terms_url or str(request.url_for("terms_of_service_page"))
    privacy_url = settings.privacy_url or str(request.url_for("privacy_policy_page"))
    dpa_url = settings.dpa_url or str(request.url_for("data_processing_agreement_page"))
    return LegalPublicConfig(
        version=settings.legal_version,
        termsUrl=terms_url,
        privacyUrl=privacy_url,
        dpaUrl=dpa_url,
    )


@router.get("/config", response_model=LegalConfigResponse)
async def get_legal_config(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LegalConfigResponse:
    """Return legal configuration and the current user's acceptance status."""

    # Session dependency keeps the user instance bound for potential updates
    del session  # unused but retained for symmetry with /accept

    settings = get_settings()

    terms_url = settings.terms_url
    privacy_url = settings.privacy_url
    dpa_url = settings.dpa_url

    accepted_version = user.accepted_legal_version
    accepted_at = user.accepted_legal_at
    needs_acceptance = bool(settings.legal_version) and accepted_version != settings.legal_version

    return LegalConfigResponse(
        version=settings.legal_version,
        termsUrl=terms_url,
        privacyUrl=privacy_url,
        dpaUrl=dpa_url,
        acceptedVersion=accepted_version,
        acceptedAt=accepted_at,
        needsAcceptance=needs_acceptance,
    )


@router.post("/accept", response_model=LegalConfigResponse)
async def accept_legal(
    payload: LegalAcceptRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LegalConfigResponse:
    """Record that the current user has accepted the latest legal documents."""

    settings = get_settings()
    target_version = payload.version or settings.legal_version

    now = datetime.utcnow()
    user.accepted_legal_version = target_version
    user.accepted_legal_at = now

    session.add(user)

    needs_acceptance = bool(settings.legal_version) and target_version != settings.legal_version

    terms_url = settings.terms_url or str(request.url_for("terms_of_service_page"))
    privacy_url = settings.privacy_url or str(request.url_for("privacy_policy_page"))
    dpa_url = settings.dpa_url or str(request.url_for("data_processing_agreement_page"))

    return LegalConfigResponse(
        version=settings.legal_version,
        termsUrl=terms_url,
        privacyUrl=privacy_url,
        dpaUrl=dpa_url,
        acceptedVersion=user.accepted_legal_version,
        acceptedAt=user.accepted_legal_at,
        needsAcceptance=needs_acceptance,
    )
