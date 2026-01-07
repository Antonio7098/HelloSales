"""Tests for WorkOS HTTP authentication - Enterprise Edition."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models import User


@pytest.mark.asyncio
async def test_http_auth_accepts_dev_token_creates_user(
    async_client, db_session
) -> None:
    """Test development mode accepts dev_token and creates user with org."""
    resp = await async_client.get(
        "/api/v1/profile",
        headers={"Authorization": "Bearer dev_token"},
    )

    assert resp.status_code == 200

    result = await db_session.execute(
        select(User).where(User.auth_subject == "dev_user_123")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.auth_provider == "workos"
    assert user.email == "dev@example.com"


@pytest.mark.asyncio
async def test_http_auth_missing_token_returns_401(async_client) -> None:
    """Test that missing Authorization header returns 401."""
    resp = await async_client.get("/api/v1/profile")
    assert resp.status_code == 401
    assert "Missing Authorization header" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_http_auth_invalid_format_returns_401(async_client) -> None:
    """Test that invalid Authorization header format returns 401."""
    resp = await async_client.get(
        "/api/v1/profile",
        headers={"Authorization": "InvalidFormat token123"},
    )
    assert resp.status_code == 401
    assert "Invalid Authorization header format" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_http_auth_missing_org_id_returns_403(
    async_client, monkeypatch
) -> None:
    """Test that token without org_id returns 403 for enterprise."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_123",
                "email": "workos@example.com",
                # Missing org_id
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer workos_token"},
        )

    assert resp.status_code == 403
    assert "Organization context required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_http_auth_creates_org_membership(
    async_client, db_session, monkeypatch
) -> None:
    """Test that auth creates organization and membership."""
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_456",
                "email": "enterprise@example.com",
                "org_id": "org_enterprise_456",
            }
        ),
    ):
        resp = await async_client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer workos_token"},
        )

    assert resp.status_code == 200

    # Verify user was created
    result = await db_session.execute(
        select(User).where(User.auth_subject == "workos_user_456")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.auth_provider == "workos"
