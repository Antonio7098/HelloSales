"""Summary service for context window compression.

This module provides session-scoped summary functionality for managing
conversation context and memory within a single session.
"""

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import LLMMessage
from app.ai.providers.factory import get_llm_provider
from app.ai.substrate import ProviderCallLogger
from app.domains.summary.meta_summary import (
    META_SUMMARY_SYSTEM_PROMPT,
    MetaSummaryService,
)
from app.models import Interaction, SessionSummary, SummaryState

logger = logging.getLogger("summary")

# Default summary cadence: every N turn pairs (user + assistant = 2 interactions = 1 turn)
DEFAULT_SUMMARY_THRESHOLD = 4  # Generate summary every 4 turn pairs (8 messages)

# Rolling summary prompt - merges previous summary with new conversation
SUMMARY_PROMPT = """You are updating a coaching session summary with new conversation.

PREVIOUS SUMMARY:
{previous_summary}

NEW CONVERSATION TO INTEGRATE:
{conversation}

Create a MERGED summary that acts as session-scoped working memory.

You MUST include these sections with the exact headings:

1. SESSION STATE
   - Current focus / scenario (1 line)
   - Where the user is stuck or what they are improving (1 line)

2. RECENT SCENARIOS (DETAILED)
   - Keep only the last 2–4 scenarios in detail
   - For each scenario: Task + brief performance notes

3. EARLIER THIS SESSION (COMPRESSED)
   - If there were earlier scenarios beyond the recent ones, compress them into a single line

4. PATTERNS OBSERVED (THIS SESSION)
   - Recurring strengths and issues seen multiple times in this session
   - Keep concrete phrases/patterns (e.g., "overuses 'basically'", "run-on sentences")

5. WINS (THIS SESSION)
   - Breakthroughs or improvements; quote the user's words if possible

6. NEXT FOCUS
   - 1–2 highest-priority next coaching targets for continuing this session

7. META CANDIDATES (MAX 3 BULLETS)
   - Optional: only include items likely to matter across sessions
   - Examples: stable preferences ("prefers direct feedback"), repeated issues worth tracking long-term,
     meaningful milestones, or exercises they clearly liked/disliked

Rules:
- This summary is for THIS SESSION only (do not try to preserve every detail forever).
- Prefer recent details; compress older parts of this session.
- Keep specific phrases/patterns; avoid vague statements.
- Under 250 words.

Merged Summary:"""


