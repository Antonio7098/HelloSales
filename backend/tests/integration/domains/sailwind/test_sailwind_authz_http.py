from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models import Organization, OrganizationMembership


@pytest.mark.asyncio
async def test_sailwind_admin_placeholder_denies_non_admin(async_client, monkeypatch) -> None:
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_123",
                "email": "workos@example.com",
                "org_id": "org_123",
                "role": "rep",
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/sailwind/admin/placeholder",
            headers={"Authorization": "Bearer workos_token"},
        )

    assert resp.status_code == 403
    payload = resp.json()
    assert payload["detail"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_sailwind_admin_placeholder_allows_admin_and_persists_role(
    async_client, db_session, monkeypatch
) -> None:
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_456",
                "email": "workos2@example.com",
                "org_id": "org_456",
                "role": "admin",
                "permissions": {"can_export": True},
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/sailwind/admin/placeholder",
            headers={"Authorization": "Bearer workos_token_2"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    org = await db_session.scalar(select(Organization).where(Organization.workos_org_id == "org_456"))
    assert org is not None

    membership = await db_session.scalar(
        select(OrganizationMembership).where(OrganizationMembership.organization_id == org.id)
    )
    assert membership is not None
    assert membership.role == "admin"
    assert membership.permissions == {"can_export": True}
