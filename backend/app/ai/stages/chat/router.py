"""RouterStage - selects topology, kernel, and channel based on request."""
from __future__ import annotations

import logging
from uuid import UUID

from app.ai.substrate.protocols.routing import RouteDecision, RouteRequest
from app.ai.substrate.stages import get_router_or_raise, register_stage
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput

logger = logging.getLogger("router")


@register_stage(kind=StageKind.ROUTE)
class RouterStage(Stage):
    """Stage that selects the appropriate topology, kernel, and channel.

    This stage runs first to determine the pipeline configuration based
    on the incoming request.
    """

    name = "router"
    kind = StageKind.ROUTE

    def __init__(
        self,
        router_name: str | None = None,
        _db=None,
        _router_port=None,
    ) -> None:
        if router_name is None:
            self._router = None
        else:
            router_class = get_router_or_raise(router_name)
            self._router = router_class()

    async def execute(self, ctx: StageContext) -> StageOutput:
        try:
            snapshot = ctx.snapshot
            data = ctx.config.get('data', {})

            logger.info(f"RouterStage: service={data.get('service')}, input_text={snapshot.input_text[:50] if snapshot.input_text else 'None'}...")

            route_request = RouteRequest(
                service=data.get("service") or "chat",
                input_text=snapshot.input_text,
                input_metadata=data.get("metadata", {}),
                user_id=snapshot.user_id or UUID("00000000-0000-0000-0000-000000000000"),
                session_id=snapshot.session_id or UUID("00000000-0000-0000-0000-000000000000"),
                org_id=snapshot.org_id,
            )

            if self._router is None:
                decision = RouteDecision(
                    topology="voice",
                    kernel="fast_kernel",
                    channel="voice_channel",
                    agent_id="coach_v2",
                    behavior="default",
                    confidence=1.0,
                    reason="No router configured - using defaults",
                )
            else:
                decision: RouteDecision = self._router.route(route_request)

            route_data = {
                "topology": decision.topology,
                "kernel": decision.kernel,
                "channel": decision.channel,
                "agent_id": decision.agent_id,
                "behavior": decision.behavior,
                "confidence": decision.confidence,
                "reason": decision.reason,
            }

            ctx.emit_event("routing_decision", route_data)

            return StageOutput.ok(
                topology=decision.topology,
                kernel=decision.kernel,
                channel=decision.channel,
                agent_id=decision.agent_id,
                behavior=decision.behavior,
                route_data=route_data,
            )
        except Exception as exc:
            logger.exception(f"RouterStage failed: {exc}")
            return StageOutput.fail(error=str(exc))


__all__ = ["RouterStage"]
