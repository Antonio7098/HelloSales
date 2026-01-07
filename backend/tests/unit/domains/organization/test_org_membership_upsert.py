import uuid

import pytest

from app.domains.organization.service import OrganizationService
from app.models import Organization, User


@pytest.mark.asyncio
async def test_ensure_membership_updates_role_and_permissions(db_session):
    subject = f"test_{uuid.uuid4()}"
    user = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(user)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    service = OrganizationService(db_session)

    await service.ensure_membership(
        user_id=user.id,
        organization_id=org.id,
        role="rep",
        permissions={"can_view": True},
    )

    updated = await service.ensure_membership(
        user_id=user.id,
        organization_id=org.id,
        role="admin",
        permissions={"can_export": True},
    )

    assert updated.role == "admin"
    assert updated.permissions == {"can_export": True}


@pytest.mark.asyncio
async def test_ensure_membership_does_not_clear_fields_when_claims_missing(db_session):
    subject = f"test_{uuid.uuid4()}"
    user = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(user)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    service = OrganizationService(db_session)

    created = await service.ensure_membership(
        user_id=user.id,
        organization_id=org.id,
        role="admin",
        permissions={"can_export": True},
    )

    unchanged = await service.ensure_membership(
        user_id=user.id,
        organization_id=org.id,
        role=None,
        permissions=None,
    )

    assert unchanged.user_id == created.user_id
    assert unchanged.organization_id == created.organization_id
    assert unchanged.role == "admin"
    assert unchanged.permissions == {"can_export": True}
