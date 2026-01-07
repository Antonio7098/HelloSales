"""Sailwind playbook service for CRM-like sales functionality."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sailwind_playbook import (
    Client,
    ClientArchetype,
    Product,
    ProductArchetype,
    Strategy,
)

logger = logging.getLogger("sailwind")


ALLOWED_STRATEGY_STATUSES = {"draft", "active", "archived"}


class PlaybookConflictError(Exception):
    pass


class PlaybookNotFoundError(Exception):
    pass


class PlaybookValidationError(Exception):
    pass


class PlaybookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_product_archetypes(
        self,
        *,
        organization_id: UUID,
        include_archived: bool = False,
    ) -> list[ProductArchetype]:
        stmt = select(ProductArchetype).where(ProductArchetype.organization_id == organization_id)
        if not include_archived:
            stmt = stmt.where(ProductArchetype.archived_at.is_(None))
        stmt = stmt.order_by(ProductArchetype.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_product_archetype(
        self,
        *,
        organization_id: UUID,
        name: str,
        user_id: UUID,
    ) -> ProductArchetype:
        archetype = ProductArchetype(organization_id=organization_id, name=name)

        try:
            async with self.db.begin_nested():
                self.db.add(archetype)
                await self.db.flush()
        except IntegrityError as exc:
            raise PlaybookConflictError("Product archetype already exists") from exc

        logger.info(
            "Playbook product archetype created",
            extra={
                "service": "sailwind",
                "operation": "playbook.product_archetype.create",
                "status": "created",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(archetype.id),
            },
        )
        return archetype

    async def update_product_archetype(
        self,
        *,
        organization_id: UUID,
        archetype_id: UUID,
        user_id: UUID,
        name: str | None = None,
        archived: bool | None = None,
    ) -> ProductArchetype:
        archetype = await self.db.scalar(
            select(ProductArchetype).where(
                ProductArchetype.id == archetype_id,
                ProductArchetype.organization_id == organization_id,
            )
        )
        if archetype is None:
            raise PlaybookNotFoundError("Product archetype not found")

        if name is not None:
            archetype.name = name

        if archived is True:
            archetype.archived_at = datetime.utcnow()
        elif archived is False:
            archetype.archived_at = None

        try:
            async with self.db.begin_nested():
                await self.db.flush()
        except IntegrityError as exc:
            raise PlaybookConflictError("Product archetype already exists") from exc

        logger.info(
            "Playbook product archetype updated",
            extra={
                "service": "sailwind",
                "operation": "playbook.product_archetype.update",
                "status": "updated",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(archetype.id),
            },
        )
        return archetype

    async def list_client_archetypes(
        self,
        *,
        organization_id: UUID,
        include_archived: bool = False,
    ) -> list[ClientArchetype]:
        stmt = select(ClientArchetype).where(ClientArchetype.organization_id == organization_id)
        if not include_archived:
            stmt = stmt.where(ClientArchetype.archived_at.is_(None))
        stmt = stmt.order_by(ClientArchetype.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_client_archetype(
        self,
        *,
        organization_id: UUID,
        name: str,
        industry: str | None,
        user_id: UUID,
    ) -> ClientArchetype:
        archetype = ClientArchetype(organization_id=organization_id, name=name, industry=industry)

        try:
            async with self.db.begin_nested():
                self.db.add(archetype)
                await self.db.flush()
        except IntegrityError as exc:
            raise PlaybookConflictError("Client archetype already exists") from exc

        logger.info(
            "Playbook client archetype created",
            extra={
                "service": "sailwind",
                "operation": "playbook.client_archetype.create",
                "status": "created",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(archetype.id),
            },
        )
        return archetype

    async def update_client_archetype(
        self,
        *,
        organization_id: UUID,
        archetype_id: UUID,
        user_id: UUID,
        name: str | None = None,
        industry: str | None = None,
        archived: bool | None = None,
    ) -> ClientArchetype:
        archetype = await self.db.scalar(
            select(ClientArchetype).where(
                ClientArchetype.id == archetype_id,
                ClientArchetype.organization_id == organization_id,
            )
        )
        if archetype is None:
            raise PlaybookNotFoundError("Client archetype not found")

        if name is not None:
            archetype.name = name
        if industry is not None:
            archetype.industry = industry

        if archived is True:
            archetype.archived_at = datetime.utcnow()
        elif archived is False:
            archetype.archived_at = None

        try:
            async with self.db.begin_nested():
                await self.db.flush()
        except IntegrityError as exc:
            raise PlaybookConflictError("Client archetype already exists") from exc

        logger.info(
            "Playbook client archetype updated",
            extra={
                "service": "sailwind",
                "operation": "playbook.client_archetype.update",
                "status": "updated",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(archetype.id),
            },
        )
        return archetype

    async def list_products(self, *, organization_id: UUID, include_archived: bool = False) -> list[Product]:
        stmt = select(Product).where(Product.organization_id == organization_id)
        if not include_archived:
            stmt = stmt.where(Product.archived_at.is_(None))
        stmt = stmt.order_by(Product.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_product(
        self,
        *,
        organization_id: UUID,
        name: str,
        product_archetype_id: UUID | None,
        user_id: UUID,
    ) -> Product:
        resolved_archetype_id: UUID | None = None
        if product_archetype_id is not None:
            archetype = await self.db.scalar(
                select(ProductArchetype).where(
                    ProductArchetype.id == product_archetype_id,
                    ProductArchetype.organization_id == organization_id,
                )
            )
            if archetype is None:
                raise PlaybookNotFoundError("Product archetype not found")
            if archetype.archived_at is not None:
                raise PlaybookValidationError("Product archetype is archived")
            resolved_archetype_id = archetype.id

        product = Product(organization_id=organization_id, name=name, product_archetype_id=resolved_archetype_id)
        self.db.add(product)
        await self.db.flush()
        logger.info(
            "Playbook product created",
            extra={
                "service": "sailwind",
                "operation": "playbook.product.create",
                "status": "created",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(product.id),
            },
        )
        return product

    async def update_product(
        self,
        *,
        organization_id: UUID,
        product_id: UUID,
        user_id: UUID,
        name: str | None = None,
        product_archetype_id: UUID | None = None,
        product_archetype_id_provided: bool = False,
        archived: bool | None = None,
    ) -> Product:
        product = await self.db.scalar(
            select(Product).where(Product.id == product_id, Product.organization_id == organization_id)
        )
        if product is None:
            raise PlaybookNotFoundError("Product not found")

        if name is not None:
            product.name = name

        if product_archetype_id_provided:
            if product_archetype_id is None:
                product.product_archetype_id = None
            else:
                archetype = await self.db.scalar(
                    select(ProductArchetype).where(
                        ProductArchetype.id == product_archetype_id,
                        ProductArchetype.organization_id == organization_id,
                    )
                )
                if archetype is None:
                    raise PlaybookNotFoundError("Product archetype not found")
                if archetype.archived_at is not None:
                    raise PlaybookValidationError("Product archetype is archived")
                product.product_archetype_id = archetype.id

        if archived is True:
            product.archived_at = datetime.utcnow()
        elif archived is False:
            product.archived_at = None

        await self.db.flush()

        logger.info(
            "Playbook product updated",
            extra={
                "service": "sailwind",
                "operation": "playbook.product.update",
                "status": "updated",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(product.id),
            },
        )
        return product

    async def list_clients(self, *, organization_id: UUID, include_archived: bool = False) -> list[Client]:
        stmt = select(Client).where(Client.organization_id == organization_id)
        if not include_archived:
            stmt = stmt.where(Client.archived_at.is_(None))
        stmt = stmt.order_by(Client.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_client(
        self,
        *,
        organization_id: UUID,
        name: str,
        industry: str | None,
        client_archetype_id: UUID | None,
        user_id: UUID,
    ) -> Client:
        resolved_archetype_id: UUID | None = None
        if client_archetype_id is not None:
            archetype = await self.db.scalar(
                select(ClientArchetype).where(
                    ClientArchetype.id == client_archetype_id,
                    ClientArchetype.organization_id == organization_id,
                )
            )
            if archetype is None:
                raise PlaybookNotFoundError("Client archetype not found")
            if archetype.archived_at is not None:
                raise PlaybookValidationError("Client archetype is archived")
            resolved_archetype_id = archetype.id

        client = Client(
            organization_id=organization_id,
            name=name,
            industry=industry,
            client_archetype_id=resolved_archetype_id,
        )
        self.db.add(client)
        await self.db.flush()

        logger.info(
            "Playbook client created",
            extra={
                "service": "sailwind",
                "operation": "playbook.client.create",
                "status": "created",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(client.id),
            },
        )
        return client

    async def update_client(
        self,
        *,
        organization_id: UUID,
        client_id: UUID,
        user_id: UUID,
        name: str | None = None,
        industry: str | None = None,
        client_archetype_id: UUID | None = None,
        client_archetype_id_provided: bool = False,
        archived: bool | None = None,
    ) -> Client:
        client = await self.db.scalar(
            select(Client).where(Client.id == client_id, Client.organization_id == organization_id)
        )
        if client is None:
            raise PlaybookNotFoundError("Client not found")

        if name is not None:
            client.name = name
        if industry is not None:
            client.industry = industry

        if client_archetype_id_provided:
            if client_archetype_id is None:
                client.client_archetype_id = None
            else:
                archetype = await self.db.scalar(
                    select(ClientArchetype).where(
                        ClientArchetype.id == client_archetype_id,
                        ClientArchetype.organization_id == organization_id,
                    )
                )
                if archetype is None:
                    raise PlaybookNotFoundError("Client archetype not found")
                if archetype.archived_at is not None:
                    raise PlaybookValidationError("Client archetype is archived")
                client.client_archetype_id = archetype.id

        if archived is True:
            client.archived_at = datetime.utcnow()
        elif archived is False:
            client.archived_at = None

        await self.db.flush()

        logger.info(
            "Playbook client updated",
            extra={
                "service": "sailwind",
                "operation": "playbook.client.update",
                "status": "updated",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(client.id),
            },
        )
        return client

    async def list_strategies(
        self, *, organization_id: UUID, include_archived: bool = False
    ) -> list[Strategy]:
        stmt = select(Strategy).where(Strategy.organization_id == organization_id)
        if not include_archived:
            stmt = stmt.where(Strategy.status != "archived")
        stmt = stmt.order_by(Strategy.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_strategy(
        self,
        *,
        organization_id: UUID,
        product_id: UUID,
        client_id: UUID,
        strategy_text: str,
        status: str | None,
        user_id: UUID,
    ) -> Strategy:
        resolved_status = (status or "draft").strip()
        if resolved_status not in ALLOWED_STRATEGY_STATUSES:
            raise PlaybookValidationError("Invalid strategy status")

        product = await self.db.scalar(
            select(Product).where(Product.id == product_id, Product.organization_id == organization_id)
        )
        if product is None:
            raise PlaybookNotFoundError("Product not found")

        client = await self.db.scalar(
            select(Client).where(Client.id == client_id, Client.organization_id == organization_id)
        )
        if client is None:
            raise PlaybookNotFoundError("Client not found")

        strategy = Strategy(
            organization_id=organization_id,
            product_id=product.id,
            client_id=client.id,
            strategy_text=strategy_text,
            status=resolved_status,
        )

        try:
            async with self.db.begin_nested():
                self.db.add(strategy)
                await self.db.flush()
        except IntegrityError as exc:
            raise PlaybookConflictError("Strategy already exists for this product and client") from exc

        logger.info(
            "Playbook strategy created",
            extra={
                "service": "sailwind",
                "operation": "playbook.strategy.create",
                "status": "created",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(strategy.id),
                "product_id": str(product.id),
                "client_id": str(client.id),
            },
        )
        return strategy

    async def update_strategy(
        self,
        *,
        organization_id: UUID,
        strategy_id: UUID,
        user_id: UUID,
        strategy_text: str | None = None,
        status: str | None = None,
    ) -> Strategy:
        strategy = await self.db.scalar(
            select(Strategy).where(
                Strategy.id == strategy_id,
                Strategy.organization_id == organization_id,
            )
        )
        if strategy is None:
            raise PlaybookNotFoundError("Strategy not found")

        if strategy_text is not None:
            strategy.strategy_text = strategy_text

        if status is not None:
            next_status = status.strip()
            if next_status not in ALLOWED_STRATEGY_STATUSES:
                raise PlaybookValidationError("Invalid strategy status")
            strategy.status = next_status

        await self.db.flush()

        logger.info(
            "Playbook strategy updated",
            extra={
                "service": "sailwind",
                "operation": "playbook.strategy.update",
                "status": "updated",
                "organization_id": str(organization_id),
                "user_id": str(user_id),
                "entity_id": str(strategy.id),
            },
        )
        return strategy
