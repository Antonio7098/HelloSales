"""Chat service for handling text conversations with LLM."""

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.providers.base import LLMMessage, LLMProvider
from app.ai.providers.factory import get_llm_provider
from app.ai.stages.chat.llm_stream import LlmStreamFailure, LlmStreamStage
from app.ai.substrate import (
    PipelineEventLogger,
    ProviderCallLogger,
    get_circuit_breaker,
    handle_agent_output_runtime,
)
from app.ai.substrate.events import get_event_sink
from app.ai.substrate.policy.gateway import (
    PolicyCheckpoint,
    PolicyContext,
    PolicyDecision,
    PolicyGateway,
)
from app.ai.substrate.policy.guardrails import (
    GuardrailsCheckpoint,
    GuardrailsContext,
    GuardrailsDecision,
    GuardrailsStage,
)
from app.ai.validation import (
    emit_agent_output_validation_event,
    parse_agent_output,
)
from app.config import get_settings
from app.database import get_session_context
from app.infrastructure.pricing import estimate_llm_cost_cents
from app.models import (
    Assessment,
    Interaction,
    ProviderCall,
    Session,
    SessionSummary,
    SkillAssessment,
    SummaryState,
    User,
    UserMetaSummary,
    UserProfile,
)
from app.models.observability import PipelineRun
from app.prompts import ONBOARDING_PROMPT
from app.schemas.assessment import AssessmentResponse
from app.schemas.skill import SkillContextForLLM

if TYPE_CHECKING:
    pass

logger = logging.getLogger("chat")
profile_logger = logging.getLogger("profile")


class _LLMStreamFailure(Exception):
    def __init__(self, original: Exception, token_count: int) -> None:
        super().__init__(str(original))
        self.original = original
        self.token_count = token_count


# Context configuration
ALWAYS_INCLUDE_LAST_N = 6  # Always include last N messages for immediate context
SUMMARY_THRESHOLD = 8  # Generate summary every 8 turns (4 exchange pairs)


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


# System prompt variants for the AI coach
SYSTEM_PROMPT_V1 = """You are Eloquence, an AI speech coach helping users improve their communication skills.
You are warm, encouraging, and constructive. You provide specific, actionable feedback.

Conversation style:
- At the very beginning of a new conversation, get straight into coaching.
  Briefly introduce yourself as a coach and immediately ask what they would like to practise
  (for example, introductions, presentations, interviews, or everyday conversations).
- Assume the user has come here to work on their speaking. Default to concrete, coaching-focused
  responses rather than small talk.
- Keep messages short and to the point (roughly 2–4 sentences), focused on one or two actionable
  improvements at a time, and always oriented toward practice.
- Stay with the current exercise, question, or scenario and deepen it. Do not introduce new exercises,
  topics, or scenarios unless the user clearly asks to change focus or seems explicitly bored or stuck.
- When the user keeps working on the same thing, keep iterating on that same thing (asking follow-ups,
  refining, and improving it) instead of switching to a new area.

Feedback approach (graduated):
- First, use subtle hints or questions to help the user notice issues themselves
  (e.g., "How might you phrase that more concisely?" or "What word could replace 'thing' here?").
- If they don't self-correct, then provide explicit correction with the improved phrasing.
- This "hint first, then tell" approach builds awareness and retention.

Lexical focus:
- Prioritize natural word combinations (collocations, fixed phrases, idiomatic expressions)
  over isolated grammar rules. For example, "make a decision" not "do a decision".
- When correcting, highlight the specific phrase or word choice, not abstract grammar.
- Model native-like expressions by offering alternatives the user can immediately try.

When users practise speaking, you:
1. Acknowledge what they did well (be specific: quote their words)
2. Identify 1–2 specific, actionable areas for improvement (focus on phrases, not rules)
3. Offer a concrete rephrasing or technique they can try immediately
4. Keep responses concise but helpful"""


async def _enforce_llm_circuit_breaker(
    *,
    operation: str,
    provider: str,
    model_id: str | None,
    request_id: uuid.UUID | None,
    session_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    _org_id: uuid.UUID | None,
) -> bool:
    """Check and enforce LLM circuit breaker state.

    Returns:
        True if breaker is open and call should be denied, False if call can proceed.

    Raises:
        None - this function only returns a boolean and emits events.
    """
    breaker = get_circuit_breaker()

    if await breaker.is_open(operation=operation, provider=provider, model_id=model_id):
        # Emit denial event
        get_event_sink().try_emit(
            type="llm.breaker.denied",
            data={
                "operation": operation,
                "provider": provider,
                "model_id": model_id,
                "reason": "circuit_open",
            },
        )

        logger.warning(
            "LLM call denied by circuit breaker",
            extra={
                "service": "chat",
                "operation": operation,
                "provider": provider,
                "model_id": model_id,
                "session_id": str(session_id) if session_id else None,
                "user_id": str(user_id) if user_id else None,
                "request_id": str(request_id) if request_id else None,
            },
        )

        return True

    # Note the attempt for breaker state tracking
    await breaker.note_attempt(operation=operation, provider=provider, model_id=model_id)

    return False


def _get_safe_minimal_reply() -> str:
    """Return a safe minimal reply for total LLM failure."""
    return "I'm having trouble connecting right now. Please try again in a moment."

SYSTEM_PROMPT_V2 = """You're Eloquence, but talk like an old friend who's already mid-conversation with the user.

Conversation style:
- If they open with a greeting, greet them back warmly and then ask what they would like to practice.
- At the start of a new conversation, briefly reply, ask how they are doing, and ask if they want to jump into some practice.
- Only ask whether they want to jump into practice once at the start of a new conversation; once practice has begun, do not ask again.
- If they ask to practice something, do not ask for confirmation—just begin.
- Default to direct prompts like "Let's jump into some interview practice"—never say "I'll take your answer and give feedback" or outline a plan.
- Keep every message to one or two punchy sentences with zero waffle.
- Do not promot them to talk about random information. Stick to what is detailed in their profile, or encourage them to speak about topics without explicitly stating the words they should say.

Feedback:
- Quote one thing they nailed (use their words).
- Offer one improved sentence that nudges the weakest one or two areas while keeping most of their phrasing intact. No skill lists, no total rewrites.
- Explain to them briefly what the addition does and why they shoul duse it.
- Lead with gentle hints; only spell it out if they stall.
- You can mention one or two skills (pillars) when analysing, but not all at once.
- Do not use technical concepts. Keep the language simple and understandable. Do not say anaphora. Just say repetition.

General rules:
- Stay on the current exercise until they ask to switch topics.
- Do not analyse general greetings or meta chatter—wait for explicit consent to practice.
- Never list scores, tracked skills, or say "I'm your coach". They already know."""

DEFAULT_PROMPT_VERSION = "v1"
PROMPT_VARIANTS: dict[str, str] = {
    "v1": SYSTEM_PROMPT_V1,
    "v2": SYSTEM_PROMPT_V2,
}

# Backwards compatibility for tests and imports that still reference SYSTEM_PROMPT directly
SYSTEM_PROMPT = SYSTEM_PROMPT_V1


