"""Base repository with common CRUD operations."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
EntityType = TypeVar("EntityType")


class BaseRepository(Generic[ModelType, EntityType]):
    """Base repository providing common CRUD operations.

    Subclasses should set:
    - model_class: The SQLAlchemy model class
    - Implement to_entity and from_entity methods
    """

    model_class: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> EntityType | None:
        """Get entity by primary key."""
        result = await self.session.get(self.model_class, id)
        if result is None:
            return None
        return result.to_entity()

    async def create(self, entity: EntityType) -> EntityType:
        """Create a new entity."""
        model = self.model_class.from_entity(entity)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, entity: EntityType) -> EntityType:
        """Update an existing entity."""
        model = self.model_class.from_entity(entity)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID."""
        result = await self.session.get(self.model_class, id)
        if result is None:
            return False
        await self.session.delete(result)
        await self.session.flush()
        return True

    async def exists(self, id: UUID) -> bool:
        """Check if entity exists."""
        result = await self.session.get(self.model_class, id)
        return result is not None


class OrgScopedRepository(BaseRepository[ModelType, EntityType]):
    """Repository for org-scoped entities.

    All queries are automatically scoped to the organization.
    """

    async def get_by_id(self, id: UUID, org_id: UUID) -> EntityType | None:
        """Get entity by ID within org scope."""
        stmt = select(self.model_class).where(
            self.model_class.id == id,
            self.model_class.org_id == org_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_entity()

    async def list_by_org(
        self,
        org_id: UUID,
        limit: int = 100,
        offset: int = 0,
        **filters: Any,
    ) -> list[EntityType]:
        """List entities for an organization."""
        stmt = select(self.model_class).where(self.model_class.org_id == org_id)

        # Apply additional filters
        for key, value in filters.items():
            if hasattr(self.model_class, key) and value is not None:
                stmt = stmt.where(getattr(self.model_class, key) == value)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def delete(self, id: UUID, org_id: UUID) -> bool:
        """Delete entity by ID within org scope."""
        stmt = select(self.model_class).where(
            self.model_class.id == id,
            self.model_class.org_id == org_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True
