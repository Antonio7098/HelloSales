import uuid

import pytest

from app.ai.substrate import PipelineEventLogger
from app.ai.substrate.policy.gateway import (
    PolicyCheckpoint,
    PolicyContext,
    PolicyDecision,
    PolicyGateway,
)
from app.config import get_settings
from app.models import Organization, OrganizationMembership, Session, User


@pytest.mark.asyncio
async def test_workos_enabled_blocks_missing_membership(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    get_settings.cache_clear()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="workos", auth_subject=subject, clerk_id=None)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}")
    db_session.add(org)
    await db_session.flush()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()

    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service="chat",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org.id,
    )
    await db_session.commit()

    gateway = PolicyGateway()
    ctx = PolicyContext(
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org.id,
        service="chat",
        trigger=None,
        behavior=None,
        quality_mode=None,
        intent="chat",
    )
    result = await gateway.evaluate(checkpoint=PolicyCheckpoint.PRE_LLM, context=ctx)
    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "org_membership_missing"


@pytest.mark.asyncio
async def test_workos_enabled_allows_with_membership(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    get_settings.cache_clear()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="workos", auth_subject=subject, clerk_id=None)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    org = Organization(workos_org_id=f"org_{uuid.uuid4()}")
    db_session.add(org)
    await db_session.flush()

    membership = OrganizationMembership(user_id=user.id, organization_id=org.id, role="member")
    db_session.add(membership)
    await db_session.flush()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()

    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service="chat",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org.id,
    )
    await db_session.commit()

    gateway = PolicyGateway()
    ctx = PolicyContext(
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org.id,
        service="chat",
        trigger=None,
        behavior=None,
        quality_mode=None,
        intent="chat",
    )
    result = await gateway.evaluate(checkpoint=PolicyCheckpoint.PRE_LLM, context=ctx)
    assert result.decision == PolicyDecision.ALLOW
