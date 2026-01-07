"""Unified TriageStage - classifies user responses before agent execution.

This stage runs in the pre_agent phase to determine if the user's response
should be assessed against skills or treated as general chatter.

Implements the unified Stage protocol:
- execute(ctx: StageContext) -> StageOutput
- Uses StageContext.snapshot directly (no SnapshotBuilder needed)
- Returns StageOutput with unified status/data/artifacts/events
"""
from __future__ import annotations

from app.ai.providers.factory import get_llm_provider
from app.ai.substrate.agent.context_snapshot import ContextSnapshot
from app.ai.substrate.stages import register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput
from app.database import get_session_factory
from app.domains.assessment.triage import TriageService
from app.schemas.assessment import ChatMessage, ChatRole, TriageRequest


@register_stage(kind=StageKind.WORK)
class TriageStage(Stage):
    """Stage that triages user responses before agent execution.

    This stage uses LLM-based classification to determine if the user's
    response should be assessed against skills (assess) or treated as
    general chatter/meta conversation (skip).

    Runs in the pre_agent phase so assessment can be skipped early if needed.
    """

    name = "triage"
    kind = StageKind.WORK

    def __init__(self, llm_provider_name: str | None = None) -> None:
        """Initialize the triage stage.

        Args:
            llm_provider_name: Optional LLM provider name override
        """
        self._llm_provider_name = llm_provider_name

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Execute triage logic using StageContext.

        Args:
            ctx: StageContext containing the immutable snapshot

        Returns:
            StageOutput with triage decision
        """
        snapshot = ctx.snapshot
        user_input = snapshot.input_text

        if not user_input:
            return StageOutput.ok(
                triage_decision="skip",
                triage_reason="no_input",
                skip_assessment=True,
            )

        session_id = snapshot.session_id
        if session_id is None:
            return StageOutput.ok(
                triage_decision="skip",
                triage_reason="no_session",
                skip_assessment=True,
            )

        session_factory = get_session_factory()
        async with session_factory() as db:
            llm_provider = get_llm_provider(self._llm_provider_name) if self._llm_provider_name else get_llm_provider()
            triage_service = TriageService(db, llm_provider=llm_provider)

            chat_context = self._build_context(snapshot)
            triage_request = TriageRequest(
                session_id=session_id,
                user_response=user_input,
                context=chat_context,
            )

            try:
                triage_response = await triage_service.classify_response(
                    request=triage_request,
                    interaction_id=snapshot.interaction_id,
                    request_id=snapshot.request_id,
                )

                decision = triage_response.decision.value
                skip_assessment = decision == "skip"

                return StageOutput.ok(
                    triage_decision=decision,
                    triage_reason=triage_response.reason,
                    skip_assessment=skip_assessment,
                    triage_latency_ms=triage_response.latency_ms,
                    triage_tokens=triage_response.tokens_used,
                    triage_cost_cents=triage_response.cost_cents,
                    triage_provider=triage_response.provider,
                    triage_model=triage_response.model,
                )
            except Exception as exc:
                return StageOutput.ok(
                    triage_decision="skip",
                    triage_reason=f"error: {str(exc)}",
                    skip_assessment=True,
                )

    def _build_context(self, snapshot: ContextSnapshot) -> list[ChatMessage]:
        """Build chat context from snapshot messages.

        Args:
            snapshot: The context snapshot

        Returns:
            List of ChatMessage objects for triage
        """
        context: list[ChatMessage] = []
        for msg in snapshot.messages[-5:]:
            role = ChatRole.USER if msg.role == "user" else ChatRole.ASSISTANT
            context.append(ChatMessage(role=role, content=msg.content))
        return context


__all__ = ["TriageStage"]
