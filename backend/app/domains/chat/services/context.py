"""ChatContextService for SRP compliance.

Handles building LLM context from enrichers, history, and session data.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Interaction,
    Session,
    SessionSummary,
    SummaryState,
    UserMetaSummary,
)
from app.prompts import ONBOARDING_PROMPT
from app.schemas.assessment import AssessmentResponse
from app.schemas.skill import SkillContextForLLM

if TYPE_CHECKING:
    from app.ai.providers.base import LLMMessage

logger = logging.getLogger("chat")

# Context configuration
ALWAYS_INCLUDE_LAST_N = 6  # Always include last N messages for immediate context


@dataclass
class ChatContext:
    """Context for LLM conversation."""

    messages: list["LLMMessage"]
    summary_text: str | None = None
    cutoff_at: datetime | None = None


@dataclass
class PrefetchedEnrichers:
    """Container for enricher results that can be prefetched.

    This allows callers (e.g. voice pipeline) to start these DB-heavy queries
    earlier in the lifecycle (such as during STT) and then inject the results
    into context building instead of blocking on them later.
    """

    is_onboarding: bool | None
    meta_summary_text: str | None
    summary: SummaryState | None
    profile_text: str | None
    last_n: list[Interaction]


class ChatContextService:
    """Service for building LLM conversation context.

    Responsibilities:
    - Build chat context with system prompt, history, and summaries
    - Fetch enricher data (onboarding, meta_summary, profile, interactions)
    - Handle prefetching for latency-sensitive pipelines
    """

    def __init__(
        self,
        db: AsyncSession,
        system_prompt: str,
    ) -> None:
        """Initialize context service.

        Args:
            db: Database session
            system_prompt: System prompt to use for the conversation
        """
        self.db = db
        self.system_prompt = system_prompt

    async def build_context(
        self,
        session_id: uuid.UUID,
        skills_context: list[SkillContextForLLM] | None = None,
        platform: str | None = None,
        precomputed_assessment: AssessmentResponse | None = None,
        pipeline_run_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        prefetched: PrefetchedEnrichers | None = None,
    ) -> ChatContext:
        """Build conversation context from summary + recent messages.

        Always includes the last N messages for immediate context continuity,
        even right after a summary is generated.

        Args:
            session_id: Session ID
            precomputed_assessment: Optional assessment for the current/latest turn
            prefetched: Optional pre-fetched enricher data

        Returns:
            ChatContext with messages ready for LLM
        """
        return await self._build_context_with_enrichers(
            session_id=session_id,
            skills_context=skills_context,
            _platform=platform,
            precomputed_assessment=precomputed_assessment,
            _pipeline_run_id=pipeline_run_id,
            _request_id=request_id,
            _user_id=user_id,
            _org_id=org_id,
            prefetched=prefetched,
        )

    async def prefetch_enrichers(self, session_id: uuid.UUID) -> PrefetchedEnrichers:
        """Prefetch enricher data for a session without emitting pipeline events.

        This is used by latency-sensitive pipelines (e.g. voice) to start the
        DB-heavy summary/profile/meta_summary queries earlier (during STT), and
        then inject the results into context building instead of blocking later.
        """
        is_onboarding = await self._get_is_onboarding(session_id)
        meta_summary_text = await self._get_meta_summary_text(session_id)
        summary = await self._get_latest_summary(session_id)
        profile_text = await self._build_profile_context(session_id)
        last_n = await self._get_last_n_interactions(session_id, n=ALWAYS_INCLUDE_LAST_N)

        return PrefetchedEnrichers(
            is_onboarding=is_onboarding,
            meta_summary_text=meta_summary_text,
            summary=summary,
            profile_text=profile_text,
            last_n=last_n,
        )

    async def _build_context_with_enrichers(
        self,
        *,
        session_id: uuid.UUID,
        skills_context: list[SkillContextForLLM] | None,
        _platform: str | None,
        precomputed_assessment: AssessmentResponse | None,
        _pipeline_run_id: uuid.UUID | None,
        _request_id: uuid.UUID | None,
        _user_id: uuid.UUID | None,
        _org_id: uuid.UUID | None,
        prefetched: PrefetchedEnrichers | None = None,
    ) -> ChatContext:
        """Build conversation context from summary + recent messages."""
        from app.ai.providers.base import LLMMessage

        messages: list[LLMMessage] = []
        summary_text: str | None = None
        cutoff_at: datetime | None = None

        # If we already have prefetched results (e.g. from voice prefetch), reuse them
        if prefetched is not None:
            is_onboarding = prefetched.is_onboarding
            meta_summary_text = prefetched.meta_summary_text
            summary_state = prefetched.summary
            profile_text = prefetched.profile_text
            last_n = prefetched.last_n
        else:
            # Run independent DB queries in parallel for lower latency
            is_onboarding_task = self._get_is_onboarding(session_id)
            meta_summary_text_task = self._get_meta_summary_text(session_id)
            summary_state_task = self._get_latest_summary(session_id)
            profile_text_task = self._build_profile_context(session_id)
            last_n_task = self._get_last_n_interactions(session_id, n=ALWAYS_INCLUDE_LAST_N)

            is_onboarding, meta_summary_text, summary_state, profile_text, last_n = (
                await asyncio.gather(
                    is_onboarding_task,
                    meta_summary_text_task,
                    summary_state_task,
                    profile_text_task,
                    last_n_task,
                )
            )

        # Add system prompt
        if is_onboarding:
            messages.append(LLMMessage(role="system", content=ONBOARDING_PROMPT))
        else:
            messages.append(LLMMessage(role="system", content=self.system_prompt))

        # Add meta summary if available (from context-level summarization)
        if meta_summary_text:
            messages.append(
                LLMMessage(role="system", content=f"Context:\n{meta_summary_text}")
            )

        # Add profile context if available
        if profile_text:
            messages.append(LLMMessage(role="system", content=f"Profile:\n{profile_text}"))

        # Add skills context if available
        if skills_context:
            skills_text = "\n".join(
                f"- {skill.name}: {skill.description} (level {skill.level})"
                for skill in skills_context
            )
            messages.append(
                LLMMessage(role="system", content=f"Skills focus:\n{skills_text}")
            )

        # Add assessment context if available
        if precomputed_assessment:
            assessment_text = f"""Assessment of last response:
- Primary skill: {precomputed_assessment.skill_name}
- Rating: {precomputed_assessment.rating}/5
- Summary: {precomputed_assessment.summary}

Target skill: {precomputed_assessment.skill_name}"""
            messages.append(LLMMessage(role="system", content=assessment_text))

        # Add summary if available
        if summary_state and summary_state.summary_text:
            summary_text = summary_state.summary_text
            cutoff_at = summary_state.cutoff_at

            # Include summary and messages after cutoff
            messages.append(
                LLMMessage(role="system", content=f"Summary of earlier conversation:\n{summary_text}")
            )

        # Add recent messages (always include last N, even after summary)
        for interaction in last_n:
            messages.append(
                LLMMessage(role=interaction.role, content=interaction.content)
            )

        return ChatContext(
            messages=messages,
            summary_text=summary_text,
            cutoff_at=cutoff_at,
        )

    async def _get_is_onboarding(self, session_id: uuid.UUID) -> bool | None:
        """Check if session is an onboarding session."""
        result = await self.db.execute(
            select(Session.is_onboarding).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def _get_meta_summary_text(self, session_id: uuid.UUID) -> str | None:
        """Get meta-summary text for the session's user."""
        result = await self.db.execute(select(Session.user_id).where(Session.id == session_id))
        resolved_user_id = result.scalar_one_or_none()
        if not resolved_user_id:
            return None

        meta_result = await self.db.execute(
            select(UserMetaSummary.summary_text).where(
                UserMetaSummary.user_id == resolved_user_id
            )
        )
        text = meta_result.scalar_one_or_none()
        if not text:
            return None
        cleaned = str(text).strip()
        return cleaned or None

    async def _get_latest_summary(self, session_id: uuid.UUID) -> SummaryState | None:
        """Get the latest summary state for a session."""
        result = await self.db.execute(
            select(SessionSummary).where(SessionSummary.session_id == session_id)
        )
        summary_state = result.scalar_one_or_none()
        if summary_state:
            return SummaryState(
                summary_text=summary_state.summary_text,
                summary_turn_count=summary_state.summary_turn_count,
                cutoff_at=summary_state.cutoff_at,
            )
        return None

    async def _build_profile_context(self, session_id: uuid.UUID) -> str | None:
        """Build profile context for the session's user."""
        from app.models import User, UserProfile

        result = await self.db.execute(select(Session.user_id).where(Session.id == session_id))
        user_id = result.scalar_one_or_none()
        if not user_id:
            return None

        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return None

        # Build context from profile
        profile_result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()

        if not profile:
            return None

        # Format as readable text
        parts = []

        if profile.name:
            parts.append(f"Name: {profile.name}")

        if profile.native_language:
            parts.append(f"Native language: {profile.native_language}")

        if profile.target_language:
            parts.append(f"Target language: {profile.target_language}")

        if profile.learning_goals:
            parts.append(f"Goals: {profile.learning_goals}")

        if profile.proficiency_level:
            parts.append(f"Current level: {profile.proficiency_level}")

        if profile.additional_context:
            parts.append(f"Context: {profile.additional_context}")

        return "\n".join(parts) if parts else None

    async def _get_last_n_interactions(
        self,
        session_id: uuid.UUID,
        n: int = ALWAYS_INCLUDE_LAST_N,
    ) -> list[Interaction]:
        """Get the last N interactions for a session."""
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.created_at.desc())
            .limit(n)
        )
        # Return in chronological order (oldest first)
        return list(reversed(result.scalars().all()))