def resolve_system_prompt(version: str | None = None) -> str:
    """Return the configured system prompt, defaulting to v1."""

    key = version or DEFAULT_PROMPT_VERSION
    return PROMPT_VARIANTS.get(key, SYSTEM_PROMPT_V1)


@dataclass
class ChatContext:
    """Context for LLM conversation."""

    messages: list[LLMMessage]
    summary_text: str | None = None
    cutoff_at: datetime | None = None


class PersistInteractionsStage:
    def __init__(self, service: "ChatService") -> None:
        self._service = service

    async def persist_user_message(
        self,
        *,
        session_id: uuid.UUID,
        content: str,
        message_id: uuid.UUID,
    ) -> None:
        await self._service._save_interaction(
            session_id=session_id,
            role="user",
            content=content,
            message_id=message_id,
        )

    async def persist_assistant_message(
        self,
        *,
        session_id: uuid.UUID,
        content: str,
        message_id: uuid.UUID,
    ) -> None:
        await self._service._save_interaction(
            session_id=session_id,
            role="assistant",
            content=content,
            message_id=message_id,
        )


class ContextBuildStage:
    def __init__(self, service: "ChatService") -> None:
        self._service = service

    async def run(
        self,
        *,
        session_id: uuid.UUID,
        skills_context: list[SkillContextForLLM] | None,
        platform: str | None,
        precomputed_assessment: AssessmentResponse | None,
        pipeline_run_id: uuid.UUID | None,
        request_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
    ) -> ChatContext:
        return await self._service._build_context_with_enrichers(
            session_id=session_id,
            skills_context=skills_context,
            platform=platform,
            precomputed_assessment=precomputed_assessment,
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            user_id=user_id,
            org_id=org_id,
        )


