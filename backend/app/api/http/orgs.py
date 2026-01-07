"""HTTP endpoints for organization context."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.http.dependencies import EnterpriseOrgContext, get_enterprise_org_context
from app.schemas.organization import OrganizationMembershipMeResponse, OrganizationMeResponse

router = APIRouter(prefix="/api/v1/orgs", tags=["orgs"])


@router.get("/me", response_model=OrganizationMeResponse)
async def get_current_org(
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
) -> OrganizationMeResponse:
    org = org_context.organization
    return OrganizationMeResponse(
        organization_id=org.id,
        workos_org_id=org.workos_org_id,
        name=org.name,
    )


@router.get("/me/memberships", response_model=OrganizationMembershipMeResponse)
async def get_my_membership(
    org_context: EnterpriseOrgContext = Depends(get_enterprise_org_context),
) -> OrganizationMembershipMeResponse:
    membership = org_context.membership
    return OrganizationMembershipMeResponse(
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        role=membership.role,
        permissions=membership.permissions,
        created_at=membership.created_at,
    )
