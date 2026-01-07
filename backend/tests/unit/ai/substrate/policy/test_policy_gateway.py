import uuid

import pytest
from sqlalchemy import select

from app.ai.substrate import PipelineEventLogger
from app.ai.substrate.policy.gateway import (
    PolicyCheckpoint,
    PolicyContext,
    PolicyDecision,
    PolicyGateway,
)
from app.config import get_settings
from app.models import PipelineEvent, Session, User


async def _create_run(
    *,
    db_session,
    pipeline_run_id: uuid.UUID,
    request_id: uuid.UUID,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    service: str,
) -> None:
    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service=service,
        request_id=request_id,
        session_id=session_id,
        user_id=user_id,
        org_id=org_id,
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_policy_allowlist_blocks_unknown_intent(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("POLICY_ALLOWLIST_ENABLED", "true")
    monkeypatch.setenv("POLICY_ALLOWLIST_PRE_LLM", "chat")
    get_settings.cache_clear()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="clerk", auth_subject=subject, clerk_id=subject)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()
    org_id = uuid.uuid4()

    await _create_run(
        db_session=db_session,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
    )

    gateway = PolicyGateway()
    ctx = PolicyContext(
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
        trigger=None,
        behavior=None,
        quality_mode=None,
        intent="voice",
    )
    result = await gateway.evaluate(checkpoint=PolicyCheckpoint.PRE_LLM, context=ctx)
    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "intent_not_allowed"

    events = list(
        (
            await db_session.execute(
                select(PipelineEvent).where(PipelineEvent.pipeline_run_id == pipeline_run_id)
            )
        )
        .scalars()
        .all()
    )
    event_types = {e.type for e in events}
    assert "policy.decision" in event_types
    assert "policy.intent.denied" in event_types


@pytest.mark.asyncio
async def test_policy_prompt_token_budget_blocks(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("POLICY_MAX_PROMPT_TOKENS", "10")
    get_settings.cache_clear()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="clerk", auth_subject=subject, clerk_id=subject)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()
    org_id = uuid.uuid4()

    await _create_run(
        db_session=db_session,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
    )

    gateway = PolicyGateway()
    ctx = PolicyContext(
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
        trigger=None,
        behavior=None,
        quality_mode=None,
        intent="chat",
        prompt_tokens_estimate=999,
    )
    result = await gateway.evaluate(checkpoint=PolicyCheckpoint.PRE_LLM, context=ctx)
    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "budget.prompt_tokens_exceeded"

    events = list(
        (
            await db_session.execute(
                select(PipelineEvent).where(PipelineEvent.pipeline_run_id == pipeline_run_id)
            )
        )
        .scalars()
        .all()
    )
    event_types = {e.type for e in events}
    assert "policy.decision" in event_types
    assert "policy.budget.exceeded" in event_types


@pytest.mark.asyncio
async def test_policy_run_rate_quota_blocks_second_run(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("POLICY_MAX_RUNS_PER_MINUTE", "1")
    get_settings.cache_clear()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="clerk", auth_subject=subject, clerk_id=subject)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    request_id = uuid.uuid4()
    org_id = uuid.uuid4()

    first_run_id = uuid.uuid4()
    await _create_run(
        db_session=db_session,
        pipeline_run_id=first_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
    )

    second_run_id = uuid.uuid4()
    await _create_run(
        db_session=db_session,
        pipeline_run_id=second_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
    )

    gateway = PolicyGateway()
    ctx = PolicyContext(
        pipeline_run_id=second_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
        trigger=None,
        behavior=None,
        quality_mode=None,
        intent="chat",
        prompt_tokens_estimate=1,
    )
    result = await gateway.evaluate(checkpoint=PolicyCheckpoint.PRE_LLM, context=ctx)
    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "quota.runs_per_minute_exceeded"

    events = list(
        (
            await db_session.execute(
                select(PipelineEvent).where(PipelineEvent.pipeline_run_id == second_run_id)
            )
        )
        .scalars()
        .all()
    )
    event_types = {e.type for e in events}
    assert "policy.decision" in event_types
    assert "policy.quota.exceeded" in event_types


@pytest.mark.asyncio
async def test_policy_escalation_blocks_action_type_not_allowed(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("POLICY_ALLOWLIST_ENABLED", "true")
    monkeypatch.setenv("POLICY_ALLOWLIST_PRE_ACTION", "chat")
    monkeypatch.setenv(
        "POLICY_INTENT_RULES_JSON", '{"chat": {"action_types": [], "artifact_types": []}}'
    )
    get_settings.cache_clear()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="clerk", auth_subject=subject, clerk_id=subject)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()
    org_id = uuid.uuid4()

    await _create_run(
        db_session=db_session,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
    )

    gateway = PolicyGateway()
    ctx = PolicyContext(
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
        trigger=None,
        behavior=None,
        quality_mode=None,
        intent="chat",
        proposed_action_types=["tool.web.fetch"],
    )
    result = await gateway.evaluate(checkpoint=PolicyCheckpoint.PRE_ACTION, context=ctx)
    assert result.decision == PolicyDecision.BLOCK
    assert result.reason == "escalation.action_type_not_allowed"

    events = list(
        (
            await db_session.execute(
                select(PipelineEvent).where(PipelineEvent.pipeline_run_id == pipeline_run_id)
            )
        )
        .scalars()
        .all()
    )
    event_types = {e.type for e in events}
    assert "policy.decision" in event_types
    assert "policy.escalation.denied" in event_types


@pytest.mark.asyncio
async def test_policy_escalation_allows_configured_artifact_type(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_ALLOWLIST_ENABLED", "true")
    monkeypatch.setenv("POLICY_ALLOWLIST_PRE_PERSIST", "chat")
    monkeypatch.setenv(
        "POLICY_INTENT_RULES_JSON",
        '{"chat": {"action_types": [], "artifact_types": ["ui.chart"]}}',
    )
    get_settings.cache_clear()

    subject = f"test_{uuid.uuid4()}"
    user = User(auth_provider="clerk", auth_subject=subject, clerk_id=subject)
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()
    org_id = uuid.uuid4()

    await _create_run(
        db_session=db_session,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
    )

    gateway = PolicyGateway()
    ctx = PolicyContext(
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
        trigger=None,
        behavior=None,
        quality_mode=None,
        intent="chat",
        proposed_artifact_types=["ui.chart"],
    )
    result = await gateway.evaluate(checkpoint=PolicyCheckpoint.PRE_PERSIST, context=ctx)
    assert result.decision == PolicyDecision.ALLOW
