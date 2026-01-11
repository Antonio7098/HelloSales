"""Session service - manages chat sessions and interactions."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.interaction import Interaction
from app.domain.entities.session import Session, SummaryState
from app.domain.errors import NotFoundError, SessionNotFoundError, ValidationError
from app.infrastructure.repositories.interaction_repository import (
    InteractionRepositoryImpl,
)
from app.infrastructure.repositories.session_repository import SessionRepositoryImpl
from app.infrastructure.telemetry import get_logger

logger = get_logger(__name__)


class SessionService:
    """Service for managing chat sessions.

    Handles session lifecycle, interactions, and summary state.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = SessionRepositoryImpl(db)
        self.interaction_repo = InteractionRepositoryImpl(db)

    async def create_session(
        self,
        user_id: UUID,
        org_id: UUID | None = None,
        product_id: UUID | None = None,
        client_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new chat session.

        Args:
            user_id: User ID
            org_id: Organization ID
            product_id: Optional product context
            client_id: Optional client context
            metadata: Optional session metadata

        Returns:
            Created session
        """
        session = Session(
            id=uuid4(),
            user_id=user_id,
            org_id=org_id,
            product_id=product_id,
            client_id=client_id,
            state="active",
            started_at=datetime.now(UTC),
        )

        created = await self.session_repo.create(session)

        logger.info(
            "Session created",
            extra={
                "session_id": str(created.id),
                "user_id": str(user_id),
            },
        )

        return created

    async def get_session(self, session_id: UUID) -> Session:
        """Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session

        Raises:
            SessionNotFoundError: If session not found
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise SessionNotFoundError(
                message=f"Session {session_id} not found",
                details={"session_id": str(session_id)},
            )
        return session

    async def get_active_sessions(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[Session]:
        """Get active sessions for a user.

        Args:
            user_id: User ID
            limit: Maximum sessions to return

        Returns:
            List of active sessions
        """
        return await self.session_repo.list_by_user(
            user_id,
            state="active",
            limit=limit,
        )

    async def end_session(self, session_id: UUID) -> Session:
        """End a chat session.

        Args:
            session_id: Session ID

        Returns:
            Updated session

        Raises:
            SessionNotFoundError: If session not found
        """
        session = await self.get_session(session_id)

        if not session.is_active():
            raise ValidationError(
                code="SESSION_NOT_ACTIVE",
                message="Session is not active",
                details={"session_id": str(session_id), "state": session.state},
            )

        session.end()
        updated = await self.session_repo.update(session)

        logger.info(
            "Session ended",
            extra={
                "session_id": str(session_id),
                "duration_ms": session.duration_ms,
            },
        )

        return updated

    async def add_interaction(
        self,
        session_id: UUID,
        role: str,
        content: str | None,
        input_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> Interaction:
        """Add an interaction to a session.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            input_type: Input type (text, audio)
            metadata: Optional interaction metadata

        Returns:
            Created interaction

        Raises:
            SessionNotFoundError: If session not found
            ValidationError: If session not active
        """
        session = await self.get_session(session_id)

        if not session.is_active():
            raise ValidationError(
                code="SESSION_NOT_ACTIVE",
                message="Cannot add interaction to inactive session",
                details={"session_id": str(session_id), "state": session.state},
            )

        interaction = await self.interaction_repo.create(
            session_id=session_id,
            role=role,
            content=content,
            input_type=input_type,
            metadata=metadata,
        )

        # Update session interaction count
        await self.session_repo.increment_interaction_count(session_id)

        logger.debug(
            "Interaction added",
            extra={
                "session_id": str(session_id),
                "interaction_id": str(interaction.id),
                "role": role,
            },
        )

        return interaction

    async def get_conversation_history(
        self,
        session_id: UUID,
        after_sequence: int = 0,
        limit: int | None = None,
    ) -> list[Interaction]:
        """Get conversation history for a session.

        Args:
            session_id: Session ID
            after_sequence: Only return interactions after this sequence
            limit: Maximum interactions to return

        Returns:
            List of interactions in chronological order
        """
        return await self.interaction_repo.list_by_session(
            session_id,
            after_sequence=after_sequence,
            limit=limit,
        )

    async def get_recent_interactions(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list[Interaction]:
        """Get most recent interactions for a session.

        Args:
            session_id: Session ID
            limit: Maximum interactions to return

        Returns:
            List of recent interactions in chronological order
        """
        return await self.interaction_repo.get_recent(session_id, limit=limit)

    async def get_or_create_summary_state(
        self,
        session_id: UUID,
    ) -> SummaryState:
        """Get or create summary state for a session.

        Args:
            session_id: Session ID

        Returns:
            Summary state
        """
        state = await self.session_repo.get_summary_state(session_id)
        if state:
            return state

        # Create new summary state
        state = SummaryState(
            id=uuid4(),
            session_id=session_id,
            turns_since_summary=0,
        )
        return await self.session_repo.create_summary_state(state)

    async def check_summary_needed(
        self,
        session_id: UUID,
        threshold: int = 8,
    ) -> bool:
        """Check if a summary is needed for a session.

        Args:
            session_id: Session ID
            threshold: Turn threshold for summary

        Returns:
            True if summary is needed
        """
        state = await self.get_or_create_summary_state(session_id)
        return state.should_summarize(threshold)

    async def increment_turn_count(self, session_id: UUID) -> SummaryState:
        """Increment the turn count for summary tracking.

        Args:
            session_id: Session ID

        Returns:
            Updated summary state
        """
        state = await self.get_or_create_summary_state(session_id)
        state.increment_turn()
        return await self.session_repo.update_summary_state(state)

    async def record_summary(
        self,
        session_id: UUID,
        cutoff_sequence: int,
    ) -> SummaryState:
        """Record that a summary was generated.

        Args:
            session_id: Session ID
            cutoff_sequence: Sequence number up to which summary was made

        Returns:
            Updated summary state
        """
        state = await self.get_or_create_summary_state(session_id)
        state.reset_after_summary(cutoff_sequence)
        return await self.session_repo.update_summary_state(state)
