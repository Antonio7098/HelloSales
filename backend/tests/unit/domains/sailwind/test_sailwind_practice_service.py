import uuid

import pytest

from app.domains.sailwind.practice import (
    PracticeConflictError,
    PracticeNotFoundError,
    PracticeSessionService,
    PracticeValidationError,
    TerritoryService,
)
from app.models import (
    Client,
    Organization,
    OrganizationMembership,
    Product,
    Strategy,
    User,
)


@pytest.mark.asyncio
async def test_create_rep_assignment_denies_non_member(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    service = TerritoryService(db_session)

    with pytest.raises(PracticeNotFoundError):
        await service.create_rep_assignment(
            organization_id=org.id,
            user_id=rep.id,
            product_id=product.id,
            client_id=client.id,
            strategy_id=None,
            min_practice_minutes=None,
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_rep_assignment_denies_negative_minutes(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(user_id=rep.id, organization_id=org.id, role="rep")
    db_session.add(membership)

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    service = TerritoryService(db_session)

    with pytest.raises(PracticeValidationError):
        await service.create_rep_assignment(
            organization_id=org.id,
            user_id=rep.id,
            product_id=product.id,
            client_id=client.id,
            strategy_id=None,
            min_practice_minutes=-1,
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_rep_assignment_denies_strategy_mismatch(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(user_id=rep.id, organization_id=org.id, role="rep")
    db_session.add(membership)

    product_a = Product(organization_id=org.id, name="Widget")
    client_a = Client(organization_id=org.id, name="Globex", industry=None)
    product_b = Product(organization_id=org.id, name="Gadget")
    client_b = Client(organization_id=org.id, name="Initech", industry=None)
    db_session.add_all([product_a, client_a, product_b, client_b])
    await db_session.flush()

    strategy = Strategy(
        organization_id=org.id,
        product_id=product_b.id,
        client_id=client_b.id,
        status="active",
        strategy_text="Do the thing",
    )
    db_session.add(strategy)
    await db_session.flush()

    service = TerritoryService(db_session)

    with pytest.raises(PracticeValidationError):
        await service.create_rep_assignment(
            organization_id=org.id,
            user_id=rep.id,
            product_id=product_a.id,
            client_id=client_a.id,
            strategy_id=strategy.id,
            min_practice_minutes=10,
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_rep_assignment_conflicts_on_duplicate(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(user_id=rep.id, organization_id=org.id, role="rep")
    db_session.add(membership)

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    service = TerritoryService(db_session)

    await service.create_rep_assignment(
        organization_id=org.id,
        user_id=rep.id,
        product_id=product.id,
        client_id=client.id,
        strategy_id=None,
        min_practice_minutes=10,
        actor_user_id=uuid.uuid4(),
    )

    with pytest.raises(PracticeConflictError):
        await service.create_rep_assignment(
            organization_id=org.id,
            user_id=rep.id,
            product_id=product.id,
            client_id=client.id,
            strategy_id=None,
            min_practice_minutes=10,
            actor_user_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_start_practice_session_denies_missing_strategy(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(user_id=rep.id, organization_id=org.id, role="rep")
    db_session.add(membership)

    service = PracticeSessionService(db_session)

    with pytest.raises(PracticeNotFoundError):
        await service.start_practice_session(
            organization_id=org.id,
            user_id=rep.id,
            strategy_id=uuid.uuid4(),
            rep_assignment_id=None,
            actor_user_id=rep.id,
        )


@pytest.mark.asyncio
async def test_start_practice_session_denies_non_member(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    strategy = Strategy(
        organization_id=org.id,
        product_id=product.id,
        client_id=client.id,
        status="active",
        strategy_text="Hello",
    )
    db_session.add(strategy)
    await db_session.flush()

    service = PracticeSessionService(db_session)

    with pytest.raises(PracticeNotFoundError):
        await service.start_practice_session(
            organization_id=org.id,
            user_id=rep.id,
            strategy_id=strategy.id,
            rep_assignment_id=None,
            actor_user_id=rep.id,
        )


@pytest.mark.asyncio
async def test_start_practice_session_denies_mismatched_rep_assignment(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(user_id=rep.id, organization_id=org.id, role="rep")
    db_session.add(membership)

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    other_product = Product(organization_id=org.id, name="Gadget")
    other_client = Client(organization_id=org.id, name="Initech", industry=None)
    db_session.add_all([product, client, other_product, other_client])
    await db_session.flush()

    strategy = Strategy(
        organization_id=org.id,
        product_id=product.id,
        client_id=client.id,
        status="active",
        strategy_text="Hello",
    )
    pinned_strategy = Strategy(
        organization_id=org.id,
        product_id=other_product.id,
        client_id=other_client.id,
        status="active",
        strategy_text="Pinned",
    )
    db_session.add_all([strategy, pinned_strategy])
    await db_session.flush()

    territory_service = TerritoryService(db_session)
    assignment = await territory_service.create_rep_assignment(
        organization_id=org.id,
        user_id=rep.id,
        product_id=other_product.id,
        client_id=other_client.id,
        strategy_id=pinned_strategy.id,
        min_practice_minutes=None,
        actor_user_id=uuid.uuid4(),
    )

    practice_service = PracticeSessionService(db_session)

    with pytest.raises(PracticeValidationError):
        await practice_service.start_practice_session(
            organization_id=org.id,
            user_id=rep.id,
            strategy_id=strategy.id,
            rep_assignment_id=assignment.id,
            actor_user_id=rep.id,
        )


@pytest.mark.asyncio
async def test_start_practice_session_creates_chat_session(db_session):
    subject = f"test_{uuid.uuid4()}"
    rep = User(
        auth_provider="clerk",
        auth_subject=subject,
        clerk_id=subject,
    )
    db_session.add(rep)

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name="Acme")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(user_id=rep.id, organization_id=org.id, role="rep")
    db_session.add(membership)

    product = Product(organization_id=org.id, name="Widget")
    client = Client(organization_id=org.id, name="Globex", industry=None)
    db_session.add_all([product, client])
    await db_session.flush()

    strategy = Strategy(
        organization_id=org.id,
        product_id=product.id,
        client_id=client.id,
        status="active",
        strategy_text="Hello",
    )
    db_session.add(strategy)
    await db_session.flush()

    practice_service = PracticeSessionService(db_session)
    created = await practice_service.start_practice_session(
        organization_id=org.id,
        user_id=rep.id,
        strategy_id=strategy.id,
        rep_assignment_id=None,
        actor_user_id=rep.id,
    )

    assert created.chat_session_id is not None
    assert created.organization_id == org.id
    assert created.user_id == rep.id
    assert created.strategy_id == strategy.id
    assert created.status == "active"
