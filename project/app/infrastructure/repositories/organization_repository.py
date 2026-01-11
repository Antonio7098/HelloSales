"""Organization repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.organization import Organization, OrganizationMembership
from app.infrastructure.database.models.organization import (
    OrganizationMembershipModel,
    OrganizationModel,
)
from app.infrastructure.repositories.base import BaseRepository


class OrganizationRepositoryImpl(BaseRepository[OrganizationModel, Organization]):
    """SQLAlchemy implementation of OrganizationRepository."""

    model_class = OrganizationModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, org_id: UUID) -> Organization | None:
        """Get organization by ID."""
        return await super().get_by_id(org_id)

    async def get_by_external_id(self, external_id: str) -> Organization | None:
        """Get organization by external ID (WorkOS org ID)."""
        stmt = select(OrganizationModel).where(
            OrganizationModel.external_id == external_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_by_slug(self, slug: str) -> Organization | None:
        """Get organization by slug."""
        stmt = select(OrganizationModel).where(OrganizationModel.slug == slug)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def create(self, org: Organization) -> Organization:
        """Create a new organization."""
        model = OrganizationModel.from_entity(org)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, org: Organization) -> Organization:
        """Update an existing organization."""
        model = OrganizationModel.from_entity(org)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def get_or_create_by_external_id(
        self,
        external_id: str,
        name: str,
        slug: str | None = None,
    ) -> tuple[Organization, bool]:
        """Get or create organization by external ID.

        Returns tuple of (organization, created).
        """
        existing = await self.get_by_external_id(external_id)
        if existing:
            return existing, False

        from uuid import uuid4

        org = Organization(
            id=uuid4(),
            external_id=external_id,
            name=name,
            slug=slug,
        )
        created = await self.create(org)
        return created, True


class OrganizationMembershipRepositoryImpl(
    BaseRepository[OrganizationMembershipModel, OrganizationMembership]
):
    """SQLAlchemy implementation of OrganizationMembershipRepository."""

    model_class = OrganizationMembershipModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, membership_id: UUID) -> OrganizationMembership | None:
        """Get membership by ID."""
        return await super().get_by_id(membership_id)

    async def get_by_user_and_org(
        self, user_id: UUID, org_id: UUID
    ) -> OrganizationMembership | None:
        """Get membership for a user in an organization."""
        stmt = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.user_id == user_id,
            OrganizationMembershipModel.organization_id == org_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def list_by_user(self, user_id: UUID) -> list[OrganizationMembership]:
        """List all memberships for a user."""
        stmt = (
            select(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.user_id == user_id)
            .order_by(OrganizationMembershipModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def list_by_org(self, org_id: UUID) -> list[OrganizationMembership]:
        """List all memberships for an organization."""
        stmt = (
            select(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.organization_id == org_id)
            .order_by(OrganizationMembershipModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def create(self, membership: OrganizationMembership) -> OrganizationMembership:
        """Create a new membership."""
        model = OrganizationMembershipModel.from_entity(membership)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, membership: OrganizationMembership) -> OrganizationMembership:
        """Update an existing membership."""
        model = OrganizationMembershipModel.from_entity(membership)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def delete(self, membership_id: UUID) -> bool:
        """Delete a membership."""
        stmt = select(OrganizationMembershipModel).where(
            OrganizationMembershipModel.id == membership_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.flush()
            return True
        return False
