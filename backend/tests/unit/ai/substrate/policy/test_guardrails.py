import uuid

import pytest
from sqlalchemy import select

from app.ai.substrate import PipelineEventLogger
from app.ai.substrate.policy.guardrails import (
    GuardrailsCheckpoint,
    GuardrailsContext,
    GuardrailsDecision,
    GuardrailsStage,
)
from app.config import get_settings
from app.models import PipelineEvent, Session, User


@pytest.mark.asyncio
async def test_guardrails_force_block_emits_events(db_session, monkeypatch):
    monkeypatch.setenv("GUARDRAILS_ENABLED", "true")
    monkeypatch.setenv("GUARDRAILS_FORCE_CHECKPOINT", "pre_llm")
    monkeypatch.setenv("GUARDRAILS_FORCE_DECISION", "block")
    monkeypatch.setenv("GUARDRAILS_FORCE_REASON", "test_block")
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

    stage = GuardrailsStage()
    ctx = GuardrailsContext(
        pipeline_run_id=pipeline_run_id,
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        service="chat",
        intent="chat",
        input_excerpt="hello",
    )
    result = await stage.evaluate(checkpoint=GuardrailsCheckpoint.PRE_LLM, context=ctx)
    assert result.decision == GuardrailsDecision.BLOCK

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
    assert "guardrails.decision" in event_types
    assert "guardrails.blocked" in event_types
