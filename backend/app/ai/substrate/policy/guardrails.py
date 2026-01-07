"""Guardrails policy stage for content moderation."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

from app.ai.substrate import PipelineEventLogger
from app.ai.substrate.policy.guardrails_registry import register_guardrails
from app.config import get_settings
from app.database import get_session_context

logger = logging.getLogger("guardrails")


class GuardrailsCheckpoint(str, Enum):
    PRE_LLM = "pre_llm"
    PRE_ACTION = "pre_action"
    PRE_PERSIST = "pre_persist"


class GuardrailsDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


@dataclass(frozen=True)
class GuardrailsContext:
    pipeline_run_id: UUID
    request_id: UUID | None
    session_id: UUID | None
    user_id: UUID | None
    org_id: UUID | None
    service: str
    intent: str | None
    input_excerpt: str | None = None


@dataclass(frozen=True)
class GuardrailsResult:
    decision: GuardrailsDecision
    reason: str


@register_guardrails(
    name="default",
    checkpoints=["pre_llm", "pre_action", "pre_persist"],
    description="Default guardrails stage for content moderation"
)
class GuardrailsStage:
    async def evaluate(
        self,
        *,
        checkpoint: GuardrailsCheckpoint,
        context: GuardrailsContext,
    ) -> GuardrailsResult:
        settings = get_settings()

        if not getattr(settings, "guardrails_enabled", True):
            result = GuardrailsResult(decision=GuardrailsDecision.ALLOW, reason="disabled")
            await self._emit_decision(checkpoint=checkpoint, context=context, result=result)
            return result

        forced_checkpoint = getattr(settings, "guardrails_force_checkpoint", None)
        forced_decision = getattr(settings, "guardrails_force_decision", None)
        if forced_checkpoint and forced_decision and str(forced_checkpoint) == checkpoint.value:
            reason = getattr(settings, "guardrails_force_reason", None) or "forced"
            try:
                decision = GuardrailsDecision(str(forced_decision))
            except Exception:
                decision = GuardrailsDecision.BLOCK
            result = GuardrailsResult(decision=decision, reason=reason)
            await self._emit_decision(checkpoint=checkpoint, context=context, result=result)
            return result

        result = GuardrailsResult(decision=GuardrailsDecision.ALLOW, reason="default_allow")
        await self._emit_decision(checkpoint=checkpoint, context=context, result=result)
        return result

    async def _emit_decision(
        self,
        *,
        checkpoint: GuardrailsCheckpoint,
        context: GuardrailsContext,
        result: GuardrailsResult,
    ) -> None:
        if context.pipeline_run_id is None:
            return

        # Handle both GuardrailsContext and PolicyContext (which may lack input_excerpt)
        input_excerpt = getattr(context, 'input_excerpt', None)

        data: dict[str, Any] = {
            "checkpoint": checkpoint.value,
            "decision": result.decision.value,
            "reason": result.reason,
            "service": context.service,
            "intent": context.intent,
            "input_excerpt": input_excerpt,
        }

        async with get_session_context() as db:
            event_logger = PipelineEventLogger(db)
            await event_logger.emit(
                pipeline_run_id=context.pipeline_run_id,
                type="guardrails.decision",
                request_id=context.request_id,
                session_id=context.session_id,
                user_id=context.user_id,
                org_id=context.org_id,
                data=data,
            )

            if result.decision != GuardrailsDecision.ALLOW:
                await event_logger.emit(
                    pipeline_run_id=context.pipeline_run_id,
                    type="guardrails.blocked",
                    request_id=context.request_id,
                    session_id=context.session_id,
                    user_id=context.user_id,
                    org_id=context.org_id,
                    data=data,
                )

        logger.info(
            "Guardrails decision",
            extra={
                "service": "guardrails",
                "pipeline_run_id": str(context.pipeline_run_id),
                "metadata": data,
            },
        )
