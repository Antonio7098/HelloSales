from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrganizationMembership
from app.models.sailwind_playbook import Client, Product, Strategy
from app.models.sailwind_practice import PracticeSession, RepAssignment
from app.models.session import Session

logger = logging.getLogger("sailwind")


ALLOWED_PRACTICE_SESSION_STATUSES = {"active", "ended", "cancelled"}


class PracticeConflictError(Exception):
    pass


class PracticeNotFoundError(Exception):
    pass


class PracticeValidationError(Exception):
    pass


class TerritoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rep_assignments(self, *, organization_id: UUID) -> list[RepAssignment]:
        stmt = (
            select(RepAssignment)
            .where(RepAssignment.organization_id == organization_id)
            .order_by(RepAssignment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_rep_assignments_for_user(
        self, *, organization_id: UUID, user_id: UUID
    ) -> list[RepAssignment]:
        stmt = (
            select(RepAssignment)
            .where(
                RepAssignment.organization_id == organization_id,
                RepAssignment.user_id == user_id,
            )
            .order_by(RepAssignment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_rep_assignment(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        product_id: UUID,
        client_id: UUID,
        strategy_id: UUID | None,
        min_practice_minutes: int | None,
        actor_user_id: UUID,
    ) -> RepAssignment:
        if min_practice_minutes is not None and min_practice_minutes <= 0:
            raise PracticeValidationError("min_practice_minutes must be positive")

        membership = await self.db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        if membership is None:
            raise PracticeNotFoundError("User is not a member of this organization")

        product = await self.db.scalar(
            select(Product).where(Product.id == product_id, Product.organization_id == organization_id)
        )
        if product is None:
            raise PracticeNotFoundError("Product not found")

        client = await self.db.scalar(
            select(Client).where(Client.id == client_id, Client.organization_id == organization_id)
        )
        if client is None:
            raise PracticeNotFoundError("Client not found")

        strategy: Strategy | None = None
        if strategy_id is not None:
            strategy = await self.db.scalar(
                select(Strategy).where(
                    Strategy.id == strategy_id,
                    Strategy.organization_id == organization_id,
                )
            )
            if strategy is None:
                raise PracticeNotFoundError("Strategy not found")
            if strategy.product_id != product.id or strategy.client_id != client.id:
                raise PracticeValidationError("Strategy does not match product/client")

        assignment = RepAssignment(
            organization_id=organization_id,
            user_id=user_id,
            product_id=product.id,
            client_id=client.id,
            strategy_id=(strategy.id if strategy is not None else None),
            min_practice_minutes=min_practice_minutes,
        )

        try:
            async with self.db.begin_nested():
                self.db.add(assignment)
                await self.db.flush()
        except IntegrityError as exc:
            raise PracticeConflictError("Rep assignment already exists") from exc

        logger.info(
            "Sailwind rep assignment created",
            extra={
                "service": "sailwind",
                "operation": "territory.rep_assignment.create",
                "status": "created",
                "organization_id": str(organization_id),
                "user_id": str(actor_user_id),
                "entity_id": str(assignment.id),
                "rep_user_id": str(user_id),
                "product_id": str(product.id),
                "client_id": str(client.id),
                "strategy_id": str(strategy.id) if strategy is not None else None,
            },
        )

        return assignment


class PracticeSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _require_membership(self, *, organization_id: UUID, user_id: UUID) -> None:
        membership = await self.db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        if membership is None:
            raise PracticeNotFoundError("User is not a member of this organization")

    async def list_practice_sessions_for_user(
        self, *, organization_id: UUID, user_id: UUID, limit: int = 50
    ) -> list[PracticeSession]:
        await self._require_membership(organization_id=organization_id, user_id=user_id)
        stmt = (
            select(PracticeSession)
            .where(
                PracticeSession.organization_id == organization_id,
                PracticeSession.user_id == user_id,
            )
            .order_by(PracticeSession.started_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def start_practice_session(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        strategy_id: UUID,
        rep_assignment_id: UUID | None,
        actor_user_id: UUID,
    ) -> PracticeSession:
        await self._require_membership(organization_id=organization_id, user_id=user_id)
        strategy = await self.db.scalar(
            select(Strategy).where(
                Strategy.id == strategy_id,
                Strategy.organization_id == organization_id,
            )
        )
        if strategy is None:
            raise PracticeNotFoundError("Strategy not found")

        rep_assignment: RepAssignment | None = None
        if rep_assignment_id is not None:
            rep_assignment = await self.db.scalar(
                select(RepAssignment).where(
                    RepAssignment.id == rep_assignment_id,
                    RepAssignment.organization_id == organization_id,
                    RepAssignment.user_id == user_id,
                )
            )
            if rep_assignment is None:
                raise PracticeNotFoundError("Rep assignment not found")
            if rep_assignment.strategy_id is not None and rep_assignment.strategy_id != strategy.id:
                raise PracticeValidationError("Rep assignment is pinned to a different strategy")
            if rep_assignment.product_id != strategy.product_id or rep_assignment.client_id != strategy.client_id:
                raise PracticeValidationError("Rep assignment does not match strategy")

        chat_session = Session(user_id=user_id)
        self.db.add(chat_session)
        await self.db.flush()

        practice = PracticeSession(
            organization_id=organization_id,
            user_id=user_id,
            strategy_id=strategy.id,
            rep_assignment_id=(rep_assignment.id if rep_assignment is not None else None),
            chat_session_id=chat_session.id,
            status="active",
            started_at=datetime.utcnow(),
        )
        self.db.add(practice)
        await self.db.flush()

        logger.info(
            "Sailwind practice session started",
            extra={
                "service": "sailwind",
                "operation": "practice.session.start",
                "status": "created",
                "organization_id": str(organization_id),
                "user_id": str(actor_user_id),
                "entity_id": str(practice.id),
                "rep_user_id": str(user_id),
                "strategy_id": str(strategy.id),
                "rep_assignment_id": str(rep_assignment.id) if rep_assignment is not None else None,
                "chat_session_id": str(chat_session.id),
            },
        )

        return practice

    async def end_practice_session(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        practice_session_id: UUID,
        actor_user_id: UUID,
        status: str = "ended",
    ) -> PracticeSession:
        resolved_status = (status or "").strip().lower()
        if resolved_status not in ALLOWED_PRACTICE_SESSION_STATUSES:
            raise PracticeValidationError("Invalid practice session status")

        practice = await self.db.scalar(
            select(PracticeSession).where(
                PracticeSession.id == practice_session_id,
                PracticeSession.organization_id == organization_id,
                PracticeSession.user_id == user_id,
            )
        )
        if practice is None:
            raise PracticeNotFoundError("Practice session not found")

        practice.status = resolved_status
        practice.ended_at = datetime.utcnow()
        await self.db.flush()

        logger.info(
            "Sailwind practice session ended",
            extra={
                "service": "sailwind",
                "operation": "practice.session.end",
                "status": "updated",
                "organization_id": str(organization_id),
                "user_id": str(actor_user_id),
                "entity_id": str(practice.id),
                "rep_user_id": str(user_id),
                "final_status": resolved_status,
            },
        )

        return practice
