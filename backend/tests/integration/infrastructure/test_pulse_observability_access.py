import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.substrate import PipelineEventLogger
from app.config import get_settings
from app.models import Organization, OrganizationMembership, PipelineRun, User


@pytest.mark.asyncio
async def test_pulse_pipeline_runs_scoped_to_clerk_user(async_client, db_session, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "false")
    get_settings.cache_clear()

    subject_1 = f"pulse_user_1_{uuid.uuid4()}"
    subject_2 = f"pulse_user_2_{uuid.uuid4()}"

    user_1 = User(
        auth_provider="clerk",
        auth_subject=subject_1,
        clerk_id=subject_1,
        email="pulse-user-1@example.com",
    )
    user_2 = User(
        auth_provider="clerk",
        auth_subject=subject_2,
        clerk_id=subject_2,
        email="pulse-user-2@example.com",
    )
    db_session.add_all([user_1, user_2])
    await db_session.flush()

    run_1_id = uuid.uuid4()
    run_2_id = uuid.uuid4()

    run_1 = PipelineRun(id=run_1_id, service="chat", user_id=user_1.id, success=True)
    run_2 = PipelineRun(id=run_2_id, service="chat", user_id=user_2.id, success=True)
    db_session.add_all([run_1, run_2])

    event_logger = PipelineEventLogger(db_session)
    await event_logger.emit(
        pipeline_run_id=run_1_id,
        type="pipeline.created",
        request_id=None,
        session_id=None,
        user_id=user_1.id,
        org_id=None,
        data=None,
    )
    await event_logger.emit(
        pipeline_run_id=run_2_id,
        type="pipeline.created",
        request_id=None,
        session_id=None,
        user_id=user_2.id,
        org_id=None,
        data=None,
    )

    await db_session.commit()

    with patch(
        "app.auth.identity.verify_clerk_jwt",
        new=AsyncMock(return_value={"sub": subject_1, "email": "pulse-user-1@example.com"}),
    ):
        resp = await async_client.get(
            "/api/v1/pulse/pipeline-runs",
            headers={"Authorization": "Bearer token"},
            params={"limit": 50},
        )
        assert resp.status_code == 200
        payload = resp.json()
        items = payload.get("items")
        assert isinstance(items, list)
        ids = {item.get("id") for item in items}
        assert str(run_1_id) in ids
        assert str(run_2_id) not in ids

        detail = await async_client.get(
            f"/api/v1/pulse/pipeline-runs/{run_2_id}",
            headers={"Authorization": "Bearer token"},
        )
        assert detail.status_code == 404


@pytest.mark.asyncio
async def test_pulse_pipeline_runs_admin_can_view_all(async_client, db_session, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "false")

    admin_subject = f"pulse_admin_{uuid.uuid4()}"
    monkeypatch.setenv("ADMIN_USER_IDS", admin_subject)
    get_settings.cache_clear()

    user_subject = f"pulse_user_{uuid.uuid4()}"
    admin_user = User(
        auth_provider="clerk",
        auth_subject=admin_subject,
        clerk_id=admin_subject,
        email="pulse-admin@example.com",
    )
    user = User(
        auth_provider="clerk",
        auth_subject=user_subject,
        clerk_id=user_subject,
        email="pulse-user@example.com",
    )
    db_session.add_all([admin_user, user])
    await db_session.flush()

    run_user_id = uuid.uuid4()
    run_admin_id = uuid.uuid4()

    run_user = PipelineRun(id=run_user_id, service="chat", user_id=user.id, success=True)
    run_admin = PipelineRun(id=run_admin_id, service="chat", user_id=admin_user.id, success=True)
    db_session.add_all([run_user, run_admin])
    await db_session.commit()

    with patch(
        "app.auth.identity.verify_clerk_jwt",
        new=AsyncMock(return_value={"sub": admin_subject, "email": "pulse-admin@example.com"}),
    ):
        resp = await async_client.get(
            "/api/v1/pulse/pipeline-runs",
            headers={"Authorization": "Bearer token"},
            params={"limit": 50},
        )
        assert resp.status_code == 200
        payload = resp.json()
        items = payload.get("items")
        assert isinstance(items, list)
        ids = {item.get("id") for item in items}
        assert str(run_user_id) in ids
        assert str(run_admin_id) in ids


@pytest.mark.asyncio
async def test_pulse_workos_requires_membership_and_scopes_to_org(
    async_client, db_session, monkeypatch
):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")
    get_settings.cache_clear()

    workos_org_id = f"org_{uuid.uuid4()}"
    subject = f"workos_user_{uuid.uuid4()}"

    user = User(
        auth_provider="workos",
        auth_subject=subject,
        clerk_id=None,
        email="workos-user@example.com",
    )
    org = Organization(workos_org_id=workos_org_id, name=None)
    db_session.add_all([user, org])
    await db_session.flush()

    membership = OrganizationMembership(
        user_id=user.id, organization_id=org.id, role=None, permissions=None
    )
    db_session.add(membership)

    other_org = Organization(workos_org_id=f"org_{uuid.uuid4()}", name=None)
    db_session.add(other_org)
    await db_session.flush()

    run_allowed_id = uuid.uuid4()
    run_blocked_id = uuid.uuid4()

    run_allowed = PipelineRun(
        id=run_allowed_id,
        service="chat",
        user_id=user.id,
        org_id=org.id,
        success=True,
    )
    run_blocked = PipelineRun(
        id=run_blocked_id,
        service="chat",
        user_id=user.id,
        org_id=other_org.id,
        success=True,
    )
    db_session.add_all([run_allowed, run_blocked])

    event_logger = PipelineEventLogger(db_session)
    await event_logger.emit(
        pipeline_run_id=run_allowed_id,
        type="pipeline.created",
        request_id=None,
        session_id=None,
        user_id=user.id,
        org_id=org.id,
        data=None,
    )

    await db_session.commit()

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": subject,
                "email": "workos-user@example.com",
                "org_id": workos_org_id,
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/pulse/pipeline-runs",
            headers={"Authorization": "Bearer token"},
            params={"limit": 50},
        )
        assert resp.status_code == 200
        payload = resp.json()
        items = payload.get("items")
        assert isinstance(items, list)
        ids = {item.get("id") for item in items}
        assert str(run_allowed_id) in ids
        assert str(run_blocked_id) not in ids

        detail = await async_client.get(
            f"/api/v1/pulse/pipeline-runs/{run_blocked_id}",
            headers={"Authorization": "Bearer token"},
        )
        assert detail.status_code == 404


@pytest.mark.asyncio
async def test_pulse_workos_missing_membership_returns_403(async_client, db_session, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")
    get_settings.cache_clear()

    workos_org_id = f"org_{uuid.uuid4()}"
    subject = f"workos_user_{uuid.uuid4()}"

    user = User(
        auth_provider="workos",
        auth_subject=subject,
        clerk_id=None,
        email="workos-user@example.com",
    )
    org = Organization(workos_org_id=workos_org_id, name=None)
    db_session.add_all([user, org])
    await db_session.flush()

    run_id = uuid.uuid4()
    run = PipelineRun(id=run_id, service="chat", user_id=user.id, org_id=org.id, success=True)
    db_session.add(run)
    await db_session.commit()

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": subject,
                "email": "workos-user@example.com",
                "org_id": workos_org_id,
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/pulse/pipeline-runs",
            headers={"Authorization": "Bearer token"},
            params={"limit": 50},
        )
        assert resp.status_code == 403
