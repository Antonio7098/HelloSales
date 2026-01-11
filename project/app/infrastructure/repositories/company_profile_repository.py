"""Company profile repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.company_profile import CompanyProfile
from app.infrastructure.database.models.company_profile import CompanyProfileModel
from app.infrastructure.repositories.base import OrgScopedRepository


class CompanyProfileRepositoryImpl(OrgScopedRepository[CompanyProfileModel, CompanyProfile]):
    """SQLAlchemy implementation of CompanyProfileRepository."""

    model_class = CompanyProfileModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, profile_id: UUID, org_id: UUID) -> CompanyProfile | None:
        """Get company profile by ID within org scope."""
        return await super().get_by_id(profile_id, org_id)

    async def get_by_org(self, org_id: UUID) -> CompanyProfile | None:
        """Get the company profile for an organization.

        Each organization has at most one company profile.
        """
        stmt = select(CompanyProfileModel).where(CompanyProfileModel.org_id == org_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def create(self, profile: CompanyProfile) -> CompanyProfile:
        """Create a new company profile."""
        model = CompanyProfileModel.from_entity(profile)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, profile: CompanyProfile) -> CompanyProfile:
        """Update an existing company profile."""
        model = CompanyProfileModel.from_entity(profile)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def upsert(self, profile: CompanyProfile) -> CompanyProfile:
        """Create or update the company profile for an organization."""
        existing = await self.get_by_org(profile.org_id)
        if existing:
            # Update existing profile with new values
            profile.id = existing.id
            return await self.update(profile)
        return await self.create(profile)

    async def delete(self, profile_id: UUID, org_id: UUID) -> bool:
        """Delete a company profile."""
        stmt = select(CompanyProfileModel).where(
            CompanyProfileModel.id == profile_id,
            CompanyProfileModel.org_id == org_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.flush()
            return True
        return False
