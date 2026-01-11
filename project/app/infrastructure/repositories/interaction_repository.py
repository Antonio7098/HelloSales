"""Interaction repository implementation."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.interaction import Interaction
from app.infrastructure.database.models.interaction import InteractionModel
from app.infrastructure.repositories.base import BaseRepository


class InteractionRepositoryImpl(BaseRepository[InteractionModel, Interaction]):
    """SQLAlchemy implementation of InteractionRepository."""

    model_class = InteractionModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, interaction_id: UUID) -> Interaction | None:
        """Get interaction by ID."""
        return await super().get_by_id(interaction_id)

    async def create(
        self,
        session_id: UUID,
        role: str,
        content: str | None,
        input_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> Interaction:
        """Create a new interaction with auto-generated sequence number."""
        sequence_number = await self.get_next_sequence_number(session_id)

        interaction = Interaction(
            id=uuid4(),
            session_id=session_id,
            role=role,  # type: ignore
            sequence_number=sequence_number,
            content=content,
            input_type=input_type,  # type: ignore
            created_at=datetime.now(UTC),
        )

        model = InteractionModel.from_entity(interaction)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def list_by_session(
        self,
        session_id: UUID,
        after_sequence: int = 0,
        limit: int | None = None,
    ) -> list[Interaction]:
        """List interactions for a session, optionally after a sequence number."""
        stmt = select(InteractionModel).where(
            InteractionModel.session_id == session_id,
            InteractionModel.sequence_number > after_sequence,
        )

        stmt = stmt.order_by(InteractionModel.sequence_number)

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def get_recent(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list[Interaction]:
        """Get most recent interactions for a session."""
        stmt = (
            select(InteractionModel)
            .where(InteractionModel.session_id == session_id)
            .order_by(InteractionModel.sequence_number.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        # Reverse to get chronological order
        return [model.to_entity() for model in reversed(result.scalars().all())]

    async def get_next_sequence_number(self, session_id: UUID) -> int:
        """Get the next sequence number for a session."""
        stmt = select(func.max(InteractionModel.sequence_number)).where(
            InteractionModel.session_id == session_id
        )
        result = await self.session.execute(stmt)
        max_seq = result.scalar()
        return (max_seq or 0) + 1

    async def count_by_session(self, session_id: UUID) -> int:
        """Count interactions in a session."""
        stmt = select(func.count(InteractionModel.id)).where(
            InteractionModel.session_id == session_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
