from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.database import get_session_context
from app.models import User


@pytest.mark.asyncio
async def test_sailwind_practice_rep_assignments_admin_create_and_rep_views(async_client, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    org_id = "org_practice_http_123"

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_admin_practice_http",
                "email": "admin@example.com",
                "org_id": org_id,
                "role": "admin",
            }
        ),
    ):
        product = await async_client.post(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Widget"},
        )
        assert product.status_code == 200
        product_id = product.json()["id"]

        client = await async_client.post(
            "/api/v1/sailwind/clients",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Globex", "industry": "Tech"},
        )
        assert client.status_code == 200
        client_id = client.json()["id"]

        strategy = await async_client.post(
            "/api/v1/sailwind/strategies",
            headers={"Authorization": "Bearer token_admin"},
            json={
                "product_id": product_id,
                "client_id": client_id,
                "strategy_text": "Lead with ROI",
            },
        )
        assert strategy.status_code == 200
        strategy_id = strategy.json()["id"]

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_rep_practice_http",
                "email": "rep@example.com",
                "org_id": org_id,
                "role": "rep",
            }
        ),
    ):
        # Bootstrap rep user + membership
        listed = await async_client.get(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer token_rep"},
        )
        assert listed.status_code == 200

    async with get_session_context() as db:
        rep_user = await db.scalar(
            select(User).where(
                User.auth_provider == "workos",
                User.auth_subject == "workos_rep_practice_http",
            )
        )
        assert rep_user is not None
        rep_user_id = str(rep_user.id)

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_admin_practice_http",
                "email": "admin@example.com",
                "org_id": org_id,
                "role": "admin",
            }
        ),
    ):
        created = await async_client.post(
            "/api/v1/sailwind/rep-assignments",
            headers={"Authorization": "Bearer token_admin"},
            json={
                "user_id": rep_user_id,
                "product_id": product_id,
                "client_id": client_id,
                "strategy_id": strategy_id,
                "min_practice_minutes": 10,
            },
        )
        assert created.status_code == 200
        assignment_id = created.json()["id"]

        admin_list = await async_client.get(
            "/api/v1/sailwind/rep-assignments",
            headers={"Authorization": "Bearer token_admin"},
        )
        assert admin_list.status_code == 200
        ids = [a["id"] for a in admin_list.json()]
        assert assignment_id in ids

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_rep_practice_http",
                "email": "rep@example.com",
                "org_id": org_id,
                "role": "rep",
            }
        ),
    ):
        rep_list = await async_client.get(
            "/api/v1/sailwind/my/rep-assignments",
            headers={"Authorization": "Bearer token_rep"},
        )
        assert rep_list.status_code == 200
        rep_ids = [a["id"] for a in rep_list.json()]
        assert assignment_id in rep_ids


@pytest.mark.asyncio
async def test_sailwind_practice_sessions_rep_start_and_cross_tenant_denial(async_client, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    org_id = "org_practice_http_sessions_123"

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_admin_practice_http_sessions",
                "email": "admin@example.com",
                "org_id": org_id,
                "role": "admin",
            }
        ),
    ):
        product = await async_client.post(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Widget"},
        )
        assert product.status_code == 200
        product_id = product.json()["id"]

        client = await async_client.post(
            "/api/v1/sailwind/clients",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Globex", "industry": "Tech"},
        )
        assert client.status_code == 200
        client_id = client.json()["id"]

        strategy = await async_client.post(
            "/api/v1/sailwind/strategies",
            headers={"Authorization": "Bearer token_admin"},
            json={
                "product_id": product_id,
                "client_id": client_id,
                "strategy_text": "Lead with ROI",
            },
        )
        assert strategy.status_code == 200
        strategy_id = strategy.json()["id"]

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_rep_practice_http_sessions",
                "email": "rep@example.com",
                "org_id": org_id,
                "role": "rep",
            }
        ),
    ):
        started = await async_client.post(
            "/api/v1/sailwind/practice-sessions",
            headers={"Authorization": "Bearer token_rep"},
            json={
                "strategy_id": strategy_id,
                "rep_assignment_id": None,
            },
        )
        assert started.status_code == 200
        practice_id = started.json()["id"]
        assert started.json()["chat_session_id"]

        listed = await async_client.get(
            "/api/v1/sailwind/my/practice-sessions",
            headers={"Authorization": "Bearer token_rep"},
        )
        assert listed.status_code == 200
        ids = [s["id"] for s in listed.json()]
        assert practice_id in ids

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_admin_practice_http_other",
                "email": "admin2@example.com",
                "org_id": "org_practice_http_other",
                "role": "admin",
            }
        ),
    ):
        cross = await async_client.post(
            "/api/v1/sailwind/rep-assignments",
            headers={"Authorization": "Bearer token_admin_other"},
            json={
                "user_id": started.json()["user_id"],
                "product_id": product_id,
                "client_id": client_id,
                "strategy_id": strategy_id,
                "min_practice_minutes": 10,
            },
        )
        assert cross.status_code == 404


@pytest.mark.asyncio
async def test_sailwind_practice_admin_endpoints_denied_for_rep(async_client, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_rep_denied_http",
                "email": "rep@example.com",
                "org_id": "org_practice_http_denied",
                "role": "rep",
            }
        ),
    ):
        denied_list = await async_client.get(
            "/api/v1/sailwind/rep-assignments",
            headers={"Authorization": "Bearer token_rep"},
        )
        assert denied_list.status_code == 403