class SummaryService:
    """Service for managing session summaries."""

    def __init__(
        self,
        db: AsyncSession,
        summary_threshold: int = DEFAULT_SUMMARY_THRESHOLD,
        model_id: str | None = None,
    ):
        """Initialize summary service.

        Args:
            db: Database session
            summary_threshold: Number of turn pairs before generating summary
            model_id: Override model ID (None = use configured default)
        """
        self.db = db
        self.summary_threshold = summary_threshold

        from app.config import get_settings

        settings = get_settings()
        self.llm = get_llm_provider(settings.summary_llm_provider)
        configured_model = (settings.summary_llm_model_id or "").strip()
        self._default_model_id = model_id or configured_model or self._get_default_model_id()
        self.call_logger = ProviderCallLogger(db)

    @staticmethod
    def _get_default_model_id() -> str:
        """Get the default model ID based on env configuration."""
        from app.config import get_settings

        settings = get_settings()
        choice = settings.llm_model_choice
        return settings.llm_model1_id if choice == "model1" else settings.llm_model2_id

    async def check_and_trigger(
        self,
        session_id: uuid.UUID,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
    ) -> SessionSummary | None:
        """Check if summary should be generated and trigger if needed.

        Args:
            session_id: Session ID
            send_status: Callback to send status updates

        Returns:
            New summary if generated, None otherwise
        """
        state = await self._get_summary_state(session_id)

        if not state:
            logger.debug(
                "No summary state found",
                extra={"service": "summary", "session_id": str(session_id)},
            )
            return None

        # Check if we've hit the threshold
        # turns_since counts individual messages, so divide by 2 for turn pairs
        turn_pairs = state.turns_since // 2

        if turn_pairs < self.summary_threshold:
            logger.debug(
                "Summary threshold not reached",
                extra={
                    "service": "summary",
                    "session_id": str(session_id),
                    "turn_pairs": turn_pairs,
                    "threshold": self.summary_threshold,
                },
            )
            return None

        logger.info(
            "Summary threshold reached, generating summary",
            extra={
                "service": "summary",
                "session_id": str(session_id),
                "turn_pairs": turn_pairs,
            },
        )

        return await self.generate_summary(session_id, send_status)

    async def generate_summary(
        self,
        session_id: uuid.UUID,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
    ) -> SessionSummary:
        """Generate a new summary for the session.

        Args:
            session_id: Session ID
            send_status: Callback to send status updates

        Returns:
            New SessionSummary record
        """
        start_time = time.time()

        if send_status:
            await send_status("summary", "started", None)

        try:
            # Get all interactions since last summary
            interactions = await self._get_interactions_for_summary(session_id)

            if not interactions:
                logger.warning(
                    "No interactions to summarize",
                    extra={"service": "summary", "session_id": str(session_id)},
                )
                if send_status:
                    await send_status("summary", "complete", {"skipped": True})
                raise ValueError("No interactions to summarize")

            # Build conversation text
            conversation_text = self._format_conversation(interactions)

            # Get previous summary for rolling merge
            previous_summary = await self._get_latest_summary_text(session_id)

            # Get current summary version
            current_version = await self._get_latest_version(session_id)
            new_version = current_version + 1

            # Generate summary via LLM (with fallback)
            # Pass previous summary for rolling merge
            messages = [
                LLMMessage(
                    role="user",
                    content=SUMMARY_PROMPT.format(
                        previous_summary=previous_summary
                        or "(This is the first summary for this session)",
                        conversation=conversation_text,
                    ),
                )
            ]

            response = await self._generate_with_fallback(messages, session_id)
            summary_text = response.content.strip()

            transcript_slice_limit = 30
            transcript_slice_items = interactions[-transcript_slice_limit:]
            transcript_slice = [
                {
                    "interactionId": str(i.id),
                    "messageId": str(i.message_id),
                    "role": i.role,
                    "content": i.content,
                    "createdAt": i.created_at.isoformat() if i.created_at else None,
                }
                for i in transcript_slice_items
            ]

            # Save summary (cutoff_idx left as None - we use created_at for ordering)
            summary = SessionSummary(
                session_id=session_id,
                version=new_version,
                text=summary_text,
                cutoff_idx=len(interactions),  # Number of interactions summarized
                token_count=response.tokens_out,
            )
            self.db.add(summary)

            # Reset summary state
            await self._reset_summary_state(session_id)

            try:
                await self.db.commit()
                await self.db.refresh(summary)
            except IntegrityError:
                await self.db.rollback()
                result = await self.db.execute(
                    select(SessionSummary)
                    .where(SessionSummary.session_id == session_id)
                    .order_by(SessionSummary.version.desc())
                    .limit(1)
                )
                existing = result.scalar_one_or_none()
                if existing is None:
                    raise

                duration_ms = int((time.time() - start_time) * 1000)
                if send_status:
                    await send_status(
                        "summary",
                        "complete",
                        {
                            "version": existing.version,
                            "interaction_count": len(interactions),
                            "summary_text": existing.text,
                            "duration_ms": duration_ms,
                            "transcript_slice": transcript_slice,
                            "transcript_slice_total": len(interactions),
                        },
                    )

                return existing

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Summary generated",
                extra={
                    "service": "summary",
                    "session_id": str(session_id),
                    "summary_id": str(summary.id),
                    "version": new_version,
                    "interaction_count": len(interactions),
                    "token_count": response.tokens_out,
                    "duration_ms": duration_ms,
                },
            )

            if send_status:
                await send_status(
                    "summary",
                    "complete",
                    {
                        "version": new_version,
                        "interaction_count": len(interactions),
                        "summary_text": summary_text,
                        "duration_ms": duration_ms,
                        "transcript_slice": transcript_slice,
                        "transcript_slice_total": len(interactions),
                    },
                )

            return summary

        except Exception as e:
            logger.error(
                "Summary generation failed",
                extra={
                    "service": "summary",
                    "session_id": str(session_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            if send_status:
                await send_status("summary", "error", {"error": str(e)})
            raise

    async def _get_summary_state(self, session_id: uuid.UUID) -> SummaryState | None:
        """Get summary state for a session."""
        result = await self.db.execute(
            select(SummaryState).where(SummaryState.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def _get_interactions_for_summary(
        self,
        session_id: uuid.UUID,
    ) -> list[Interaction]:
        """Get interactions that need to be summarized."""
        # Get latest summary cutoff
        result = await self.db.execute(
            select(SessionSummary)
            .where(SessionSummary.session_id == session_id)
            .order_by(SessionSummary.version.desc())
            .limit(1)
        )
        latest_summary = result.scalar_one_or_none()
        cutoff_time = latest_summary.created_at if latest_summary else None

        # Get interactions after cutoff
        query = select(Interaction).where(Interaction.session_id == session_id)
        if cutoff_time is not None:
            query = query.where(Interaction.created_at > cutoff_time)
        query = query.order_by(Interaction.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_latest_version(self, session_id: uuid.UUID) -> int:
        """Get the latest summary version for a session."""
        result = await self.db.execute(
            select(func.max(SessionSummary.version)).where(SessionSummary.session_id == session_id)
        )
        max_version = result.scalar()
        return max_version or 0

    async def _get_latest_summary_text(self, session_id: uuid.UUID) -> str | None:
        """Get the text of the most recent summary for rolling merge."""
        result = await self.db.execute(
            select(SessionSummary.text)
            .where(SessionSummary.session_id == session_id)
            .order_by(SessionSummary.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _reset_summary_state(self, session_id: uuid.UUID) -> None:
        """Reset turns_since counter after generating summary."""
        result = await self.db.execute(
            select(SummaryState).where(SummaryState.session_id == session_id)
        )
        state = result.scalar_one_or_none()
        if state:
            state.turns_since = 0

    def _format_conversation(self, interactions: list[Interaction]) -> str:
        """Format interactions as conversation text for summary prompt."""
        lines = []
        for interaction in interactions:
            role = "User" if interaction.role == "user" else "Coach"
            lines.append(f"{role}: {interaction.content}")
        return "\n\n".join(lines)

    async def _generate_with_fallback(
        self,
        messages: list[LLMMessage],
        session_id: uuid.UUID,
    ):
        """Generate LLM response with fallback to backup provider on failure.

        Args:
            messages: LLM messages to send
            session_id: Session ID for logging

        Returns:
            LLMResponse from primary or backup provider
        """
        from app.config import get_settings

        settings = get_settings()
        primary_error = None

        # Prepare prompt payload for observability
        prompt_payload = [{"role": m.role, "content": m.content} for m in messages]

        # Try primary provider
        try:
            response, _call_row = await self.call_logger.call_llm_generate(
                service="summary",
                provider=self.llm.name,
                model_id=self._default_model_id,
                prompt_messages=prompt_payload,
                call=lambda: self.llm.generate(
                    messages,
                    model=self._default_model_id,
                    max_tokens=500,
                ),
                session_id=session_id,
                user_id=None,
                interaction_id=None,
                request_id=None,
            )
            return response
        except Exception as exc:
            primary_error = exc
            logger.warning(
                "Primary LLM failed for summary, will try backup",
                extra={
                    "service": "summary",
                    "session_id": str(session_id),
                    "error": str(exc),
                    "backup_provider": settings.llm_backup_provider,
                },
            )

        # Try backup provider if configured
        backup_provider_name = settings.llm_backup_provider
        if backup_provider_name and backup_provider_name != self.llm.name:
            try:
                backup_llm = get_llm_provider(backup_provider_name)
                response, _call_row = await self.call_logger.call_llm_generate(
                    service="summary",
                    provider=backup_llm.name,
                    model_id=self._default_model_id,
                    prompt_messages=prompt_payload,
                    call=lambda: backup_llm.generate(
                        messages,
                        model=self._default_model_id,
                        max_tokens=500,
                    ),
                    session_id=session_id,
                    user_id=None,
                    interaction_id=None,
                    request_id=None,
                )

                logger.info(
                    "Backup LLM succeeded for summary",
                    extra={
                        "service": "summary",
                        "session_id": str(session_id),
                        "backup_provider": backup_provider_name,
                    },
                )
                return response
            except Exception as backup_exc:
                logger.error(
                    "Backup LLM also failed for summary",
                    extra={
                        "service": "summary",
                        "session_id": str(session_id),
                        "primary_error": str(primary_error),
                        "backup_error": str(backup_exc),
                        "backup_provider": backup_provider_name,
                    },
                )
                raise backup_exc from primary_error

        # No backup configured - raise original error
        raise primary_error  # type: ignore[misc]


__all__ = [
    "SummaryService",
    "MetaSummaryService",
    "DEFAULT_SUMMARY_THRESHOLD",
    "SUMMARY_PROMPT",
    "META_SUMMARY_SYSTEM_PROMPT",
]
