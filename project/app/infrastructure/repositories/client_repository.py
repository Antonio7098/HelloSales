"""Client repository implementation."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.client import Client
from app.infrastructure.database.models.client import ClientModel
from app.infrastructure.repositories.base import OrgScopedRepository


class ClientRepositoryImpl(OrgScopedRepository[ClientModel, Client]):
    """SQLAlchemy implementation of ClientRepository."""

    model_class = ClientModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, client_id: UUID, org_id: UUID) -> Client | None:
        """Get client by ID within org scope."""
        return await super().get_by_id(client_id, org_id)

    async def create(self, client: Client) -> Client:
        """Create a new client."""
        model = ClientModel.from_entity(client)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def update(self, client: Client) -> Client:
        """Update an existing client."""
        model = ClientModel.from_entity(client)
        merged = await self.session.merge(model)
        await self.session.flush()
        await self.session.refresh(merged)
        return merged.to_entity()

    async def list_by_org(
        self,
        org_id: UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Client]:
        """List clients for an organization."""
        stmt = select(ClientModel).where(ClientModel.org_id == org_id)

        if active_only:
            stmt = stmt.where(ClientModel.is_active == True)  # noqa: E712

        stmt = stmt.order_by(ClientModel.name)
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def delete(self, client_id: UUID, org_id: UUID) -> bool:
        """Soft delete a client (set is_active=False)."""
        stmt = (
            update(ClientModel)
            .where(
                ClientModel.id == client_id,
                ClientModel.org_id == org_id,
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
    ) -> list[Client]:
        """Search clients by name or company."""
        search_pattern = f"%{query}%"
        stmt = (
            select(ClientModel)
            .where(
                ClientModel.org_id == org_id,
                ClientModel.is_active == True,  # noqa: E712
                (
                    ClientModel.name.ilike(search_pattern)
                    | ClientModel.company.ilike(search_pattern)
                ),
            )
            .order_by(ClientModel.name)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]
