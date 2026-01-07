import uuid

import pytest

from app.ai.substrate import PipelineEventLogger
from app.config import get_settings
from app.models import PipelineRun, Session, User


@pytest.mark.asyncio
async def test_admin_pipeline_runs_exposes_mode_quality_and_canceled(
    async_client,
    db_session,
    monkeypatch,
):
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")
    get_settings.cache_clear()

    user_subject = f"admin_pipeline_runs_{uuid.uuid4()}"
    user = User(
        auth_provider="clerk",
        auth_subject=user_subject,
        clerk_id=user_subject,
        email="admin-pipeline-runs@example.com",
    )
    db_session.add(user)
    await db_session.flush()

    session = Session(user_id=user.id)
    db_session.add(session)
    await db_session.flush()

    pipeline_run_id = uuid.uuid4()
    request_id = uuid.uuid4()
    org_id = uuid.uuid4()

    run = PipelineRun(
        id=pipeline_run_id,
        service="chat",
        status="canceled",
        mode="typed",
        quality_mode="fast",
        request_id=request_id,
        org_id=org_id,
        session_id=session.id,
        user_id=user.id,
        success=False,
        error="canceled",
    )
    db_session.add(run)

    event_logger = PipelineEventLogger(db_session)
    await event_logger.emit(
        pipeline_run_id=pipeline_run_id,
        type="pipeline.created",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        data={"trigger": "test"},
    )
    await event_logger.emit(
        pipeline_run_id=pipeline_run_id,
        type="pipeline.started",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        data=None,
    )
    await event_logger.emit(
        pipeline_run_id=pipeline_run_id,
        type="pipeline.canceled",
        request_id=request_id,
        session_id=session.id,
        user_id=user.id,
        org_id=org_id,
        data=None,
    )

    await db_session.commit()

    resp = await async_client.get("/admin/stats/pipeline-runs", params={"limit": 50})
    assert resp.status_code == 200
    payload = resp.json()

    items = payload.get("items")
    assert isinstance(items, list)

    match = next((item for item in items if item.get("id") == str(pipeline_run_id)), None)
    assert match is not None
    assert match.get("status") == "canceled"
    assert match.get("mode") == "typed"
    assert match.get("quality_mode") == "fast"
    assert match.get("success") is False

    detail = await async_client.get(f"/admin/stats/pipeline-runs/{pipeline_run_id}")
    assert detail.status_code == 200
    detail_payload = detail.json()

    run_data = detail_payload.get("run")
    assert isinstance(run_data, dict)
    assert run_data.get("id") == str(pipeline_run_id)
    assert run_data.get("status") == "canceled"
    assert run_data.get("mode") == "typed"
    assert run_data.get("quality_mode") == "fast"

    events = detail_payload.get("events")
    assert isinstance(events, list)
    event_types = [e.get("type") for e in events]
    assert "pipeline.created" in event_types
    assert "pipeline.started" in event_types
    assert "pipeline.canceled" in event_types
