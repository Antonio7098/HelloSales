from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_sailwind_playbook_products_admin_crud_and_rep_read(async_client, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_admin",
                "email": "admin@example.com",
                "org_id": "org_playbook_123",
                "role": "admin",
            }
        ),
    ):
        created = await async_client.post(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer workos_token"},
            json={"name": "Widget"},
        )
        assert created.status_code == 200
        product_id = created.json()["id"]

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_rep",
                "email": "rep@example.com",
                "org_id": "org_playbook_123",
                "role": "rep",
            }
        ),
    ):
        denied = await async_client.post(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer workos_token_rep"},
            json={"name": "Should Fail"},
        )
        assert denied.status_code == 403

        listed = await async_client.get(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer workos_token_rep"},
        )
        assert listed.status_code == 200
        ids = [p["id"] for p in listed.json()]
        assert product_id in ids


@pytest.mark.asyncio
async def test_sailwind_playbook_strategies_conflict_and_cross_tenant(async_client, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_admin",
                "email": "admin@example.com",
                "org_id": "org_playbook_456",
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

        strategy_1 = await async_client.post(
            "/api/v1/sailwind/strategies",
            headers={"Authorization": "Bearer token_admin"},
            json={
                "product_id": product_id,
                "client_id": client_id,
                "strategy_text": "Lead with ROI",
            },
        )
        assert strategy_1.status_code == 200
        strategy_id = strategy_1.json()["id"]
        assert strategy_1.json()["status"] == "draft"

        strategy_2 = await async_client.post(
            "/api/v1/sailwind/strategies",
            headers={"Authorization": "Bearer token_admin"},
            json={
                "product_id": product_id,
                "client_id": client_id,
                "strategy_text": "Duplicate",
            },
        )
        assert strategy_2.status_code == 409

        updated = await async_client.patch(
            f"/api/v1/sailwind/strategies/{strategy_id}",
            headers={"Authorization": "Bearer token_admin"},
            json={"status": "active"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "active"

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_other_admin",
                "email": "admin2@example.com",
                "org_id": "org_playbook_other",
                "role": "admin",
            }
        ),
    ):
        cross = await async_client.patch(
            f"/api/v1/sailwind/products/{product_id}",
            headers={"Authorization": "Bearer token_admin_other"},
            json={"name": "Nope"},
        )
        assert cross.status_code == 404


@pytest.mark.asyncio
async def test_sailwind_playbook_archetypes_admin_crud_and_linking(async_client, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_admin",
                "email": "admin@example.com",
                "org_id": "org_playbook_789",
                "role": "admin",
            }
        ),
    ):
        created_product_archetype = await async_client.post(
            "/api/v1/sailwind/product-archetypes",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Product Persona"},
        )
        assert created_product_archetype.status_code == 200
        product_archetype_id = created_product_archetype.json()["id"]

        created_client_archetype = await async_client.post(
            "/api/v1/sailwind/client-archetypes",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Client Persona", "industry": "Tech"},
        )
        assert created_client_archetype.status_code == 200
        client_archetype_id = created_client_archetype.json()["id"]

        created_product = await async_client.post(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Widget", "product_archetype_id": product_archetype_id},
        )
        assert created_product.status_code == 200
        assert created_product.json()["product_archetype_id"] == product_archetype_id
        product_id = created_product.json()["id"]

        created_client = await async_client.post(
            "/api/v1/sailwind/clients",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Globex", "client_archetype_id": client_archetype_id},
        )
        assert created_client.status_code == 200
        assert created_client.json()["client_archetype_id"] == client_archetype_id
        client_id = created_client.json()["id"]

        cleared_product = await async_client.patch(
            f"/api/v1/sailwind/products/{product_id}",
            headers={"Authorization": "Bearer token_admin"},
            json={"product_archetype_id": None},
        )
        assert cleared_product.status_code == 200
        assert cleared_product.json()["product_archetype_id"] is None

        cleared_client = await async_client.patch(
            f"/api/v1/sailwind/clients/{client_id}",
            headers={"Authorization": "Bearer token_admin"},
            json={"client_archetype_id": None},
        )
        assert cleared_client.status_code == 200
        assert cleared_client.json()["client_archetype_id"] is None

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_rep",
                "email": "rep@example.com",
                "org_id": "org_playbook_789",
                "role": "rep",
            }
        ),
    ):
        denied = await async_client.post(
            "/api/v1/sailwind/product-archetypes",
            headers={"Authorization": "Bearer token_rep"},
            json={"name": "Denied"},
        )
        assert denied.status_code == 403

        listed = await async_client.get(
            "/api/v1/sailwind/product-archetypes",
            headers={"Authorization": "Bearer token_rep"},
        )
        assert listed.status_code == 200


@pytest.mark.asyncio
async def test_sailwind_playbook_denies_linking_archived_archetype(async_client, monkeypatch):
    monkeypatch.setenv("WORKOS_AUTH_ENABLED", "true")
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_123")

    with patch(
        "app.auth.identity.verify_workos_jwt",
        new=AsyncMock(
            return_value={
                "sub": "workos_user_admin",
                "email": "admin@example.com",
                "org_id": "org_playbook_999",
                "role": "admin",
            }
        ),
    ):
        created_archetype = await async_client.post(
            "/api/v1/sailwind/product-archetypes",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Archived Persona"},
        )
        assert created_archetype.status_code == 200
        archetype_id = created_archetype.json()["id"]

        archived = await async_client.patch(
            f"/api/v1/sailwind/product-archetypes/{archetype_id}",
            headers={"Authorization": "Bearer token_admin"},
            json={"archived": True},
        )
        assert archived.status_code == 200
        assert archived.json()["archived_at"] is not None

        denied = await async_client.post(
            "/api/v1/sailwind/products",
            headers={"Authorization": "Bearer token_admin"},
            json={"name": "Widget", "product_archetype_id": archetype_id},
        )
        assert denied.status_code == 400
