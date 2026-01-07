import uuid
from datetime import datetime

import pytest

from app.domains.sailwind.playbook import (
    PlaybookConflictError,
    PlaybookNotFoundError,
    PlaybookService,
    PlaybookValidationError,
)
from app.models import Client, ClientArchetype, Organization, Product, ProductArchetype


@pytest.mark.asyncio
async def test_create_strategy_denies_invalid_status(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    service = PlaybookService(db_session)

    with pytest.raises(PlaybookValidationError):
        await service.create_strategy(
            organization_id=org.id,
            product_id=product.id,
            client_id=client.id,
            strategy_text="Hello",
            status="nope",
            user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_strategy_denies_cross_org_ids(db_session):
    org_a = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    org_b = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Beta")
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    product = Product(organization_id=org_a.id, name="Widget")
    client = Client(organization_id=org_b.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    service = PlaybookService(db_session)

    with pytest.raises(PlaybookNotFoundError):
        await service.create_strategy(
            organization_id=org_a.id,
            product_id=product.id,
            client_id=client.id,
            strategy_text="Hello",
            status="draft",
            user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_product_archetype_conflicts_on_duplicate_name(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    service = PlaybookService(db_session)

    await service.create_product_archetype(
        organization_id=org.id,
        name="Widget",
        user_id=uuid.uuid4(),
    )

    with pytest.raises(PlaybookConflictError):
        await service.create_product_archetype(
            organization_id=org.id,
            name="Widget",
            user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_product_denies_missing_archetype(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    service = PlaybookService(db_session)

    with pytest.raises(PlaybookNotFoundError):
        await service.create_product(
            organization_id=org.id,
            name="Widget",
            product_archetype_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_product_denies_archived_archetype(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    archetype = ProductArchetype(
        organization_id=org.id,
        name="Widget",
        archived_at=datetime.utcnow(),
    )
    db_session.add(archetype)
    await db_session.flush()

    service = PlaybookService(db_session)

    with pytest.raises(PlaybookValidationError):
        await service.create_product(
            organization_id=org.id,
            name="New Product",
            product_archetype_id=archetype.id,
            user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_update_product_can_set_and_clear_archetype(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    archetype = ProductArchetype(organization_id=org.id, name="Widget")
    product = Product(organization_id=org.id, name="Gadget")
    db_session.add_all([archetype, product])
    await db_session.flush()

    service = PlaybookService(db_session)

    updated = await service.update_product(
        organization_id=org.id,
        product_id=product.id,
        user_id=uuid.uuid4(),
        product_archetype_id=archetype.id,
        product_archetype_id_provided=True,
    )
    assert updated.product_archetype_id == archetype.id

    cleared = await service.update_product(
        organization_id=org.id,
        product_id=product.id,
        user_id=uuid.uuid4(),
        product_archetype_id=None,
        product_archetype_id_provided=True,
    )
    assert cleared.product_archetype_id is None


@pytest.mark.asyncio
async def test_create_client_denies_missing_archetype(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    service = PlaybookService(db_session)

    with pytest.raises(PlaybookNotFoundError):
        await service.create_client(
            organization_id=org.id,
            name="Globex",
            industry=None,
            client_archetype_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_client_denies_archived_archetype(db_session):
    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    archetype = ClientArchetype(
        organization_id=org.id,
        name="Enterprise",
        industry="Tech",
        archived_at=datetime.utcnow(),
    )
    db_session.add(archetype)
    await db_session.flush()

    service = PlaybookService(db_session)

    with pytest.raises(PlaybookValidationError):
        await service.create_client(
            organization_id=org.id,
            name="New Client",
            industry=None,
            client_archetype_id=archetype.id,
            user_id=uuid.uuid4(),
        )
