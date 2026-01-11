"""Session repository implementation."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.session import Session
from app.infrastructure.database.models.session import SessionModel
from app.infrastructure.repositories.base import BaseRepository


class SessionRepositoryImpl(BaseRepository[SessionModel, Session]):
    """SQLAlchemy implementation of SessionRepository."""

    model_class = SessionModel

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, session_id: UUID) -> Session | None:
        """Get session by ID."""
        return await super().get_by_id(session_id)

    async def create(self, session: Session) -> Session:
        """Create a new session."""
        return await super().create(session)

    async def update(self, session: Session) -> Session:
        """Update an existing session."""
        return await super().update(session)

    async def list_by_user(
        self,
        user_id: UUID,
        org_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Session]:
        """List sessions for a user, optionally filtered by org."""
        stmt = select(SessionModel).where(SessionModel.user_id == user_id)

        if org_id is not None:
            stmt = stmt.where(SessionModel.org_id == org_id)

        stmt = stmt.order_by(SessionModel.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return [model.to_entity() for model in result.scalars().all()]

    async def get_active_by_user(
        self,
        user_id: UUID,
        org_id: UUID | None = None,
    ) -> Session | None:
        """Get the most recent active session for a user."""
        stmt = select(SessionModel).where(
            SessionModel.user_id == user_id,
            SessionModel.state == "active",
        )

        if org_id is not None:
            stmt = stmt.where(SessionModel.org_id == org_id)

        stmt = stmt.order_by(SessionModel.created_at.desc()).limit(1)

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return model.to_entity()

    async def increment_interaction_count(
        self,
        session_id: UUID,
        cost_cents: int = 0,
    ) -> None:
        """Increment interaction count and optionally add cost."""
        stmt = (
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(
                interaction_count=SessionModel.interaction_count + 1,
                total_cost_cents=SessionModel.total_cost_cents + cost_cents,
                updated_at=datetime.now(UTC),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def end_session(self, session_id: UUID) -> Session | None:
        """End a session and calculate duration."""
        model = await self.session.get(SessionModel, session_id)
        if model is None:
            return None

        now = datetime.now(UTC)
        duration_ms = None
        if model.started_at:
            duration_ms = int((now - model.started_at).total_seconds() * 1000)

        model.state = "ended"
        model.ended_at = now
        model.duration_ms = duration_ms
        model.updated_at = now

        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()
