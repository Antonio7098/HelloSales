import uuid

import pytest

from app.ai.substrate import PipelineEventLogger
from app.models import PipelineRun, User


@pytest.mark.asyncio
async def test_admin_policy_denials_metrics_aggregates_denies(async_client, db_session):
    user_subject = f"policy_metrics_user_{uuid.uuid4()}"
    user = User(
        auth_provider="clerk",
        auth_subject=user_subject,
        clerk_id=user_subject,
        email="policy-metrics@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    run_id = uuid.uuid4()
    run = PipelineRun(id=run_id, service="chat", user_id=user.id, success=True)
    db_session.add(run)
    await db_session.flush()

    logger = PipelineEventLogger(db_session)

    # Allow decision
    await logger.emit(
        pipeline_run_id=run_id,
        type="policy.decision",
        request_id=None,
        session_id=None,
        user_id=user.id,
        org_id=None,
        data={
            "checkpoint": "pre_llm",
            "decision": "allow",
            "reason": "default_allow",
            "intent": "chat",
        },
    )

    # Deny decision
    await logger.emit(
        pipeline_run_id=run_id,
        type="policy.decision",
        request_id=None,
        session_id=None,
        user_id=user.id,
        org_id=None,
        data={
            "checkpoint": "pre_action",
            "decision": "block",
            "reason": "escalation.action_type_not_allowed",
            "intent": "chat",
        },
    )

    await db_session.commit()

    resp = await async_client.get(
        "/admin/stats/policy-denials",
        params={"since_minutes": 60, "limit": 100, "pipeline_run_id": str(run_id)},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload.get("total_policy_decisions") == 2
    assert payload.get("denied_total") == 1

    denied_by_reason = payload.get("denied_by_reason")
    assert isinstance(denied_by_reason, dict)
    assert denied_by_reason.get("escalation.action_type_not_allowed") == 1

    denied_by_checkpoint = payload.get("denied_by_checkpoint")
    assert isinstance(denied_by_checkpoint, dict)
    assert denied_by_checkpoint.get("pre_action") == 1

    denied_by_intent = payload.get("denied_by_intent")
    assert isinstance(denied_by_intent, dict)
    assert denied_by_intent.get("chat") == 1


@pytest.mark.asyncio
async def test_admin_policy_triggers_metrics_counts_budget_and_quota(async_client, db_session):
    user_subject = f"policy_triggers_user_{uuid.uuid4()}"
    user = User(
        auth_provider="clerk",
        auth_subject=user_subject,
        clerk_id=user_subject,
        email="policy-triggers@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    run_id = uuid.uuid4()
    run = PipelineRun(id=run_id, service="chat", user_id=user.id, success=True)
    db_session.add(run)
    await db_session.flush()

    logger = PipelineEventLogger(db_session)
    await logger.emit(
        pipeline_run_id=run_id,
        type="policy.budget.exceeded",
        request_id=None,
        session_id=None,
        user_id=user.id,
        org_id=None,
        data={
            "checkpoint": "pre_llm",
            "decision": "block",
            "reason": "budget.prompt_tokens_exceeded",
        },
    )
    await logger.emit(
        pipeline_run_id=run_id,
        type="policy.quota.exceeded",
        request_id=None,
        session_id=None,
        user_id=user.id,
        org_id=None,
        data={
            "checkpoint": "pre_llm",
            "decision": "block",
            "reason": "quota.runs_per_minute_exceeded",
        },
    )

    await db_session.commit()

    resp = await async_client.get(
        "/admin/stats/policy-triggers",
        params={"since_minutes": 60, "pipeline_run_id": str(run_id)},
    )
    assert resp.status_code == 200
    payload = resp.json()

    by_type = payload.get("by_type")
    assert isinstance(by_type, dict)
    assert by_type.get("policy.budget.exceeded") == 1
    assert by_type.get("policy.quota.exceeded") == 1
    assert payload.get("total") == 2
