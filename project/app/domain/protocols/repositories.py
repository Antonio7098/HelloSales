"""Repository protocols - abstract interfaces for data access."""

from typing import Protocol
from uuid import UUID

from app.domain.entities import (
    Client,
    CompanyProfile,
    Interaction,
    Organization,
    OrganizationMembership,
    Product,
    SalesEmail,
    SalesScript,
    Session,
    SessionSummary,
    SummaryState,
    User,
)


class UserRepository(Protocol):
    """Abstract interface for user data access."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        ...

    async def get_by_auth_subject(self, auth_subject: str) -> User | None:
        """Get user by auth provider subject (e.g., WorkOS user ID)."""
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        ...

    async def create(self, user: User) -> User:
        """Create a new user."""
        ...

    async def update(self, user: User) -> User:
        """Update an existing user."""
        ...


class OrganizationRepository(Protocol):
    """Abstract interface for organization data access."""

    async def get_by_id(self, org_id: UUID) -> Organization | None:
        """Get organization by ID."""
        ...

    async def get_by_external_id(self, external_id: str) -> Organization | None:
        """Get organization by external ID (e.g., WorkOS org ID)."""
        ...

    async def create(self, org: Organization) -> Organization:
        """Create a new organization."""
        ...

    async def update(self, org: Organization) -> Organization:
        """Update an existing organization."""
        ...

    async def get_membership(
        self, user_id: UUID, org_id: UUID
    ) -> OrganizationMembership | None:
        """Get a user's membership in an organization."""
        ...

    async def create_membership(
        self, membership: OrganizationMembership
    ) -> OrganizationMembership:
        """Create an organization membership."""
        ...

    async def get_user_organizations(self, user_id: UUID) -> list[Organization]:
        """Get all organizations a user belongs to."""
        ...


class CompanyProfileRepository(Protocol):
    """Abstract interface for company profile data access."""

    async def get_by_org_id(self, org_id: UUID) -> CompanyProfile | None:
        """Get company profile for an organization."""
        ...

    async def create(self, profile: CompanyProfile) -> CompanyProfile:
        """Create a new company profile."""
        ...

    async def update(self, profile: CompanyProfile) -> CompanyProfile:
        """Update an existing company profile."""
        ...

    async def upsert(self, profile: CompanyProfile) -> CompanyProfile:
        """Create or update company profile."""
        ...


class SessionRepository(Protocol):
    """Abstract interface for session data access."""

    async def get_by_id(self, session_id: UUID) -> Session | None:
        """Get session by ID."""
        ...

    async def create(self, session: Session) -> Session:
        """Create a new session."""
        ...

    async def update(self, session: Session) -> Session:
        """Update an existing session."""
        ...

    async def list_by_user(
        self,
        user_id: UUID,
        org_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Session]:
        """List sessions for a user, optionally filtered by org."""
        ...

    async def increment_interaction_count(
        self, session_id: UUID, cost_cents: int = 0
    ) -> None:
        """Increment interaction count and optionally add cost."""
        ...


class SummaryRepository(Protocol):
    """Abstract interface for session summary data access."""

    async def get_latest(self, session_id: UUID) -> SessionSummary | None:
        """Get the latest summary for a session."""
        ...

    async def create_summary(
        self,
        session_id: UUID,
        summary_text: str,
        cutoff_sequence: int,
        token_count: int | None = None,
    ) -> SessionSummary:
        """Create a new summary for a session."""
        ...

    async def get_or_create_state(self, session_id: UUID) -> SummaryState:
        """Get or create summary state for a session."""
        ...

    async def update_state(self, state: SummaryState) -> SummaryState:
        """Update summary state."""
        ...


class InteractionRepository(Protocol):
    """Abstract interface for interaction data access."""

    async def get_by_id(self, interaction_id: UUID) -> Interaction | None:
        """Get interaction by ID."""
        ...

    async def create(
        self,
        session_id: UUID,
        role: str,
        content: str | None,
        input_type: str = "text",
        metadata: dict | None = None,
    ) -> Interaction:
        """Create a new interaction."""
        ...

    async def list_by_session(
        self,
        session_id: UUID,
        after_sequence: int = 0,
        limit: int | None = None,
    ) -> list[Interaction]:
        """List interactions for a session, optionally after a sequence number."""
        ...

    async def get_next_sequence_number(self, session_id: UUID) -> int:
        """Get the next sequence number for a session."""
        ...


class ProductRepository(Protocol):
    """Abstract interface for product data access."""

    async def get_by_id(self, product_id: UUID, org_id: UUID) -> Product | None:
        """Get product by ID within org scope."""
        ...

    async def create(self, product: Product) -> Product:
        """Create a new product."""
        ...

    async def update(self, product: Product) -> Product:
        """Update an existing product."""
        ...

    async def list_by_org(
        self,
        org_id: UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Product]:
        """List products for an organization."""
        ...

    async def delete(self, product_id: UUID, org_id: UUID) -> bool:
        """Soft delete a product (set is_active=False)."""
        ...


class ClientRepository(Protocol):
    """Abstract interface for client data access."""

    async def get_by_id(self, client_id: UUID, org_id: UUID) -> Client | None:
        """Get client by ID within org scope."""
        ...

    async def create(self, client: Client) -> Client:
        """Create a new client."""
        ...

    async def update(self, client: Client) -> Client:
        """Update an existing client."""
        ...

    async def list_by_org(
        self,
        org_id: UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Client]:
        """List clients for an organization."""
        ...

    async def delete(self, client_id: UUID, org_id: UUID) -> bool:
        """Soft delete a client (set is_active=False)."""
        ...


class SalesScriptRepository(Protocol):
    """Abstract interface for sales script data access."""

    async def get_by_id(self, script_id: UUID, org_id: UUID) -> SalesScript | None:
        """Get script by ID within org scope."""
        ...

    async def create(self, script: SalesScript) -> SalesScript:
        """Create a new script."""
        ...

    async def update(self, script: SalesScript) -> SalesScript:
        """Update an existing script."""
        ...

    async def list_by_org(
        self,
        org_id: UUID,
        product_id: UUID | None = None,
        client_id: UUID | None = None,
        script_type: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SalesScript]:
        """List scripts for an organization with optional filters."""
        ...

    async def delete(self, script_id: UUID, org_id: UUID) -> bool:
        """Soft delete a script (set is_active=False)."""
        ...


class SalesEmailRepository(Protocol):
    """Abstract interface for sales email data access."""

    async def get_by_id(self, email_id: UUID, org_id: UUID) -> SalesEmail | None:
        """Get email by ID within org scope."""
        ...

    async def create(self, email: SalesEmail) -> SalesEmail:
        """Create a new email."""
        ...

    async def update(self, email: SalesEmail) -> SalesEmail:
        """Update an existing email."""
        ...

    async def list_by_org(
        self,
        org_id: UUID,
        product_id: UUID | None = None,
        client_id: UUID | None = None,
        email_type: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SalesEmail]:
        """List emails for an organization with optional filters."""
        ...

    async def delete(self, email_id: UUID, org_id: UUID) -> bool:
        """Soft delete an email (set is_active=False)."""
        ...
