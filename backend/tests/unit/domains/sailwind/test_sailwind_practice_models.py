import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Client, Organization, OrganizationMembership, Product, RepAssignment, User


@pytest.mark.asyncio
async def test_rep_assignment_unique_per_org_user_product_client(db_session):
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

    membership = OrganizationMembership(user_id=user.id, organization_id=org.id, role="rep")
    db_session.add(membership)

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    a1 = RepAssignment(
        organization_id=org.id,
        user_id=user.id,
        product_id=product.id,
        client_id=client.id,
        strategy_id=None,
        min_practice_minutes=10,
    )
    db_session.add(a1)
    await db_session.commit()

    a2 = RepAssignment(
        organization_id=org.id,
        user_id=user.id,
        product_id=product.id,
        client_id=client.id,
        strategy_id=None,
        min_practice_minutes=5,
    )
    db_session.add(a2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
