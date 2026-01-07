"""ChatPersistenceService for SRP compliance.

Handles database persistence for chat interactions and sessions.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Interaction, Session, SessionSummary, User

logger = logging.getLogger("chat")


class ChatPersistenceService:
    """Service for persisting chat interactions and managing session state.

    Responsibilities:
    - Save user and assistant messages as Interaction records
    - Update session interaction counts
    - Manage summary state (increment turns, generate summaries)
    - Handle onboarding completion
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize persistence service.

        Args:
            db: Database session
        """
        self.db = db

    async def save_interaction(
        self,
        *,
        session_id: uuid.UUID,
        role: str,
        content: str,
        message_id: uuid.UUID,
    ) -> Interaction:
        """Save a user or assistant message as an Interaction.

        Args:
            session_id: Session ID
            role: Message role ("user" or "assistant")
            content: Message content
            message_id: Client-provided message ID for deduplication

        Returns:
            The created Interaction record
        """
        interaction = Interaction(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.utcnow(),
        )
        self.db.add(interaction)
        await self.db.flush()
        logger.debug(
            f"Saved {role} interaction",
            extra={
                "service": "chat",
                "session_id": str(session_id),
                "interaction_id": str(message_id),
                "role": role,
            },
        )
        return interaction

    async def update_session_count(self, session_id: uuid.UUID) -> None:
        """Increment the interaction count for a session.

        Args:
            session_id: Session ID
        """
        result = await self.db.execute(
            select(Session.interaction_count).where(Session.id == session_id)
        )
        current_count = result.scalar_one_or_none() or 0
        await self.db.execute(
            select(Session).where(Session.id == session_id),
        )
        await self.db.execute(
            select(Session).where(Session.id == session_id),
        )
        await self.db.execute(
            "UPDATE session SET interaction_count = :count WHERE id = :id",
            {"count": current_count + 1, "id": session_id},
        )
        # Note: No explicit flush/commit here - let the calling service batch commits

    async def update_summary_state(
        self,
        session_id: uuid.UUID,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        _increment_turns: bool = True,
    ) -> SessionSummary | None:
        """Update summary state after each turn.

        Args:
            session_id: Session ID
            send_status: Optional callback for status updates
            increment_turns: Whether to increment turn counter (False for safety loops)

        Returns:
            The updated or newly created SessionSummary, or None if not ready
        """
        SUMMARY_THRESHOLD = 8  # Generate summary every 8 turns (4 exchange pairs)
        ALWAYS_INCLUDE_LAST_N = 6  # Always include last N messages

        # Get current state
        result = await self.db.execute(
            select(SessionSummary).where(SessionSummary.session_id == session_id),
        )
        summary_state = result.scalar_one_or_none()

        # Get current turn count (count of non-empty assistant messages after initial)
        interactions_result = await self.db.execute(
            select(Interaction)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.created_at.desc())
        )
        interactions = interactions_result.scalars().all()

        # Count assistant turns (assistant messages that aren't just "I'm having trouble...")
        assistant_turns = [
            i
            for i in interactions
            if i.role == "assistant"
            and i.content
            and not i.content.startswith("I'm having trouble")
        ]

        turn_count = len(assistant_turns)

        # If we don't have a summary state yet, create one
        if summary_state is None:
            summary_state = SessionSummary(
                session_id=session_id,
                summary_turn_count=turn_count,
                summary_text=None,
                cutoff_at=None,
                last_updated=datetime.utcnow(),
            )
            self.db.add(summary_state)
            await self.db.flush()
            logger.debug(
                "Created new summary state",
                extra={
                    "service": "chat",
                    "session_id": str(session_id),
                    "turn_count": turn_count,
                },
            )
            return summary_state

        # If we haven't reached the threshold, just update the turn count
        if turn_count <= summary_state.summary_turn_count:
            # This shouldn't happen normally, but handle gracefully
            logger.warning(
                "Turn count regression detected",
                extra={
                    "service": "chat",
                    "session_id": str(session_id),
                    "current_turns": turn_count,
                    "summary_turn_count": summary_state.summary_turn_count,
                },
            )
            return summary_state

        turns_since_summary = turn_count - summary_state.summary_turn_count

        # Check if we should generate a summary
        if turns_since_summary >= SUMMARY_THRESHOLD:
            # Get messages since the last cutoff
            cutoff_at = summary_state.cutoff_at or summary_state.last_updated

            messages_result = await self.db.execute(
                select(Interaction)
                .where(
                    Interaction.session_id == session_id,
                    Interaction.created_at > cutoff_at,
                )
                .order_by(Interaction.created_at.asc())
            )
            messages_to_summarize = messages_result.scalars().all()

            # Format messages for summary (last N messages before cutoff)
            await self.db.execute(
                select(Interaction)
                .where(
                    Interaction.session_id == session_id,
                    Interaction.created_at <= cutoff_at,
                )
                .order_by(Interaction.created_at.desc())
                .limit(ALWAYS_INCLUDE_LAST_N)
            )


            logger.info(
                "Ready to generate summary",
                extra={
                    "service": "chat",
                    "session_id": str(session_id),
                    "turn_count": turn_count,
                    "summary_turn_count": summary_state.summary_turn_count,
                    "messages_to_summarize": len(messages_to_summarize),
                },
            )

            # Emit event that summary is ready to generate
            if send_status:
                await send_status(
                    "summary",
                    "pending",
                    {
                        "turn_count": turn_count,
                        "summary_turn_count": summary_state.summary_turn_count,
                        "messages_to_summarize": len(messages_to_summarize),
                    },
                )

            # Update state to prevent duplicate summaries
            summary_state.summary_turn_count = turn_count
            summary_state.last_updated = datetime.utcnow()

            return summary_state

        # Just update the timestamp if not generating
        summary_state.last_updated = datetime.utcnow()
        return summary_state

    async def complete_onboarding(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Mark onboarding as completed for a user if this is an onboarding session.

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            True if onboarding was completed, False otherwise
        """
        result = await self.db.execute(
            select(Session.is_onboarding).where(Session.id == session_id)
        )
        is_onboarding = result.scalar_one_or_none()

        if not is_onboarding:
            return False

        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if user and not user.onboarding_completed:
            user.onboarding_completed = True
            await self.db.commit()
            logger.info(
                "Onboarding completed",
                extra={
                    "service": "chat",
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                },
            )
            return True

        return False

    async def get_interaction(self, interaction_id: uuid.UUID) -> Interaction | None:
        """Get an interaction by ID.

        Args:
            interaction_id: Interaction ID

        Returns:
            The Interaction record or None if not found
        """
        result = await self.db.execute(
            select(Interaction).where(Interaction.id == interaction_id)
        )
        return result.scalar_one_or_none()
