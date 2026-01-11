"""Tests for domain entities."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.entities.user import User
from app.domain.entities.organization import Organization, OrganizationMembership
from app.domain.entities.session import Session, SummaryState
from app.domain.entities.product import Product
from app.domain.entities.client import Client


class TestUser:
    """Test User entity."""

    def test_user_creation(self):
        """Test creating a user."""
        user_id = uuid4()
        user = User(
            id=user_id,
            auth_provider="workos",
            auth_subject="user_123",
            email="test@example.com",
            display_name="Test User",
        )

        assert user.id == user_id
        assert user.auth_provider == "workos"
        assert user.auth_subject == "user_123"
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"

    def test_user_requires_email(self):
        """Test that user requires email."""
        with pytest.raises(ValueError, match="email is required"):
            User(
                id=uuid4(),
                auth_provider="workos",
                auth_subject="user_123",
                email="",
            )

    def test_user_requires_auth_subject(self):
        """Test that user requires auth_subject."""
        with pytest.raises(ValueError, match="auth_subject is required"):
            User(
                id=uuid4(),
                auth_provider="workos",
                auth_subject="",
                email="test@example.com",
            )


class TestOrganization:
    """Test Organization entity."""

    def test_organization_creation(self):
        """Test creating an organization."""
        org = Organization(
            id=uuid4(),
            external_id="org_123",
            name="Test Org",
            slug="test-org",
        )

        assert org.external_id == "org_123"
        assert org.name == "Test Org"
        assert org.slug == "test-org"

    def test_organization_requires_name(self):
        """Test that organization requires name."""
        with pytest.raises(ValueError, match="name is required"):
            Organization(
                id=uuid4(),
                external_id="org_123",
                name="",
            )


class TestOrganizationMembership:
    """Test OrganizationMembership entity."""

    def test_membership_has_permission_admin(self):
        """Test admin has all permissions."""
        membership = OrganizationMembership(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            role="admin",
        )

        assert membership.has_permission("create_product")
        assert membership.has_permission("delete_user")
        assert membership.is_admin()

    def test_membership_has_permission_member(self):
        """Test member has only granted permissions."""
        membership = OrganizationMembership(
            id=uuid4(),
            user_id=uuid4(),
            organization_id=uuid4(),
            role="member",
            permissions={"create_product": True},
        )

        assert membership.has_permission("create_product")
        assert not membership.has_permission("delete_user")
        assert not membership.is_admin()


class TestSession:
    """Test Session entity."""

    def test_session_is_active(self):
        """Test session active state."""
        session = Session(
            id=uuid4(),
            user_id=uuid4(),
            state="active",
        )

        assert session.is_active()

    def test_session_end(self):
        """Test ending a session."""
        session = Session(
            id=uuid4(),
            user_id=uuid4(),
            state="active",
            started_at=datetime.now(UTC),
        )

        session.end()

        assert not session.is_active()
        assert session.state == "ended"
        assert session.ended_at is not None
        assert session.duration_ms is not None


class TestSummaryState:
    """Test SummaryState entity."""

    def test_should_summarize(self):
        """Test summary threshold check."""
        state = SummaryState(
            id=uuid4(),
            session_id=uuid4(),
            turns_since_summary=7,
        )

        assert not state.should_summarize(threshold=8)

        state.increment_turn()
        assert state.should_summarize(threshold=8)

    def test_reset_after_summary(self):
        """Test resetting state after summary."""
        state = SummaryState(
            id=uuid4(),
            session_id=uuid4(),
            turns_since_summary=8,
        )

        state.reset_after_summary(new_cutoff=10)

        assert state.turns_since_summary == 0
        assert state.last_cutoff_sequence == 10
        assert state.last_summary_at is not None


class TestProduct:
    """Test Product entity."""

    def test_product_creation(self):
        """Test creating a product."""
        product = Product(
            id=uuid4(),
            org_id=uuid4(),
            name="Test Product",
            description="A test product",
            key_features=["Feature 1", "Feature 2"],
        )

        assert product.name == "Test Product"
        assert len(product.key_features) == 2

    def test_product_requires_name(self):
        """Test that product requires name."""
        with pytest.raises(ValueError, match="name is required"):
            Product(
                id=uuid4(),
                org_id=uuid4(),
                name="",
            )

    def test_product_to_context_dict(self):
        """Test converting product to context dict."""
        product = Product(
            id=uuid4(),
            org_id=uuid4(),
            name="Test Product",
            description="A test product",
            key_features=["Feature 1"],
            target_audience="Developers",
        )

        ctx = product.to_context_dict()

        assert ctx["name"] == "Test Product"
        assert ctx["description"] == "A test product"
        assert ctx["key_features"] == ["Feature 1"]
        assert ctx["target_audience"] == "Developers"


class TestClient:
    """Test Client entity."""

    def test_client_creation(self):
        """Test creating a client."""
        client = Client(
            id=uuid4(),
            org_id=uuid4(),
            name="John Doe",
            company="Acme Corp",
            pain_points=["Cost", "Time"],
        )

        assert client.name == "John Doe"
        assert client.company == "Acme Corp"
        assert len(client.pain_points) == 2

    def test_client_to_context_dict(self):
        """Test converting client to context dict."""
        client = Client(
            id=uuid4(),
            org_id=uuid4(),
            name="Jane Doe",
            company="Tech Inc",
            pain_points=["Scalability"],
            goals=["Reduce costs"],
        )

        ctx = client.to_context_dict()

        assert ctx["name"] == "Jane Doe"
        assert ctx["company"] == "Tech Inc"
        assert ctx["pain_points"] == ["Scalability"]
        assert ctx["goals"] == ["Reduce costs"]
