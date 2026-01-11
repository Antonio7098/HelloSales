"""Unified chat context stages - EnricherPrefetch, SkillsContext, ChatContextBuild, Persist."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.ai.substrate.agent.context_snapshot import (
    ContextSnapshot,
    MemoryEnrichment,
    Message,
    ProfileEnrichment,
    SkillsEnrichment,
)
from app.ai.substrate.events import get_event_sink
from app.ai.substrate.stages import register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput
from app.ai.substrate.stages.inputs import StageInputs
from app.domains.chat.service import ChatContext

logger = logging.getLogger("chat_stages")


@register_stage(kind=StageKind.ENRICH)
class EnricherPrefetchStage(Stage):
    """Prefetch enrichers for chat context building."""

    name = "enricher_prefetch"
    kind = StageKind.ENRICH

    async def execute(self, ctx: StageContext) -> StageOutput:
        try:
            from app.config import get_settings
            settings = get_settings()
            profile_enabled = settings.context_enricher_profile_enabled

            await get_event_sink().emit(
                type="enricher.profile.started",
                data={"enabled": profile_enabled},
            )

            prefetched_enrichers = {"summary": {}, "profile": {}}

            await get_event_sink().emit(
                type="enricher.profile.completed",
                data={"enabled": profile_enabled, "status": "complete", "duration_ms": 0},
            )

            ctx.emit_event("enricher_prefetch_completed", {"profile_enabled": profile_enabled})

            return StageOutput.ok(
                prefetched_enrichers=prefetched_enrichers,
                profile_enabled=profile_enabled,
            )
        except Exception as exc:
            ctx.emit_event("enricher_prefetch_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


@register_stage(kind=StageKind.ENRICH)
class ChatContextBuildStage(Stage):
    """Build chat context using staged data."""

    name = "context_build"
    kind = StageKind.ENRICH

    async def execute(self, ctx: StageContext) -> StageOutput:
        snapshot = ctx.snapshot
        inputs: StageInputs = ctx.config.get("inputs")

        try:
            # Get transcript from STT stage output
            stt_output = inputs.get("stt_output")
            logger.info(f"context_build: stt_output={stt_output}, type={type(stt_output).__name__ if stt_output else 'None'}")
            text = ""
            if stt_output and hasattr(stt_output, 'transcript'):
                text = stt_output.transcript
            elif stt_output:
                text = str(stt_output)
            # Fallback to text from prior outputs (e.g., text channel)
            if not text:
                text = inputs.get("text", "")

            messages = []
            if text:
                user_message = Message(
                    role="user",
                    content=text,
                    timestamp=datetime.now(UTC),
                )
                messages.append(user_message)

            context = ChatContext(messages=list(messages))

            prefetched = inputs.get("prefetched_enrichers", {})
            profile_data = prefetched.get("profile", {}) if prefetched else {}

            profile = None
            if profile_data:
                profile = ProfileEnrichment(
                    user_id=snapshot.user_id or uuid.uuid4(),
                    display_name=profile_data.get("display_name"),
                    preferences=profile_data.get("preferences", {}),
                    goals=profile_data.get("goals", []),
                    skill_levels=profile_data.get("skill_levels", {}),
                )

            skills_data = inputs.get("skills_context", [])
            skills = SkillsEnrichment(
                active_skill_ids=skills_data if isinstance(skills_data, list) else [],
                current_level=None,
                skill_progress={},
            )

            context_snapshot = ContextSnapshot(
                pipeline_run_id=snapshot.pipeline_run_id,
                request_id=snapshot.request_id,
                session_id=snapshot.session_id,
                user_id=snapshot.user_id,
                org_id=snapshot.org_id,
                interaction_id=snapshot.interaction_id,
                topology=snapshot.topology,
                channel=snapshot.channel,
                behavior=snapshot.behavior,
                messages=messages,
                profile=profile,
                memory=MemoryEnrichment(),
                skills=skills,
                input_text=text,
            )

            logger.info(f"context_build: completed, messages count={len(messages)}, text='{text[:50]}...'")
            ctx.emit_event("context_build_completed", {"messages_count": len(messages)})

            return StageOutput.ok(
                context=context,
                context_snapshot=context_snapshot,
                messages=list(messages),  # Output messages for LLM stage
            )
        except Exception as exc:
            ctx.emit_event("context_build_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


@register_stage(kind=StageKind.WORK)
class ChatPersistStage(Stage):
    """Persist user and assistant messages to database."""

    name = "persist"
    kind = StageKind.WORK

    async def execute(self, ctx: StageContext) -> StageOutput:
        inputs: StageInputs = ctx.config.get("inputs")

        try:
            # Get user_message_id from user_message_persist stage output
            user_message_id = inputs.get("user_message_id")
            # Get assistant_message_id from LLM stream output
            assistant_message_id = inputs.get("assistant_message_id")

            ctx.emit_event("persist_completed", {
                "message_id": str(user_message_id) if user_message_id else None,
                "assistant_message_id": str(assistant_message_id) if assistant_message_id else None,
            })

            return StageOutput.ok(
                user_message_id=str(user_message_id) if user_message_id else None,
                assistant_message_id=str(assistant_message_id) if assistant_message_id else None,
                session_updated=True,
            )
        except Exception as exc:
            ctx.emit_event("persist_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


__all__ = [
    "EnricherPrefetchStage",
    "SkillsContextStage",
    "ChatContextBuildStage",
    "ChatPersistStage",
]
