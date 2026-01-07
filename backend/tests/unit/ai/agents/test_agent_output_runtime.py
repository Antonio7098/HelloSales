import uuid

import pytest
from sqlalchemy import select

from app.ai.substrate import PipelineEventLogger, handle_agent_output_runtime
from app.config import get_settings
from app.models import Artifact, PipelineEvent, Session, User
from app.schemas.agent_output import AgentOutput


@pytest.mark.asyncio
async def test_pre_persist_policy_deny_blocks_artifact_persist(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("POLICY_FORCE_CHECKPOINT", "pre_persist")
    monkeypatch.setenv("POLICY_FORCE_DECISION", "block")
    monkeypatch.setenv("POLICY_FORCE_REASON", "test_block")
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
    _org_id = uuid.uuid4()

    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service="chat",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=None,  # No org_id to avoid membership requirement
    )
    await db_session.commit()

    agent_output = AgentOutput(
        assistant_message="hi",
        actions=[],
        artifacts=[{"type": "test", "payload": {"k": "v"}}],
    )

    await handle_agent_output_runtime(
        db=db_session,
        agent_output=agent_output,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=None,  # No org_id to avoid membership requirement
        service="chat",
    )
    await db_session.commit()

    artifacts = list(
        (
            await db_session.execute(
                select(Artifact).where(Artifact.pipeline_run_id == pipeline_run_id)
            )
        )
        .scalars()
        .all()
    )
    assert artifacts == []

    events = list(
        (
            await db_session.execute(
                select(PipelineEvent)
                .where(PipelineEvent.pipeline_run_id == pipeline_run_id)
                .order_by(PipelineEvent.timestamp.asc())
            )
        )
        .scalars()
        .all()
    )
    decision_events = [e for e in events if e.type == "policy.decision"]
    assert len(decision_events) >= 1
    assert any((e.data or {}).get("checkpoint") == "pre_persist" for e in decision_events)


@pytest.mark.asyncio
async def test_pre_persist_allows_artifact_persist(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.delenv("POLICY_FORCE_CHECKPOINT", raising=False)
    monkeypatch.delenv("POLICY_FORCE_DECISION", raising=False)
    monkeypatch.delenv("POLICY_FORCE_REASON", raising=False)
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "false")  # Disable tenant requirement
    monkeypatch.setenv(
        "POLICY_INTENT_RULES_JSON",
        '{"chat": {"action_types": [], "artifact_types": ["test"]}}',
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
    # Note: Not setting org_id to avoid membership requirement for this test

    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service="chat",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=None,  # No org_id to avoid membership requirement
    )
    await db_session.commit()

    agent_output = AgentOutput(
        assistant_message="hi",
        actions=[],
        artifacts=[{"type": "test", "payload": {"k": "v"}}],
    )

    await handle_agent_output_runtime(
        db=db_session,
        agent_output=agent_output,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=None,  # No org_id to avoid membership requirement
        service="chat",
    )
    await db_session.commit()

    artifacts = list(
        (
            await db_session.execute(
                select(Artifact).where(Artifact.pipeline_run_id == pipeline_run_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(artifacts) == 1
    assert artifacts[0].type == "test"
    assert artifacts[0].payload == {"k": "v"}


@pytest.mark.asyncio
async def test_pre_action_default_escalation_blocks_action(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_GATEWAY_ENABLED", "true")
    monkeypatch.delenv("POLICY_FORCE_CHECKPOINT", raising=False)
    monkeypatch.delenv("POLICY_FORCE_DECISION", raising=False)
    monkeypatch.delenv("POLICY_FORCE_REASON", raising=False)
    monkeypatch.setenv("POLICY_ALLOWLIST_ENABLED", "true")
    monkeypatch.setenv("POLICY_ALLOWLIST_PRE_ACTION", "chat")
    monkeypatch.setenv(
        "POLICY_INTENT_RULES_JSON",
        '{"chat": {"action_types": [], "artifact_types": []}}',
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
    _org_id = uuid.uuid4()

    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service="chat",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=None,  # No org_id to avoid membership requirement
    )
    await db_session.commit()

    agent_output = AgentOutput(
        assistant_message="hi",
        actions=[{"type": "tool.web.fetch", "payload": {"url": "https://example.com"}}],
        artifacts=[],
    )

    await handle_agent_output_runtime(
        db=db_session,
        agent_output=agent_output,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=None,  # No org_id to avoid membership requirement
        service="chat",
    )
    await db_session.commit()

    events = list(
        (
            await db_session.execute(
                select(PipelineEvent)
                .where(PipelineEvent.pipeline_run_id == pipeline_run_id)
                .order_by(PipelineEvent.timestamp.asc())
            )
        )
        .scalars()
        .all()
    )
    event_types = [e.type for e in events]
    assert "policy.decision" in event_types
    assert "policy.escalation.denied" in event_types
    assert "agent_output.actions.denied" in event_types