class ChatService:
    """Service for handling chat messages and LLM interactions."""

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider,
        prompt_version: str | None = None,
    ):
        """Initialize chat service.

        Args:
            db: Database session (required)
            llm_provider: LLM provider (required - no factory fallback)
            prompt_version: Optional prompt version override
        """
        if llm_provider is None:
            raise ValueError("llm_provider is required. Use explicit injection or get_llm_provider() at the call site.")
        self.db = db
        self.llm = llm_provider
        self.call_logger = ProviderCallLogger(db)
        settings = get_settings()
        configured_version = getattr(settings, "chat_prompt_version", DEFAULT_PROMPT_VERSION)
        self.prompt_version = prompt_version or configured_version
        self.system_prompt = resolve_system_prompt(self.prompt_version)

    async def handle_message(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        message_id: uuid.UUID | None = None,
        assistant_message_id: uuid.UUID | None = None,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        send_token: Callable[[str], Any] | None = None,
        _request_id: str | None = None,  # Reserved for future tracing
        pipeline_run_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        _quality_mode: str = "fast",
        skills_context: list[SkillContextForLLM] | None = None,
        model_id: str | None = None,
        platform: str | None = None,
        precomputed_assessment: AssessmentResponse | None = None,
    ) -> tuple[str, uuid.UUID]:
        """Handle an incoming chat message.

        Args:
            session_id: Session ID
            user_id: User ID
            content: Message content
            message_id: Client-generated message ID for deduplication
            send_status: Callback to send status updates
            send_token: Callback to send streamed tokens
            model_id: Override LLM model ID (None = use provider default)
            precomputed_assessment: Optional assessment result to inject into context immediately

        Returns:
            Tuple of (full response content, assistant message ID)
        """
        start_time = time.time()
        if message_id is None:
            if pipeline_run_id is not None:
                message_id = uuid.uuid5(pipeline_run_id, "user")
            else:
                message_id = uuid.uuid4()
        if assistant_message_id is None:
            if pipeline_run_id is not None:
                assistant_message_id = uuid.uuid5(pipeline_run_id, "assistant")
            else:
                assistant_message_id = uuid.uuid4()

        logger.info(
            "Chat message received",
            extra={
                "service": "chat",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "message_id": str(message_id),
                "content_length": len(content),
            },
        )

        persist_stage = PersistInteractionsStage(self)
        await persist_stage.persist_user_message(
            session_id=session_id,
            content=content,
            message_id=message_id,
        )

        context_stage = ContextBuildStage(self)
        context = await context_stage.run(
            session_id=session_id,
            skills_context=skills_context,
            platform=platform,
            precomputed_assessment=precomputed_assessment,
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            user_id=user_id,
            org_id=org_id,
        )

        if pipeline_run_id is not None:
            gateway = PolicyGateway()
            policy_ctx = PolicyContext(
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                service="chat",
                trigger=None,
                behavior=None,
                quality_mode=None,
                intent="chat",
                prompt_tokens_estimate=(len("".join(m.content for m in context.messages)) // 4),
            )
            decision = await gateway.evaluate(
                checkpoint=PolicyCheckpoint.PRE_LLM, context=policy_ctx
            )
            self._policy_last_result = decision
            if decision.decision != PolicyDecision.ALLOW:
                safe_message = "Sorry — I can't help with that."
                await persist_stage.persist_assistant_message(
                    session_id=session_id,
                    content=safe_message,
                    message_id=assistant_message_id,
                )
                await self._update_session_count(session_id)
                await self._update_summary_state(session_id, send_status)
                return safe_message, assistant_message_id

            guardrails = GuardrailsStage()
            guardrails_ctx = GuardrailsContext(
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                service="chat",
                intent="chat",
                input_excerpt=(content[:5000] if content else None),
            )
            guardrails_result = await guardrails.evaluate(
                checkpoint=GuardrailsCheckpoint.PRE_LLM,
                context=guardrails_ctx,
            )
            if guardrails_result.decision != GuardrailsDecision.ALLOW:
                safe_message = "Sorry — I can't help with that."
                await persist_stage.persist_assistant_message(
                    session_id=session_id,
                    content=safe_message,
                    message_id=assistant_message_id,
                )
                await self._update_session_count(session_id)
                await self._update_summary_state(session_id, send_status)
                return safe_message, assistant_message_id

        # Send LLM started status with full prompt for debug visibility
        llm_stage_started_at = time.time()
        if send_status:
            # Format prompt for debug display (show more content for summaries)
            prompt_debug = [
                {
                    "role": msg.role,
                    "content": (
                        msg.content[:1500] + "..." if len(msg.content) > 1500 else msg.content
                    ),
                }
                for msg in context.messages
            ]
            await send_status(
                "llm",
                "started",
                {
                    "provider": self.llm.name,
                    "model": model_id,
                    "message_count": len(context.messages),
                    "has_summary": context.summary_text is not None,
                    "prompt": prompt_debug,
                },
            )

        # Stream LLM response with fallback
        (
            full_response,
            token_count,
            llm_provider,
            llm_model,
            ttft_ms,
            llm_provider_call_id,
        ) = await self._stream_with_fallback(
            messages=context.messages,
            model_id=model_id,
            session_id=session_id,
            stage_started_at=llm_stage_started_at,
            send_status=send_status,
            send_token=send_token,
            max_tokens=get_settings().policy_llm_max_tokens,
            user_id=user_id,
            request_id=request_id,
            pipeline_run_id=pipeline_run_id,
            org_id=org_id,
            interaction_id=None,
        )

        # Calculate metrics
        duration_ms = int((time.time() - start_time) * 1000)

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens_in = len("".join(m.content for m in context.messages)) // 4
        estimated_tokens_out = len(full_response) // 4

        if pipeline_run_id is not None:
            async with get_session_context() as obs_db:
                run = await obs_db.get(PipelineRun, pipeline_run_id)
                if run is not None:
                    run.ttft_ms = ttft_ms
                    run.tokens_in = estimated_tokens_in
                    run.tokens_out = token_count
                    stages = run.stages or {}
                    llm_stage = stages.get("llm") or {}
                    llm_stage.update(
                        {
                            "provider": llm_provider,
                            "model": llm_model,
                            "ttft_ms": ttft_ms,
                            "stream_token_count": token_count,
                        }
                    )
                    stages["llm"] = llm_stage
                    run.stages = stages
                    obs_db.add(run)

        # Estimate cost in HUNDREDTHS of cents for precision
        estimated_cost_cents = estimate_llm_cost_cents(
            provider=llm_provider,
            model=llm_model,
            tokens_in=estimated_tokens_in,
            tokens_out=estimated_tokens_out,
        )

        await persist_stage.persist_assistant_message(
            session_id=session_id,
            content=full_response,
            message_id=assistant_message_id,
        )

        assistant_interaction = await self.db.get(Interaction, assistant_message_id)

        parsed_agent_output, parse_error, attempted_parse = parse_agent_output(full_response)
        if attempted_parse and pipeline_run_id is not None:
            await emit_agent_output_validation_event(
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                success=parsed_agent_output is not None,
                error=parse_error,
                parsed=(
                    parsed_agent_output.model_dump(mode="json") if parsed_agent_output else None
                ),
                raw_excerpt=full_response[:5000],
            )

        if parsed_agent_output is not None:
            await handle_agent_output_runtime(
                db=self.db,
                agent_output=parsed_agent_output,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                service="chat",
            )

        try:
            call_row = await self.db.get(ProviderCall, llm_provider_call_id)
            if call_row is not None:
                call_row.output_parsed = (
                    parsed_agent_output.model_dump(mode="json")
                    if parsed_agent_output is not None
                    else None
                )
                call_row.tokens_in = estimated_tokens_in
                call_row.tokens_out = estimated_tokens_out
                call_row.cost_cents = estimated_cost_cents
                call_row.interaction_id = (
                    assistant_interaction.id if assistant_interaction else assistant_message_id
                )

            if assistant_interaction is not None:
                assistant_interaction.llm_provider_call_id = llm_provider_call_id
            await self.db.commit()
        except Exception:  # pragma: no cover - defensive path
            logger.exception("Failed to finalize chat provider call")

        # Update session interaction count
        await self._update_session_count(session_id)

        # Update summary state (increment turns) and emit cadence info
        await self._update_summary_state(session_id, send_status)

        # If this was an onboarding session, mark onboarding as completed for the user
        result = await self.db.execute(
            select(Session.is_onboarding).where(Session.id == session_id)
        )
        is_onboarding = result.scalar_one_or_none()
        if is_onboarding:
            await self.db.execute(select(User).where(User.id == user_id))
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
        logger.info(
            "Chat message complete",
            extra={
                "service": "chat",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "assistant_message_id": str(assistant_message_id),
                "response_length": len(full_response),
                "token_count": token_count,
                "duration_ms": duration_ms,
            },
        )

        return full_response, assistant_message_id

    async def handle_message_dag(
        self,
        content: str,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        message_id: uuid.UUID | None = None,
        assistant_message_id: uuid.UUID | None = None,
        _request_id: str | None = None,
        pipeline_run_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        interaction_id: uuid.UUID | None = None,
        topology: str = "chat_fast",
        behavior: str = "practice",
        skills_context: list[SkillContextForLLM] | None = None,
        model_id: str | None = None,
        platform: str | None = None,
        skill_ids: list[str] | None = None,
        db: AsyncSession | None = None,
        send_status: Callable | None = None,
        send_token: Callable | None = None,
    ) -> tuple[str, uuid.UUID]:
        """Handle an incoming chat message using the DAG orchestrator.

        .. deprecated::
            This method is deprecated. Use :class:`ChatPipelineService` instead.
            It provides better separation of concerns between pipeline orchestration
            and core chat operations.

        This method now delegates to ChatPipelineService for DAG-based processing.
        """
        from app.domains.chat.pipeline_service import ChatPipelineService

        # Use provided db or fall back to self.db
        session_db = db or self.db

        pipeline_service = ChatPipelineService(chat_service=self, db=session_db)
        return await pipeline_service.handle_message_dag(
            content=content,
            session_id=session_id,
            user_id=user_id,
            message_id=message_id,
            assistant_message_id=assistant_message_id,
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            org_id=org_id,
            interaction_id=interaction_id,
            topology=topology,
            behavior=behavior,
            skills_context=skills_context,
            model_id=model_id,
            platform=platform,
            skill_ids=skill_ids,
            send_status=send_status,
            send_token=send_token,
        )

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
        """Public entry point for building LLM context.

        If `prefetched` is provided, uses precomputed enricher results instead of
        re-running the DB-heavy queries. Callers like the voice pipeline can
        start these earlier (e.g. during STT) and pass them here.
        """

        return await self._build_context_with_enrichers(
            session_id=session_id,
            skills_context=skills_context,
            platform=platform,
            precomputed_assessment=precomputed_assessment,
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            user_id=user_id,
            org_id=org_id,
            prefetched=prefetched,
        )

    async def prefetch_enrichers(self, session_id: uuid.UUID) -> PrefetchedEnrichers:
        """Prefetch enricher data for a session without emitting pipeline events.

        This is used by latency-sensitive pipelines (e.g. voice) to start the
        DB-heavy summary/profile/meta_summary queries earlier (during STT), and
        then inject the results into context building instead of blocking later.
        """

        settings = get_settings()

        async def _get_is_onboarding() -> bool | None:
            result = await self.db.execute(
                select(Session.is_onboarding).where(Session.id == session_id)
            )
            return result.scalar_one_or_none()

        async def _get_meta_summary_text() -> str | None:
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

        is_onboarding = await _get_is_onboarding()
        if getattr(settings, "context_enricher_meta_summary_enabled", True):
            meta_summary_text = await _get_meta_summary_text()
        else:
            meta_summary_text = None
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
        platform: str | None,
        precomputed_assessment: AssessmentResponse | None,
        pipeline_run_id: uuid.UUID | None,
        request_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        prefetched: PrefetchedEnrichers | None = None,
    ) -> ChatContext:
        """Build conversation context from summary + recent messages.

        Always includes the last N messages for immediate context continuity,
        even right after a summary is generated.

        Args:
            session_id: Session ID
            precomputed_assessment: Optional assessment for the current/latest turn
                                    (used in accurate pipeline mode).

        Returns:
            ChatContext with messages ready for LLM
        """
        messages: list[LLMMessage] = []

        settings = get_settings()

        async def _emit_pipeline_event(
            *,
            type: str,
            data: dict | None,
        ) -> None:
            if pipeline_run_id is None:
                return
            async with get_session_context() as obs_db:
                event_logger = PipelineEventLogger(obs_db)
                await event_logger.emit(
                    pipeline_run_id=pipeline_run_id,
                    type=type,
                    request_id=request_id,
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                    data=data,
                )

        async def _enricher(
            name: str,
            enabled: bool,
            fn: Callable[[], Any],
        ) -> Any:
            start = time.time()
            await _emit_pipeline_event(
                type=f"enricher.{name}.started",
                data={"enabled": enabled},
            )

            if not enabled:
                await _emit_pipeline_event(
                    type=f"enricher.{name}.completed",
                    data={"enabled": False, "status": "skipped", "duration_ms": 0},
                )
                return None

            status = "complete"
            error: str | None = None
            result: Any = None
            try:
                result = await fn()
            except Exception as exc:  # pragma: no cover - defensive
                status = "error"
                error = str(exc)
                result = None
            duration_ms = int((time.time() - start) * 1000)

            payload: dict[str, Any] = {
                "enabled": True,
                "status": status,
                "duration_ms": duration_ms,
            }
            if error is not None:
                payload["error"] = error
            await _emit_pipeline_event(
                type=f"enricher.{name}.completed",
                data=payload,
            )

            return result

        # If we already have prefetched results (e.g. from voice prefetch), reuse them
        # to avoid re-running the DB-heavy queries.
        if prefetched is not None:
            is_onboarding = prefetched.is_onboarding
            meta_summary_text = prefetched.meta_summary_text
            summary = prefetched.summary
            profile_text = prefetched.profile_text
            last_n = prefetched.last_n
        else:
            logger.info(
                "[PREFETCH] No prefetched data - running inline enricher queries",
                extra={"service": "chat", "session_id": str(session_id)},
            )

            # Run independent DB queries in parallel for lower latency
            async def _get_is_onboarding() -> bool | None:
                result = await self.db.execute(
                    select(Session.is_onboarding).where(Session.id == session_id)
                )
                return result.scalar_one_or_none()

            async def _get_meta_summary_text() -> str | None:
                result = await self.db.execute(
                    select(Session.user_id).where(Session.id == session_id)
                )
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

            # Run sequentially to avoid concurrent database access issues with async sessions
            is_onboarding = await _get_is_onboarding()
            meta_summary_text = await _enricher(
                "meta_summary",
                bool(getattr(settings, "context_enricher_meta_summary_enabled", True)),
                _get_meta_summary_text,
            )
            summary = await _enricher(
                "summary",
                bool(getattr(settings, "context_enricher_summary_enabled", True)),
                lambda: self._get_latest_summary(session_id),
            )
            profile_text = await _enricher(
                "profile",
                bool(getattr(settings, "context_enricher_profile_enabled", True)),
                lambda: self._build_profile_context(session_id),
            )
            last_n = await self._get_last_n_interactions(session_id, n=ALWAYS_INCLUDE_LAST_N)

        # Base system prompt selection
        # Onboarding sessions should not include the general coaching system prompt,
        # Build messages in optimal order for Groq caching:
        # 1. Most static (system prompts, platform hints)
        # 2. Less dynamic (skills, profile, meta summaries)
        # 3. Most dynamic (conversation history, assessments)

        # 1. SYSTEM PROMPTS (most static - put first for cache hits)
        if is_onboarding:
            messages.append(LLMMessage(role="system", content=ONBOARDING_PROMPT))
        else:
            messages.append(LLMMessage(role="system", content=self.system_prompt))

        # Platform-aware hint (semi-static)
        if is_onboarding:
            if platform == "web":
                messages.append(
                    LLMMessage(
                        role="system",
                        content=(
                            "The user is using the web / laptop version of the app. "
                            "When you explain controls, it is OK to mention that audio may be "
                            "blocked by the browser and that they should click the 'Enable audio' "
                            "banner if they cannot hear you. You can also mention keyboard "
                            "shortcuts where relevant: Arrow Down moves to the Session view, "
                            "Arrow Up moves to the Profile / Progress view, and Arrow Right moves "
                            "to the Manual view. Do not talk about hardware back buttons or "
                            "mobile-only OS gestures."
                        ),
                    )
                )
            elif platform == "native":
                messages.append(
                    LLMMessage(
                        role="system",
                        content=(
                            "The user is using the native mobile app. Focus on touch gestures "
                            "like swiping between views. Do not talk about browser audio "
                            "permission banners or keyboard shortcuts."
                        ),
                    )
                )

        # 2. CONTEXT DATA (less dynamic than conversation history)

        # Skills context (changes less frequently than conversation)
        skills_enabled = bool(getattr(settings, "context_enricher_skills_enabled", True))
        if skills_context and skills_enabled and not is_onboarding:
            # Build a compact description of tracked skills and next-level goals
            lines: list[str] = []
            for ctx in skills_context:
                level_desc = f"current level {ctx.current_level}"
                if ctx.next_level is not None:
                    level_desc += f", next level {ctx.next_level}"
                line_parts = [f"- {ctx.title} ({level_desc})"]

                if ctx.current_level_examples:
                    current_examples = ", ".join(ctx.current_level_examples[:3])
                    line_parts.append(f"  Current examples: {current_examples}")

                if ctx.next_level_criteria:
                    line_parts.append(f"  Next focus: {ctx.next_level_criteria}")

                if ctx.next_level_examples:
                    next_examples = ", ".join(ctx.next_level_examples[:3])
                    line_parts.append(f"  Next-level examples: {next_examples}")

                lines.append("\n".join(line_parts))

            skills_text = "\n".join(lines)
            messages.append(
                LLMMessage(
                    role="system",
                    content=(
                        "User is practicing the following tracked skills. "
                        "Tailor your coaching and feedback to these skills and gently "
                        "nudge the user toward the next level criteria.\n"
                        f"{skills_text}"
                    ),
                )
            )

        # Profile context (user-specific but relatively stable)
        if profile_text and not is_onboarding:
            messages.append(LLMMessage(role="system", content=profile_text))

        # Meta summary (user-specific, changes across sessions)
        if meta_summary_text:
            messages.append(
                LLMMessage(
                    role="system",
                    content=f"[User meta summary (cross-session): {meta_summary_text}]",
                )
            )

        # Conversation summary (session-specific)
        summary_text = None
        cutoff_at = None
        if summary:
            summary_text = summary.text
            cutoff_at = summary.created_at
            messages.append(
                LLMMessage(
                    role="system",
                    content=f"[Previous conversation summary: {summary_text}]",
                )
            )

        # 3. CONVERSATION HISTORY (most dynamic - put last for cache efficiency)
        after_summary = await self._get_recent_interactions(
            session_id,
            after_cutoff=cutoff_at,
        )

        # last_n was already fetched in parallel above
        # Merge: prefer after_summary order, add any from last_n not already included
        seen_ids = {i.id for i in after_summary}
        merged = list(after_summary)

        for interaction in last_n:
            if interaction.id not in seen_ids:
                merged.append(interaction)
                seen_ids.add(interaction.id)

        # Sort by created_at to maintain chronological order
        merged.sort(key=lambda i: i.created_at)

        # Fetch assessments for these interactions in ONE query (no N+1)
        interaction_ids = [i.id for i in merged if i.role == "user"]
        assessments_by_interaction = await self._get_assessments_for_interactions(interaction_ids)

        # Add interactions to context with interleaved assessments
        for interaction in merged:
            messages.append(
                LLMMessage(
                    role=interaction.role,
                    content=interaction.content,
                )
            )
            # Inject assessment right after the user message it assessed
            if interaction.role == "user" and interaction.id in assessments_by_interaction:
                assessment_text = self._format_assessment_context(
                    assessments_by_interaction[interaction.id]
                )
                if assessment_text:
                    messages.append(LLMMessage(role="system", content=assessment_text))
            elif (
                interaction.role == "user" and precomputed_assessment and interaction == merged[-1]
            ):
                # If we have a precomputed assessment for the latest user message, use it
                assessment_text = self._format_pydantic_assessment_context(precomputed_assessment)
                if assessment_text:
                    messages.append(LLMMessage(role="system", content=assessment_text))

        logger.debug(
            "Context built",
            extra={
                "service": "chat",
                "session_id": str(session_id),
                "message_count": len(messages),
                "has_summary": summary is not None,
                "after_summary_count": len(after_summary),
                "last_n_count": len(last_n),
                "merged_count": len(merged),
                "has_precomputed": precomputed_assessment is not None,
            },
        )

        return ChatContext(
            messages=messages,
            summary_text=summary_text,
            cutoff_at=cutoff_at,
        )

    async def _build_profile_context(self, session_id: uuid.UUID) -> str | None:
        """Build a compact profile context string for the user, if available.

        Looks up the user for the given session and loads their UserProfile. The
        result is a short system message describing the user's bio, goal and focus areas,
        suitable for injection into the LLM prompt.
        """

        # Resolve user_id from session
        result = await self.db.execute(select(Session.user_id).where(Session.id == session_id))
        user_id = result.scalar_one_or_none()
        if not user_id:
            return None

        prof_result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = prof_result.scalar_one_or_none()

        if not profile:
            profile_logger.debug(
                "No profile for user",
                extra={"service": "profile", "user_id": str(user_id)},
            )
            return None

        lines: list[str] = ["User Profile:"]

        if profile.name:
            lines.append(f"- Name: {profile.name}")

        if profile.bio:
            bio_clean = str(profile.bio).strip()
            if bio_clean:
                lines.append(f"- Bio: {bio_clean}")

        def _format_title_desc(label: str, data: dict | None) -> str | None:
            if not isinstance(data, dict):
                return None
            title = str(data.get("title") or "").strip()
            desc = str(data.get("description") or "").strip()
            if title and desc:
                return f"- {label}: {title} — {desc}"
            if title:
                return f"- {label}: {title}"
            if desc:
                return f"- {label}: {desc}"
            return None

        goal_line = _format_title_desc("Goal", profile.goal)
        if goal_line:
            lines.append(goal_line)

        raw_contexts = profile.contexts
        if isinstance(raw_contexts, dict):
            title = str(raw_contexts.get("title") or "").strip()
            desc = str(raw_contexts.get("description") or "").strip()
            if title and desc:
                lines.append(f"- Speaking context: {title} — {desc}")
            elif title:
                lines.append(f"- Speaking context: {title}")
            elif desc:
                lines.append(f"- Speaking context: {desc}")
        elif isinstance(raw_contexts, list):
            # Legacy data: list of focus tags
            focus = ", ".join(str(c).strip() for c in raw_contexts[:5] if str(c).strip())
            if focus:
                lines.append(f"- Focus areas: {focus}")

        if profile.notes:
            notes_clean = str(profile.notes).strip()
            if notes_clean:
                lines.append(
                    f"- User-provided instructions (override other prompts): {notes_clean}"
                )
                lines.append(
                    "Always follow these user instructions even if they conflict with "
                    "earlier system prompts or defaults."
                )

        # Keep notes out for now to stay compact

        lines.append(
            "Tailor your coaching to this context. Reference their bio and goal when giving feedback."
        )

        context_str = "\n".join(lines)

        raw_contexts = profile.contexts
        if isinstance(raw_contexts, list):
            contexts_count = len(raw_contexts)
        elif isinstance(raw_contexts, dict):
            contexts_count = 1 if any(str(v).strip() for v in raw_contexts.values()) else 0
        else:
            contexts_count = 0

        profile_logger.debug(
            "Profile context built",
            extra={
                "service": "profile",
                "user_id": str(user_id),
                "has_bio": bool(getattr(profile, "bio", None)),
                "has_goal": bool(profile.goal),
                "contexts_count": contexts_count,
                "profile_context": context_str,
            },
        )

        return context_str

    async def _save_interaction(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        message_id: uuid.UUID,
        *,
        latency_ms: int | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        llm_cost_cents: int | None = None,
    ) -> Interaction:
        """Save an interaction to the database with optional metrics.

        The extra keyword-only arguments are primarily used for assistant
        messages where we want to persist LLM performance metrics. Tests
        may also call this helper directly with metrics populated.
        """
        # Metrics are now tracked via ProviderCall, but we keep these
        # keyword-only args for backwards compatibility with tests and
        # potential callers. Touch them so linters treat them as used.
        _ = (latency_ms, tokens_in, tokens_out, llm_cost_cents)

        interaction = Interaction(
            id=message_id,
            session_id=session_id,
            message_id=message_id,
            role=role,
            content=content,
            input_type="text" if role == "user" else None,
        )
        self.db.add(interaction)
        await self.db.commit()
        await self.db.refresh(interaction)

        logger.debug(
            "Interaction saved",
            extra={
                "service": "chat",
                "session_id": str(session_id),
                "interaction_id": str(interaction.id),
                "role": role,
            },
        )

        return interaction

    async def _get_latest_summary(self, session_id: uuid.UUID) -> SessionSummary | None:
        """Get the latest summary for a session."""
        result = await self.db.execute(
            select(SessionSummary)
            .where(SessionSummary.session_id == session_id)
            .order_by(SessionSummary.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_recent_interactions(
        self,
        session_id: uuid.UUID,
        after_cutoff: datetime | None = None,
        limit: int = 20,
    ) -> list[Interaction]:
        """Get recent interactions for a session after a cutoff time."""
        query = select(Interaction).where(Interaction.session_id == session_id)

        if after_cutoff is not None:
            query = query.where(Interaction.created_at > after_cutoff)

        query = query.order_by(Interaction.created_at).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_last_n_interactions(
        self,
        session_id: uuid.UUID,
        n: int,
    ) -> list[Interaction]:
        """Get the absolute last N interactions (most recent), returned in chronological order."""
        # Get last N by ordering DESC, then reverse for chronological order
        query = (
            select(Interaction)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.created_at.desc())
            .limit(n)
        )

        result = await self.db.execute(query)
        interactions = list(result.scalars().all())

        # Reverse to get chronological order (oldest first)
        return list(reversed(interactions))

    async def _update_session_count(self, session_id: uuid.UUID) -> None:
        """Update session interaction count."""
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.interaction_count += 1
            await self.db.commit()

    async def _update_summary_state(
        self,
        session_id: uuid.UUID,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
    ) -> SummaryState:
        """Update summary state (increment turns_since).

        Returns:
            The updated SummaryState
        """
        result = await self.db.execute(
            select(SummaryState).where(SummaryState.session_id == session_id)
        )
        state = result.scalar_one_or_none()

        if state:
            state.increment_turns()
            await self.db.commit()
        else:
            # Create initial summary state
            state = SummaryState(
                session_id=session_id,
                turns_since=1,
            )
            self.db.add(state)
            await self.db.commit()

        # Emit summary cadence status
        turns_until_summary = max(0, SUMMARY_THRESHOLD - state.turns_since)

        if send_status:
            await send_status(
                "summary",
                "idle",
                {
                    "turns_since": state.turns_since,
                    "turns_until_summary": turns_until_summary,
                    "threshold": SUMMARY_THRESHOLD,
                    "event": "summary.cadence",
                    "sessionId": str(session_id),
                },
            )

        logger.debug(
            "Summary state updated",
            extra={
                "service": "chat",
                "session_id": str(session_id),
                "turns_since": state.turns_since,
                "turns_until_summary": turns_until_summary,
            },
        )

        return state

    async def _get_assessments_for_interactions(
        self,
        interaction_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, list[SkillAssessment]]:
        """Batch fetch assessments for multiple interactions in one query.

        Returns a dict mapping interaction_id -> list of SkillAssessment records.
        This avoids N+1 queries when building context.
        """
        if not interaction_ids:
            return {}

        # Single query: JOIN Assessment -> SkillAssessment, filter by interaction_ids
        result = await self.db.execute(
            select(Assessment)
            .where(Assessment.interaction_id.in_(interaction_ids))
            .options(selectinload(Assessment.skill_assessments).selectinload(SkillAssessment.skill))
        )
        assessments = list(result.scalars().all())

        # Group by interaction_id
        by_interaction: dict[uuid.UUID, list[SkillAssessment]] = {}
        for assessment in assessments:
            if assessment.interaction_id:
                skill_assessments = assessment.skill_assessments or []
                if assessment.interaction_id not in by_interaction:
                    by_interaction[assessment.interaction_id] = []
                by_interaction[assessment.interaction_id].extend(skill_assessments)

        return by_interaction

    def _format_assessment_context(
        self,
        skill_assessments: list[SkillAssessment],
    ) -> str | None:
        """Format assessment data as a compact context string for the LLM.

        Keeps it brief to avoid bloating context. Includes:
        - Skill name + level
        - Short summary (if available)
        - Key improvement focus (next_level_criteria from feedback)
        """
        if not skill_assessments:
            return None

        lines: list[str] = ["[Prior assessment of user's response:]"]

        for sa in skill_assessments:
            skill_name = sa.skill.title if sa.skill else "Unknown"
            line = f"- {skill_name}: Level {sa.level}/10"

            if sa.confidence is not None:
                line += f" (conf: {sa.confidence:.0%})"

            lines.append(line)

            # Add short summary, truncating if very long so the context stays compact
            if sa.summary:
                summary_text = str(sa.summary)
                if len(summary_text) > 160:
                    summary_text = summary_text[:157] + "..."
                lines.append(f"  {summary_text}")

            feedback = sa.feedback or {}

            # Add primary takeaway (most important insight)
            primary = feedback.get("primary_takeaway")
            if primary:
                lines.append(f"  Key: {primary[:120]}")

            # Add specific strengths (what to reinforce)
            strengths = feedback.get("strengths", [])
            if strengths:
                lines.append(f"  Strengths: {', '.join(strengths[:2])}")

            # Add specific improvements (what to work on)
            improvements = feedback.get("improvements", [])
            if improvements:
                lines.append(f"  Work on: {', '.join(improvements[:2])}")

            # Add example quotes if available (concrete evidence)
            quotes = feedback.get("example_quotes", [])
            improvement_quotes = [q for q in quotes if q.get("type") == "improvement"][:1]
            for q in improvement_quotes:
                quote_text = q.get("quote", "")[:60]
                annotation = q.get("annotation", "")[:40]
                if quote_text:
                    lines.append(f'  Example: "{quote_text}" → {annotation}')

            # Add next-level focus, labelled as "Focus" for clarity
            next_criteria = feedback.get("next_level_criteria")
            if next_criteria:
                lines.append(f"  Focus: {next_criteria[:100]}")

        result = "\n".join(lines)

        # Hard cap to avoid extremely long context blocks
        if len(result) > 400:
            result = result[:397] + "..."

        return result

    def _format_pydantic_assessment_context(
        self,
        assessment: AssessmentResponse,
    ) -> str | None:
        """Format a precomputed Pydantic assessment as a compact context string.

        Mirror of _format_assessment_context but for Pydantic models.
        """
        if not assessment.skills:
            return None

        lines: list[str] = ["[Prior assessment of user's response:]"]

        for sa in assessment.skills:
            # sa is SkillAssessmentResponse (Pydantic)
            # We don't have skill title in the response model, only ID.
            # But wait, we need the title for the prompt.
            # The Pydantic model `SkillAssessmentResponse` only has `skill_id`.
            # We might need to look up the title? Or maybe we can skip it?
            # Actually, `AssessmentResponse` doesn't carry titles.
            # BUT, the `skills_context` passed to `build_context` has titles.
            # Or we can just use "Skill <uuid>" if desperate, but that's bad prompt.
            # Let's check if we can fetch titles.
            # Since this is "accurate" mode, we care about quality.
            # However, doing a DB lookup here is annoying.
            # Ideally, `AssessmentResponse` should include skill title?
            # Or we assume the LLM knows the skill from the `User is practicing...` block?
            # The `skills_context` block lists skills with their titles.
            # So if we say "Skill ID: <uuid>", the LLM might not map it.
            # Let's try to map it using the ID if we can.
            # But `_format_pydantic_assessment_context` doesn't have access to `skills_context`.
            # For now, let's just output the feedback content which is the most important part.
            # The feedback usually talks about the skill implicitly.
            # Actually, let's look at `SkillAssessmentResponse` again.
            # It has `skill_id`.
            # We can label it "Skill Assessment:" if we don't have the title.
            # Or better: The `AssessmentService` could return titles?
            # Let's assume for now we just output the level and feedback.

            line = f"- Skill {sa.skill_id}: Level {sa.level}/10"

            if sa.confidence is not None:
                line += f" (conf: {sa.confidence:.0%})"

            lines.append(line)

            if sa.summary:
                summary_text = str(sa.summary)
                if len(summary_text) > 160:
                    summary_text = summary_text[:157] + "..."
                lines.append(f"  {summary_text}")

            feedback = sa.feedback

            # Add primary takeaway
            if feedback.primary_takeaway:
                lines.append(f"  Key: {feedback.primary_takeaway[:120]}")

            # Add specific strengths
            if feedback.strengths:
                lines.append(f"  Strengths: {', '.join(feedback.strengths[:2])}")

            # Add specific improvements
            if feedback.improvements:
                lines.append(f"  Work on: {', '.join(feedback.improvements[:2])}")

            # Add example quotes
            improvement_quotes = [q for q in feedback.example_quotes if q.type == "improvement"][:1]
            for q in improvement_quotes:
                quote_text = q.quote[:60]
                annotation = q.annotation[:40]
                if quote_text:
                    lines.append(f'  Example: "{quote_text}" → {annotation}')

            # Add next-level focus
            if feedback.next_level_criteria:
                lines.append(f"  Focus: {feedback.next_level_criteria[:100]}")

        result = "\n".join(lines)

        if len(result) > 400:
            result = result[:397] + "..."

        return result

    async def _stream_with_fallback(
        self,
        messages: list[LLMMessage],
        model_id: str | None,
        session_id: uuid.UUID,
        stage_started_at: float,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
        send_token: Callable[[str], Any] | None = None,
        max_tokens: int | None = None,
        user_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        pipeline_run_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        interaction_id: uuid.UUID | None = None,
    ) -> tuple[str, int, str, str | None, int | None, uuid.UUID]:
        """Stream LLM response with fallback to backup provider on failure.

        Args:
            messages: LLM messages to send
            model_id: Override model ID
            session_id: Session ID for logging
            start_time: Start time for duration calculation
            send_status: Status callback
            send_token: Token callback

        Returns:
            Tuple of (full_response, token_count)
        """
        from app.config import get_settings

        settings = get_settings()
        primary_error = None
        stage = LlmStreamStage()

        logger.info(f"[LLM_STREAM] _stream_with_fallback called, send_status={send_status is not None}")

        prompt_payload = [{"role": m.role, "content": m.content} for m in messages]

        # Enforce circuit breaker for primary provider
        is_primary_denied = await _enforce_llm_circuit_breaker(
            operation="llm",
            provider=self.llm.name,
            model_id=model_id,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
        )

        if is_primary_denied:
            # Primary provider denied by breaker, try backup immediately
            backup_provider_name = settings.llm_backup_provider
            if backup_provider_name and backup_provider_name != self.llm.name:
                get_event_sink().try_emit(
                    type="llm.fallback.attempted",
                    data={
                        "primary_provider": self.llm.name,
                        "backup_provider": backup_provider_name,
                        "reason": "primary_breaker_open",
                    },
                )

                try:
                    backup_llm = get_llm_provider(backup_provider_name)

                    # Check backup provider breaker too
                    is_backup_denied = await _enforce_llm_circuit_breaker(
                        operation="llm",
                        provider=backup_llm.name,
                        model_id=None,  # Use backup's default model
                        request_id=request_id,
                        session_id=session_id,
                        user_id=user_id,
                        org_id=org_id,
                    )

                    if is_backup_denied:
                        # Both providers denied, return safe minimal reply
                        safe_reply = _get_safe_minimal_reply()
                        if send_status:
                            await send_status("llm", "complete", {
                                "token_count": len(safe_reply.split()),
                                "provider": "safe_fallback",
                                "model": None,
                                "reason": "all_providers_breaker_open",
                            })
                        if send_token:
                            await send_token(safe_reply, is_complete=True)
                        return safe_reply, len(safe_reply.split()), "safe_fallback", None, 0, uuid.uuid4()

                    # Backup provider is available, proceed with backup
                    result = await stage.run(
                        call_logger=self.call_logger,
                        service="chat",
                        llm=backup_llm,
                        messages=messages,
                        model_id=None,
                        max_tokens=max_tokens,
                        prompt_payload=prompt_payload,
                        session_id=session_id,
                        user_id=user_id,
                        interaction_id=interaction_id,
                        request_id=request_id,
                        pipeline_run_id=pipeline_run_id,
                        org_id=org_id,
                        stage_started_at=stage_started_at,
                        send_status=send_status,
                        send_token=send_token,
                    )

                    get_event_sink().try_emit(
                        type="llm.fallback.succeeded",
                        data={
                            "backup_provider": backup_provider_name,
                            "stream_token_count": result.stream_token_count,
                            "reason": "primary_breaker_open",
                        },
                    )

                    return (
                        result.full_text,
                        result.stream_token_count,
                        result.provider,
                        result.model,
                        result.ttft_ms,
                        result.provider_call.id,
                    )

                except Exception as backup_exc:
                    logger.error(
                        "Backup LLM also failed after primary breaker denial",
                        extra={
                            "service": "chat",
                            "session_id": str(session_id),
                            "primary_provider": self.llm.name,
                            "backup_provider": backup_provider_name,
                            "backup_error": str(backup_exc),
                        },
                    )

            # No backup or backup failed, return safe minimal reply
            safe_reply = _get_safe_minimal_reply()
            if send_status:
                await send_status("llm", "complete", {
                    "token_count": len(safe_reply.split()),
                    "provider": "safe_fallback",
                    "model": None,
                    "reason": "no_available_providers",
                })
            if send_token:
                await send_token(safe_reply, is_complete=True)
            return safe_reply, len(safe_reply.split()), "safe_fallback", None, 0, uuid.uuid4()

        # Try primary provider (breaker allowed the attempt)
        try:
            result = await stage.run(
                call_logger=self.call_logger,
                service="chat",
                llm=self.llm,
                messages=messages,
                model_id=model_id,
                max_tokens=max_tokens,
                prompt_payload=prompt_payload,
                session_id=session_id,
                user_id=user_id,
                interaction_id=interaction_id,
                request_id=request_id,
                pipeline_run_id=pipeline_run_id,
                org_id=org_id,
                stage_started_at=stage_started_at,
                send_status=send_status,
                send_token=send_token,
            )
            return (
                result.full_text,
                result.stream_token_count,
                result.provider,
                result.model,
                result.ttft_ms,
                result.provider_call.id,
            )
        except LlmStreamFailure as exc:
            primary_error = exc.original
            if exc.stream_token_count > 0:
                get_event_sink().try_emit(
                    type="llm.fallback.blocked_post_first_token",
                    data={
                        "primary_provider": self.llm.name,
                        "backup_provider": settings.llm_backup_provider,
                        "stream_token_count": exc.stream_token_count,
                    },
                )
                if send_status:
                    await send_status("llm", "error", {"error": str(primary_error)})
                raise primary_error

            get_event_sink().try_emit(
                type="llm.fallback.attempted",
                data={
                    "primary_provider": self.llm.name,
                    "backup_provider": settings.llm_backup_provider,
                },
            )

            logger.warning(
                "Primary LLM stream failed, will try backup",
                extra={
                    "service": "chat",
                    "session_id": str(session_id),
                    "error": str(primary_error),
                    "backup_provider": settings.llm_backup_provider,
                },
            )

        # Try backup provider if configured
        backup_provider_name = settings.llm_backup_provider
        if backup_provider_name and backup_provider_name != self.llm.name:
            try:
                backup_llm = get_llm_provider(backup_provider_name)
                result = await stage.run(
                    call_logger=self.call_logger,
                    service="chat",
                    llm=backup_llm,
                    messages=messages,
                    model_id=None,
                    max_tokens=max_tokens,
                    prompt_payload=prompt_payload,
                    session_id=session_id,
                    user_id=user_id,
                    interaction_id=interaction_id,
                    request_id=request_id,
                    pipeline_run_id=pipeline_run_id,
                    org_id=org_id,
                    stage_started_at=stage_started_at,
                    send_status=send_status,
                    send_token=send_token,
                )
                logger.info(
                    "Backup LLM stream succeeded",
                    extra={
                        "service": "chat",
                        "session_id": str(session_id),
                        "backup_provider": backup_provider_name,
                    },
                )
                get_event_sink().try_emit(
                    type="llm.fallback.succeeded",
                    data={
                        "backup_provider": backup_provider_name,
                        "stream_token_count": result.stream_token_count,
                    },
                )
                return (
                    result.full_text,
                    result.stream_token_count,
                    result.provider,
                    result.model,
                    result.ttft_ms,
                    result.provider_call.id,
                )
            except Exception as backup_exc:
                logger.error(
                    "Backup LLM stream also failed",
                    extra={
                        "service": "chat",
                        "session_id": str(session_id),
                        "primary_error": str(primary_error),
                        "backup_error": str(backup_exc),
                        "backup_provider": backup_provider_name,
                    },
                )
                if send_status:
                    await send_status("llm", "error", {"error": str(backup_exc)})
                raise backup_exc from primary_error

        # No backup configured - raise original error
        if send_status:
            await send_status("llm", "error", {"error": str(primary_error)})
        raise primary_error  # type: ignore[misc]

    async def _do_stream(
        self,
        llm: LLMProvider,
        messages: list[LLMMessage],
        model_id: str | None,
        session_id: uuid.UUID,
        start_time: float,
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None,
        send_token: Callable[[str], Any] | None,
        max_tokens: int | None,
        provider_name: str,
    ) -> tuple[str, int, str, str | None]:
        """Execute streaming with a specific LLM provider.

        Returns:
            Tuple of (full_response, token_count)
        """
        full_response = ""
        token_count = 0

        effective_model = llm.resolve_model(model_id)

        try:
            kwargs: dict[str, Any] = {}
            if isinstance(max_tokens, int) and max_tokens > 0:
                kwargs["max_tokens"] = max_tokens

            # Add prompt_cache_key for better Groq caching
            # TODO: Pass is_onboarding and platform parameters when available
            cache_key = self._determine_prompt_cache_key(messages, False, None)
            if cache_key:
                kwargs["prompt_cache_key"] = cache_key

            # Send started status before streaming begins
            if send_status:
                logger.info("[LLM_STREAM] Sending llm.started status")
                await send_status("llm", "started", {
                    "provider": llm.name,
                    "model": effective_model,
                })

            # Send completion signal on the last token if we have tokens
            # Note: We track the last token to send it with is_complete=True
            last_token = None
            async for token in llm.stream(messages, model=effective_model, **kwargs):
                full_response += token
                token_count += 1
                last_token = token

                if send_token:
                    await send_token(token)

                # Send streaming status on first token
                if token_count == 1 and send_status:
                    await send_status("llm", "streaming", None)

            # Send completion signal
            if send_token and last_token and token_count > 0:
                await send_token(last_token, is_complete=True)

            # Send complete status with duration
            llm_duration_ms = int((time.time() - start_time) * 1000)
            if send_status:
                await send_status(
                    "llm",
                    "complete",
                    {
                        "token_count": token_count,
                        "duration_ms": llm_duration_ms,
                        "provider": llm.name,
                        "model": effective_model,
                    },
                )

            return full_response, token_count, llm.name, effective_model

        except Exception as e:
            logger.error(
                f"LLM stream failed ({provider_name})",
                extra={
                    "service": "chat",
                    "session_id": str(session_id),
                    "provider": provider_name,
                    "error": str(e),
                },
            )
            raise

    def _determine_prompt_cache_key(
        self, messages: list[LLMMessage], is_onboarding: bool, platform: str | None
    ) -> str | None:
        """Determine optimal prompt_cache_key based on message structure and pipeline type.

        Groups similar prompt structures together to improve Groq cache hit rates:
        - 'onboarding': All onboarding sessions share similar structure
        - 'coaching': Regular coaching sessions with skills/profile context
        - 'chat': Basic chat without skills context
        - 'platform-web/native': Platform-specific variants

        Returns None for non-Groq providers or when caching wouldn't be beneficial.
        """
        # Only apply to Groq provider
        if not hasattr(self.llm, "name") or self.llm.name != "groq":
            return None

        # Extract key characteristics from messages
        has_skills = any(
            "practicing the following tracked skills" in msg.content.lower()
            for msg in messages
            if msg.role == "system"
        )
        has_profile = any(
            "user profile" in msg.content.lower() for msg in messages if msg.role == "system"
        )
        has_meta_summary = any(
            "meta summary" in msg.content.lower() for msg in messages if msg.role == "system"
        )

        # Build cache key based on pipeline characteristics
        key_parts = []

        if is_onboarding:
            key_parts.append("onboarding")
        else:
            key_parts.append("coaching")

        if has_skills:
            key_parts.append("skills")
        if has_profile:
            key_parts.append("profile")
        if has_meta_summary:
            key_parts.append("meta")

        if platform:
            key_parts.append(platform)

        # Return None if key is too generic (wouldn't help cache performance)
        if len(key_parts) <= 1:
            return None

        return "-".join(key_parts)

    async def stream_llm_response(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        context: Any,
        on_chunk: Callable[[str], Any],
        send_status: Callable[[str, str, dict[str, Any] | None], Any] | None = None,
    ) -> None:
        """Stream LLM response for voice pipeline.

        Args:
            session_id: Session ID
            user_id: User ID
            context: Conversation context from build_context
            on_chunk: Callback for each token chunk
            send_status: Optional callback for status updates
        """
        try:
            with open("/tmp/debug_voice_handler.log", "a") as f:
                f.write(
                    f"\n[{time.time() * 1000}] stream_llm_response called\nSession ID: {session_id}\nUser ID: {user_id}\n"
                )
        except Exception:
            pass

        logger.info(
            f"[LLM_STREAM] stream_llm_response called: session_id={session_id}, user_id={user_id}, send_status={send_status is not None}"
        )

        if not context:
            logger.warning("[LLM_STREAM] No context provided")
            return

        if not hasattr(context, "messages"):
            logger.warning(f"[LLM_STREAM] Context has no messages attribute: {type(context)}")
            return

        messages = context.messages
        logger.info(f"[LLM_STREAM] Found {len(messages)} messages in context")

        # Use the existing streaming implementation
        logger.info(f"[LLM_STREAM] Calling _stream_with_fallback, send_status={send_status is not None}")
        await self._stream_with_fallback(
            messages=messages,
            model_id=None,
            session_id=session_id,
            stage_started_at=time.time(),
            send_status=send_status,
            send_token=on_chunk,
            max_tokens=None,
            user_id=user_id,
        )
        logger.info("[LLM_STREAM] _stream_with_fallback completed")
