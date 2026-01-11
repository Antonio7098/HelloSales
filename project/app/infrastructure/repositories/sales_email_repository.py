"""Sales email repository implementation."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.sales_email import SalesEmail
from app.infrastructure.database.models.hellosales import SalesEmailModel
from app.infrastructure.repositories.base import OrgScopedRepository


class SalesEmailRepositoryImpl(OrgScopedRepository[SalesEmailModel, SalesEmail]):
    """SQLAlchemy implementation of SalesEmailRepository."""

    model_class = SalesEmailModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, email_id: UUID, org_id: UUID) -> SalesEmail | None:
        """Get sales email by ID within org scope."""
        return await super().get_by_id(email_id, org_id)

    async def create(self, email: SalesEmail) -> SalesEmail:
        """Create a new sales email template."""
        model = SalesEmailModel.from_entity(email)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, email: SalesEmail) -> SalesEmail:
        """Update an existing sales email template."""
        model = SalesEmailModel.from_entity(email)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def list_by_org(
        self,
        org_id: UUID,
        active_only: bool = True,
        email_type: str | None = None,
        product_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SalesEmail]:
        """List sales email templates for an organization."""
        stmt = select(SalesEmailModel).where(SalesEmailModel.org_id == org_id)

        if active_only:
            stmt = stmt.where(SalesEmailModel.is_active == True)  # noqa: E712

        if email_type is not None:
            stmt = stmt.where(SalesEmailModel.email_type == email_type)

        if product_id is not None:
            stmt = stmt.where(SalesEmailModel.product_id == product_id)

        stmt = stmt.order_by(SalesEmailModel.name)
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def delete(self, email_id: UUID, org_id: UUID) -> bool:
        """Soft delete a sales email template (set is_active=False)."""
        stmt = (
            update(SalesEmailModel)
            .where(
                SalesEmailModel.id == email_id,
                SalesEmailModel.org_id == org_id,
            )
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def get_for_product(
        self,
        org_id: UUID,
        product_id: UUID,
        email_type: str = "cold_outreach",
    ) -> SalesEmail | None:
        """Get an email template for a product and type (returns first match)."""
        stmt = (
            select(SalesEmailModel)
            .where(
                SalesEmailModel.org_id == org_id,
                SalesEmailModel.product_id == product_id,
                SalesEmailModel.email_type == email_type,
                SalesEmailModel.is_active == True,  # noqa: E712
            )
            .order_by(SalesEmailModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def list_by_type(
        self,
        org_id: UUID,
        email_type: str,
        product_id: UUID | None = None,
    ) -> list[SalesEmail]:
        """List email templates by type."""
        stmt = (
            select(SalesEmailModel)
            .where(
                SalesEmailModel.org_id == org_id,
                SalesEmailModel.email_type == email_type,
                SalesEmailModel.is_active == True,  # noqa: E712
            )
        )

        if product_id is not None:
            stmt = stmt.where(SalesEmailModel.product_id == product_id)

        stmt = stmt.order_by(SalesEmailModel.created_at.desc())

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]
