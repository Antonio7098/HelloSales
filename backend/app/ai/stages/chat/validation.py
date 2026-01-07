"""Validation stage for agent output."""

from __future__ import annotations

from app.ai.substrate.stages import register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput
from app.ai.substrate.stages.inputs import StageInputs
from app.ai.validation import (
    emit_agent_output_validation_event,
    parse_agent_output,
)


@register_stage(kind=StageKind.TRANSFORM)
class ValidationStage(Stage):
    """Validation stage for agent output."""

    name = "validation"
    kind = StageKind.TRANSFORM

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def execute(self, ctx: StageContext) -> StageOutput:
        snapshot = ctx.snapshot
        inputs: StageInputs = ctx.config.get("inputs")

        try:
            # Get LLM output from prior stage (llm_stream outputs llm_result)
            llm_result = inputs.get("llm_result")

            if not llm_result or not isinstance(llm_result, dict):
                return StageOutput.skip(reason="no_llm_output")

            full_text = llm_result.get("full_text")
            if not full_text:
                return StageOutput.skip(reason="no_llm_output")

            full_response = full_text
            parsed_agent_output, parse_error, attempted_parse = parse_agent_output(full_response)

            success = parsed_agent_output is not None
            error = parse_error
            parsed = parsed_agent_output.model_dump() if parsed_agent_output else None
            raw_excerpt = full_response[:200] if full_response else None

            await emit_agent_output_validation_event(
                pipeline_run_id=snapshot.pipeline_run_id,
                request_id=snapshot.request_id,
                session_id=snapshot.session_id,
                user_id=snapshot.user_id,
                org_id=snapshot.org_id,
                success=success,
                error=error,
                parsed=parsed,
                raw_excerpt=raw_excerpt,
            )

            ctx.emit_event("validation_completed", {"success": success})

            return StageOutput.ok(
                success=success,
                error=error,
                parsed=parsed,
                raw_excerpt=raw_excerpt,
                full_response=full_response,  # Pass through for post_llm_policy
            )
        except Exception as exc:
            ctx.emit_event("validation_failed", {"error": str(exc)})
            return StageOutput.fail(error=str(exc))


__all__ = ["ValidationStage"]
