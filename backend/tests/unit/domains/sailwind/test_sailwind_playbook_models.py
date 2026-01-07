import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Client, Organization, Product, Strategy


@pytest.mark.asyncio
async def test_strategy_unique_per_org_product_client(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    s1 = Strategy(
        organization_id=org.id,
        product_id=product.id,
        client_id=client.id,
        status="draft",
        strategy_text="Try value-based framing",
    )
    db_session.add(s1)
    await db_session.commit()

    s2 = Strategy(
        organization_id=org.id,
        product_id=product.id,
        client_id=client.id,
        status="draft",
        strategy_text="Duplicate",
    )
    db_session.add(s2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
