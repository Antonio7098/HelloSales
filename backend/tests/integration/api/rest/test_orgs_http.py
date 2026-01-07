from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.models import Organization, OrganizationMembership


@pytest.mark.asyncio
async def test_orgs_me_missing_auth_returns_401(async_client) -> None:
    resp = await async_client.get("/api/v1/orgs/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_orgs_me_denies_clerk_sessions(async_client, monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CLERK_SECRET_KEY", "")
    monkeypatch.setenv("CLERK_DEV_BYPASS_ENABLED", "true")

    resp = await async_client.get(
        "/api/v1/orgs/me",
        headers={"Authorization": "Bearer dev_token"},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_orgs_me_returns_org_for_workos_session(
    async_client, db_session, monkeypatch
) -> None:
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_123",
                "email": "workos@example.com",
                "org_id": "org_123",
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/orgs/me",
            headers={"Authorization": "Bearer workos_token"},
        )

        resp2 = await async_client.get(
            "/api/v1/orgs/me",
            headers={"Authorization": "Bearer workos_token"},
        )

    assert resp.status_code == 200
    assert resp2.status_code == 200

    payload = resp.json()
    assert payload["workos_org_id"] == "org_123"
    assert payload["organization_id"]

    org_count = await db_session.scalar(
        select(func.count())
        .select_from(Organization)
        .where(Organization.workos_org_id == "org_123")
    )
    assert org_count == 1

    result = await db_session.execute(
        select(Organization).where(Organization.workos_org_id == "org_123")
    )
    org = result.scalar_one()

    membership_count = await db_session.scalar(
        select(func.count())
        .select_from(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org.id)
    )
    assert membership_count == 1


@pytest.mark.asyncio
async def test_orgs_me_membership_returns_membership(async_client, db_session, monkeypatch) -> None:
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_456",
                "email": "workos2@example.com",
                "org_id": "org_456",
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/orgs/me/memberships",
            headers={"Authorization": "Bearer workos_token_2"},
        )

    assert resp.status_code == 200
    payload = resp.json()

    assert payload["user_id"]
    assert payload["organization_id"]
    assert payload["created_at"]

    org = await db_session.scalar(
        select(Organization).where(Organization.workos_org_id == "org_456")
    )
    assert org is not None
