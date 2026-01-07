"""InputStage - normalizes chat input and stores in context."""

from __future__ import annotations

import logging
import uuid

from app.ai.substrate.stages import register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput

logger = logging.getLogger("chat_stages")


@register_stage(kind=StageKind.TRANSFORM)
class InputStage(Stage):
    """Normalize chat input and store in context."""

    name = "input"
    kind = StageKind.TRANSFORM

    async def execute(self, ctx: StageContext) -> StageOutput:
        snapshot = ctx.snapshot
        data = ctx.config.get('data', {})

        chat_input = {
            "text": data.get("text"),
            "session_id": snapshot.session_id,
            "user_id": snapshot.user_id,
            "org_id": snapshot.org_id,
            "quality_mode": data.get("quality_mode", "fast"),
            "skill_ids": data.get("skill_ids"),
            "message_id": data.get("message_id"),
            "assistant_message_id": data.get("assistant_message_id"),
            "platform": data.get("platform"),
            "model_id": data.get("model_id"),
        }

        if chat_input["message_id"] is None:
            chat_input["message_id"] = (
                uuid.uuid5(snapshot.pipeline_run_id, "user") if snapshot.pipeline_run_id else uuid.uuid4()
            )
        if chat_input["assistant_message_id"] is None:
            chat_input["assistant_message_id"] = (
                uuid.uuid5(snapshot.pipeline_run_id, "assistant")
                if snapshot.pipeline_run_id
                else uuid.uuid4()
            )

        ctx.emit_event("input_processed", {"message_id": str(chat_input["message_id"])})

        return StageOutput.ok(
            chat_input=chat_input,
            message_id=str(chat_input["message_id"]),
            assistant_message_id=str(chat_input["assistant_message_id"]),
        )


__all__ = ["InputStage"]
