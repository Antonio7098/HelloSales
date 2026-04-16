"""Agent-runs endpoints."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from hello_sales_backend.entrypoints.http.dependencies import get_agent_run_service
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.agent_runs import AgentRunService
from hello_sales_backend.modules.agent_runs.use_cases.commands import (
    AppendAgentTurnCommand,
    ApprovalDecisionCommand,
    StartAgentRunCommand,
)
from hello_sales_backend.shared.errors import app_error

router = APIRouter()
AgentRunServiceDep = Annotated[AgentRunService, Depends(get_agent_run_service)]


@router.post("", response_model=ApiEnvelope)
async def start_agent_run(
    request: Request,
    command: StartAgentRunCommand,
    service: AgentRunServiceDep,
) -> ApiEnvelope:
    return ok_response(
        await service.start_run(
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            actor_id=None,
            command=command,
        )
    )


@router.get("/{run_id}", response_model=ApiEnvelope)
async def get_agent_run(run_id: str, service: AgentRunServiceDep) -> ApiEnvelope:
    return ok_response(await service.get_run(run_id))


@router.post("/{run_id}/turns", response_model=ApiEnvelope)
async def append_agent_turn(
    run_id: str,
    request: Request,
    command: AppendAgentTurnCommand,
    service: AgentRunServiceDep,
) -> ApiEnvelope:
    return ok_response(
        await service.append_turn(
            run_id=run_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            actor_id=None,
            command=command,
        )
    )


@router.get("/{run_id}/events", response_model=ApiEnvelope)
async def get_agent_run_events(run_id: str, service: AgentRunServiceDep) -> ApiEnvelope:
    return ok_response(await service.list_events(run_id))


@router.get("/{run_id}/events/stream")
async def stream_agent_run_events(
    run_id: str,
    service: AgentRunServiceDep,
    after_sequence: int = Query(default=0, ge=0),
) -> StreamingResponse:
    if await service.get_run(run_id) is None:
        raise app_error(
            "Agent run was not found",
            code="agent.run.not_found",
            category="validation",
            status_code=404,
            details={"run_id": run_id},
            operation="agent_run.stream_events",
            component="agent",
        )

    async def event_source():
        async for event in service.observe_events(run_id, after_sequence=after_sequence):
            payload = json.dumps(event.model_dump(mode="json"))
            yield f"id: {event.sequence_no}\n".encode()
            yield f"event: {event.event_type}\n".encode()
            yield f"data: {payload}\n\n".encode()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{run_id}/cancel", response_model=ApiEnvelope)
async def cancel_agent_run(run_id: str, service: AgentRunServiceDep) -> ApiEnvelope:
    return ok_response(await service.cancel_run(run_id))


@router.post("/approvals/{approval_id}", response_model=ApiEnvelope)
async def decide_agent_approval(
    approval_id: str,
    request: Request,
    command: ApprovalDecisionCommand,
    service: AgentRunServiceDep,
) -> ApiEnvelope:
    return ok_response(
        await service.decide_approval(
            approval_id=approval_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            actor_id=None,
            command=command,
        )
    )
