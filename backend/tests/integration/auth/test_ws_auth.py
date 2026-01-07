"""Tests for WebSocket authentication - Enterprise Edition."""

from sqlalchemy import select

from app.models import Organization, OrganizationMembership, User


def test_ws_auth_accepts_dev_token(client, _db_session):
    """Test WebSocket accepts dev_token in development mode."""
    with client.websocket_connect("/ws") as ws:
        # Send auth message with dev token
        ws.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        data = ws.receive_json()

        assert data["type"] == "auth.success"
        assert data["payload"]["userId"] is not None
        assert data["payload"]["orgId"] is not None


def test_ws_auth_missing_token_returns_error(client):
    """Test WebSocket auth without token returns error."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "payload": {}})
        data = ws.receive_json()

        assert data["type"] == "auth.error"
        assert data["payload"]["code"] == "MISSING_TOKEN"


def test_ws_auth_missing_org_id_returns_error(client):
    """Test WebSocket auth without org_id returns error."""
    with client.websocket_connect("/ws") as ws:
        # Mock the token verification to return claims without org_id
        from unittest.mock import AsyncMock, patch

        with patch("app.api.ws.handlers.auth.verify_identity_token", new=AsyncMock(
            return_value=type("Identity", (), {
                "provider": "workos",
                "subject": "workos_user_123",
                "email": "test@example.com",
                "org_id": None,  # Missing org_id
                "raw_claims": {},
            })()
        )):
            ws.send_json({"type": "auth", "payload": {"token": "mock_token"}})
            data = ws.receive_json()

            assert data["type"] == "auth.error"
            assert data["payload"]["code"] == "MISSING_ORG_ID"


def test_ws_auth_creates_user_and_org(client, db_session):
    """Test WebSocket auth creates user and organization."""
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "payload": {"token": "dev_token"}})
        data = ws.receive_json()

        assert data["type"] == "auth.success"
        user_id = data["payload"]["userId"]
        org_id = data["payload"]["orgId"]

        # Verify user was created in DB
        from uuid import UUID
        result = db_session.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.auth_provider == "workos"

        # Verify organization was created
        result = db_session.execute(
            select(Organization).where(Organization.id == UUID(org_id))
        )
        org = result.scalar_one_or_none()
        assert org is not None
        assert org.org_id == "dev_org_123"

        # Verify membership
        result = db_session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == org.id,
            )
        )
        membership = result.scalar_one_or_none()
        assert membership is not None
