"""Common HTTP dependencies (auth, current user) - Enterprise Edition (WorkOS only)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import IdentityTokenError, verify_identity_token
from app.database import get_session
from app.domains.organization.service import OrganizationService
from app.logging_config import set_request_context
from app.models import Organization, OrganizationMembership, User

logger = logging.getLogger("auth")


async def get_identity_claims(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Extract and verify identity from WorkOS JWT token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    try:
        return await verify_identity_token(token)
    except IdentityTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    identity=Depends(get_identity_claims),
) -> User:
    """Resolve the current authenticated user from a WorkOS JWT.

    Expects an ``Authorization: Bearer <token>`` header.
    Users must belong to a WorkOS organization to access the enterprise backend.
    """

    subject = identity.subject
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    email = identity.email

    # Find or create the user record (WorkOS only)
    result = await session.execute(
        select(User).where(User.auth_subject == subject)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            auth_provider="workos",
            auth_subject=subject,
            email=email,
            display_name=email.split("@")[0] if email else None,
        )
        session.add(user)
        await session.flush()

    # Enterprise: org_id is required from WorkOS token
    if not identity.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization context required for enterprise access",
        )

    workos_org_id = str(identity.org_id)

    raw_claims = getattr(identity, "raw_claims", None) or {}
    role_raw = raw_claims.get("role")
    role = str(role_raw) if role_raw is not None else None
    permissions_raw = raw_claims.get("permissions")
    permissions = permissions_raw if isinstance(permissions_raw, dict) else None

    logger.info(
        "Enterprise tenancy bootstrap started",
        extra={
            "service": "auth",
            "operation": "org.bootstrap",
            "status": "started",
            "user_id": str(user.id),
            "org_id": workos_org_id,
        },
    )

    org_service = OrganizationService(session)
    org = await org_service.upsert_organization(
        org_id=workos_org_id,
        user_id=user.id,
    )
    await org_service.ensure_membership(
        user_id=user.id,
        organization_id=org.id,
        role=role,
        permissions=permissions,
    )

    set_request_context(
        user_id=str(user.id),
        org_id=str(org.id),
    )

    # Update email if it changed
    if email and user.email != email:
        user.email = email

    return user


@dataclass(frozen=True)
class EnterpriseOrgContext:
    """Organization context for enterprise users."""
    organization: Organization
    membership: OrganizationMembership


async def get_enterprise_org_context(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    identity=Depends(get_identity_claims),
) -> EnterpriseOrgContext:
    """Get organization context for the current user.

    Enterprise users must belong to an organization.
    """
    if not identity.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization context required",
        )

    org_id = str(identity.org_id)
    result = await session.execute(
        select(Organization).where(Organization.org_id == org_id)
    )
    organization = result.scalar_one_or_none()
    if organization is None:
        service = OrganizationService(session)
        organization = await service.upsert_organization(
            org_id=org_id,
            user_id=user.id,
        )

    membership = await session.get(
        OrganizationMembership,
        {"user_id": user.id, "organization_id": organization.id},
    )
    if membership is None:
        service = OrganizationService(session)
        membership = await service.ensure_membership(
            user_id=user.id,
            organization_id=organization.id,
        )

    return EnterpriseOrgContext(organization=organization, membership=membership)
