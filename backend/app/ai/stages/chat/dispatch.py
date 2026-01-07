"""Unified DispatchStage - selects agent/behavior based on full context.

This stage runs after context_build to select the appropriate agent
and behavior based on the full context.

Implements the unified Stage protocol:
- execute(ctx: StageContext) -> StageOutput
- Uses StageContext.snapshot directly (no SnapshotBuilder needed)
- Returns StageOutput with unified status/data/artifacts/events
"""
from __future__ import annotations

from app.ai.substrate.protocols.dispatch import DispatchDecision
from app.ai.substrate.stages import register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput


@register_stage(kind=StageKind.ROUTE)
class DispatchStage(Stage):
    """Stage that selects agent and behavior based on full context.

    This stage runs after context_build to determine which agent
    and behavior to use based on the complete conversation context.
    """

    name = "dispatch"
    kind = StageKind.ROUTE

    def __init__(
        self,
        dispatcher_name: str | None = None,
    ) -> None:
        """Initialize the dispatch stage.

        Args:
            dispatcher_name: Optional name of the dispatcher to use.
                            Required only if dispatch stage is used in pipeline.
        """
        if dispatcher_name is None:
            self._dispatcher = None
        else:
            from app.ai.substrate.stages import get_dispatcher_or_raise
            dispatcher_class = get_dispatcher_or_raise(dispatcher_name)
            self._dispatcher = dispatcher_class()

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Execute dispatch logic using StageContext.

        Args:
            ctx: StageContext containing the immutable snapshot

        Returns:
            StageOutput with dispatch decision, or skipped if no dispatcher configured.
        """
        if self._dispatcher is None:
            return StageOutput.ok(
                dispatch_agent_id="coach_v2",
                dispatch_behavior="default",
                dispatch_reason="No dispatcher configured - using defaults",
            )

        snapshot = ctx.snapshot
        decision: DispatchDecision = await self._dispatcher.dispatch(snapshot)

        return StageOutput.ok(
            dispatch_agent_id=decision.agent_id,
            dispatch_behavior=decision.behavior,
            dispatch_sub_dispatcher=decision.sub_dispatcher,
            dispatch_path_config=decision.path_config,
            dispatch_confidence=decision.confidence,
            dispatch_reason=decision.reason,
        )


__all__ = ["DispatchStage"]
