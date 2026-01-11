"""Sales script repository implementation."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.sales_script import SalesScript
from app.infrastructure.database.models.hellosales import SalesScriptModel
from app.infrastructure.repositories.base import OrgScopedRepository


class SalesScriptRepositoryImpl(OrgScopedRepository[SalesScriptModel, SalesScript]):
    """SQLAlchemy implementation of SalesScriptRepository."""

    model_class = SalesScriptModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, script_id: UUID, org_id: UUID) -> SalesScript | None:
        """Get sales script by ID within org scope."""
        return await super().get_by_id(script_id, org_id)

    async def create(self, script: SalesScript) -> SalesScript:
        """Create a new sales script."""
        model = SalesScriptModel.from_entity(script)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, script: SalesScript) -> SalesScript:
        """Update an existing sales script."""
        model = SalesScriptModel.from_entity(script)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def list_by_org(
        self,
        org_id: UUID,
        active_only: bool = True,
        script_type: str | None = None,
        product_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SalesScript]:
        """List sales scripts for an organization."""
        stmt = select(SalesScriptModel).where(SalesScriptModel.org_id == org_id)

        if active_only:
            stmt = stmt.where(SalesScriptModel.is_active == True)  # noqa: E712

        if script_type is not None:
            stmt = stmt.where(SalesScriptModel.script_type == script_type)

        if product_id is not None:
            stmt = stmt.where(SalesScriptModel.product_id == product_id)

        stmt = stmt.order_by(SalesScriptModel.name)
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def delete(self, script_id: UUID, org_id: UUID) -> bool:
        """Soft delete a sales script (set is_active=False)."""
        stmt = (
            update(SalesScriptModel)
            .where(
                SalesScriptModel.id == script_id,
                SalesScriptModel.org_id == org_id,
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
        script_type: str = "cold_call",
    ) -> SalesScript | None:
        """Get a script for a product and type (returns first match)."""
        stmt = (
            select(SalesScriptModel)
            .where(
                SalesScriptModel.org_id == org_id,
                SalesScriptModel.product_id == product_id,
                SalesScriptModel.script_type == script_type,
                SalesScriptModel.is_active == True,  # noqa: E712
            )
            .order_by(SalesScriptModel.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None
