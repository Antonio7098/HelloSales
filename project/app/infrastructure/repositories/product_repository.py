"""Product repository implementation."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.product import Product
from app.infrastructure.database.models.product import ProductModel
from app.infrastructure.repositories.base import OrgScopedRepository


class ProductRepositoryImpl(OrgScopedRepository[ProductModel, Product]):
    """SQLAlchemy implementation of ProductRepository."""

    model_class = ProductModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, product_id: UUID, org_id: UUID) -> Product | None:
        """Get product by ID within org scope."""
        return await super().get_by_id(product_id, org_id)

    async def create(self, product: Product) -> Product:
        """Create a new product."""
        model = ProductModel.from_entity(product)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, product: Product) -> Product:
        """Update an existing product."""
        model = ProductModel.from_entity(product)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def list_by_org(
        self,
        org_id: UUID,
        active_only: bool = True,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Product]:
        """List products for an organization."""
        stmt = select(ProductModel).where(ProductModel.org_id == org_id)

        if active_only:
            stmt = stmt.where(ProductModel.is_active == True)  # noqa: E712

        if category is not None:
            stmt = stmt.where(ProductModel.category == category)

        stmt = stmt.order_by(ProductModel.name)
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def delete(self, product_id: UUID, org_id: UUID) -> bool:
        """Soft delete a product (set is_active=False)."""
        stmt = (
            update(ProductModel)
            .where(
                ProductModel.id == product_id,
                ProductModel.org_id == org_id,
            )
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def search(
        self,
        org_id: UUID,
        query: str,
        limit: int = 20,
    ) -> list[Product]:
        """Search products by name or description."""
        search_pattern = f"%{query}%"
        stmt = (
            select(ProductModel)
            .where(
                ProductModel.org_id == org_id,
                ProductModel.is_active == True,  # noqa: E712
                (
                    ProductModel.name.ilike(search_pattern)
                    | ProductModel.description.ilike(search_pattern)
                ),
            )
            .order_by(ProductModel.name)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]
