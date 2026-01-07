import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Organization, OrganizationMembership, User


@pytest.mark.asyncio
async def test_organization_workos_org_id_is_unique(db_session):
    subject = f"test_{uuid.uuid4()}"
    user = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(user)

    workos_org_id = f"org_{uuid.uuid4()}"
    org_1 = Organization(workos_org_id=workos_org_id, name="Acme")
    db_session.add(org_1)
    await db_session.commit()

    org_2 = Organization(workos_org_id=workos_org_id, name="Acme Duplicate")
    db_session.add(org_2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_organization_membership_pk_prevents_duplicates(db_session):
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

    membership_1 = OrganizationMembership(user_id=user.id, organization_id=org.id)
    db_session.add(membership_1)
    await db_session.commit()

    membership_2 = OrganizationMembership(user_id=user.id, organization_id=org.id)
    db_session.add(membership_2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
