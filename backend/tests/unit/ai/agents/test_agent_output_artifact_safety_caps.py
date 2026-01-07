import uuid

import pytest
from sqlalchemy import select

from app.ai.substrate import PipelineEventLogger, handle_agent_output_runtime
from app.config import get_settings
from app.models import Artifact, PipelineEvent, Session, User
from app.schemas.agent_output import AgentOutput


@pytest.mark.asyncio
async def test_artifact_count_cap_rejects(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_MAX_ARTIFACTS", "1")
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

    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service="chat",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
    )
    await db_session.commit()

    agent_output = AgentOutput(
        assistant_message="hi",
        actions=[],
        artifacts=[
            {"type": "a", "payload": {"k": "v"}},
            {"type": "b", "payload": {"k": "v"}},
        ],
    )

    await handle_agent_output_runtime(
        db=db_session,
        agent_output=agent_output,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
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
                select(PipelineEvent).where(PipelineEvent.pipeline_run_id == pipeline_run_id)
            )
        )
        .scalars()
        .all()
    )
    assert any(e.type == "agent_output.artifacts.rejected" for e in events)


@pytest.mark.asyncio
async def test_artifact_payload_bytes_cap_rejects(db_session, monkeypatch):
    monkeypatch.setenv("POLICY_MAX_ARTIFACT_PAYLOAD_BYTES", "10")
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

    event_logger = PipelineEventLogger(db_session)
    await event_logger.create_run(
        pipeline_run_id=pipeline_run_id,
        service="chat",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
    )
    await db_session.commit()

    agent_output = AgentOutput(
        assistant_message="hi",
        actions=[],
        artifacts=[{"type": "a", "payload": {"long": "this will exceed"}}],
    )

    await handle_agent_output_runtime(
        db=db_session,
        agent_output=agent_output,
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
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
                select(PipelineEvent).where(PipelineEvent.pipeline_run_id == pipeline_run_id)
            )
        )
        .scalars()
        .all()
    )
    assert any(e.type == "agent_output.artifacts.rejected" for e in events)
