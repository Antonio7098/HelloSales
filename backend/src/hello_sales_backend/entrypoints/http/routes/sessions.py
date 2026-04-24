"""Session-first conversational endpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from hello_sales_backend.entrypoints.http.dependencies import (
    get_session_service,
    require_permissions,
)
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.agent_runs.use_cases.commands import ApprovalDecisionCommand
from hello_sales_backend.modules.sessions import SessionService
from hello_sales_backend.modules.sessions.use_cases.commands import (
    AppendSessionMessageCommand,
    CreateSessionCommand,
)
from hello_sales_backend.shared.auth import (
    APP_ACCESS_PERMISSION,
    SESSIONS_READ_PERMISSION,
    SESSIONS_WRITE_PERMISSION,
    AuthContext,
)
from hello_sales_backend.shared.errors import app_error

router = APIRouter()
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
ReadDep = Annotated[AuthContext, Depends(require_permissions(APP_ACCESS_PERMISSION, SESSIONS_READ_PERMISSION))]
WriteDep = Annotated[AuthContext, Depends(require_permissions(APP_ACCESS_PERMISSION, SESSIONS_WRITE_PERMISSION))]


@router.post("", response_model=ApiEnvelope)
async def create_session(
    request: Request,
    command: CreateSessionCommand,
    auth_context: WriteDep,
    service: SessionServiceDep,
) -> ApiEnvelope:
    return ok_response(
        await service.create_session(
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            auth_context=auth_context,
            command=command,
        )
    )


@router.get("", response_model=ApiEnvelope)
async def list_sessions(
    auth_context: ReadDep,
    service: SessionServiceDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiEnvelope:
    return ok_response(await service.list_sessions(auth_context=auth_context, limit=limit))


@router.get("/{session_id}", response_model=ApiEnvelope)
async def get_session(
    session_id: str,
    auth_context: ReadDep,
    service: SessionServiceDep,
) -> ApiEnvelope:
    return ok_response(await service.get_session(session_id, auth_context=auth_context))


@router.post("/{session_id}/messages", response_model=ApiEnvelope)
async def append_session_message(
    session_id: str,
    request: Request,
    command: AppendSessionMessageCommand,
    auth_context: WriteDep,
    service: SessionServiceDep,
) -> ApiEnvelope:
    return ok_response(
        await service.append_message(
            session_id=session_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            auth_context=auth_context,
            command=command,
        )
    )


@router.get("/{session_id}/items", response_model=ApiEnvelope)
async def get_session_items(
    session_id: str,
    auth_context: ReadDep,
    service: SessionServiceDep,
    limit: int = Query(default=500, ge=1, le=1000),
) -> ApiEnvelope:
    return ok_response(await service.list_items(session_id, auth_context=auth_context, limit=limit))


@router.get("/{session_id}/events", response_model=ApiEnvelope)
async def get_session_events(
    session_id: str,
    auth_context: ReadDep,
    service: SessionServiceDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> ApiEnvelope:
    return ok_response(await service.list_events(session_id, auth_context=auth_context, limit=limit))


@router.get("/{session_id}/events/stream")
async def stream_session_events(
    session_id: str,
    auth_context: ReadDep,
    service: SessionServiceDep,
    after_sequence: int = Query(default=0, ge=0),
) -> StreamingResponse:
    if await service.get_session(session_id, auth_context=auth_context) is None:
        raise app_error(
            "Session was not found",
            code="session.not_found",
            category="validation",
            status_code=404,
            details={"session_id": session_id},
            operation="session.stream_events",
            component="sessions",
        )

    async def event_source() -> AsyncIterator[bytes]:
        async for event in service.observe_events(
            session_id,
            auth_context=auth_context,
            after_sequence=after_sequence,
        ):
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


@router.post("/{session_id}/cancel", response_model=ApiEnvelope)
async def cancel_session(
    session_id: str,
    auth_context: WriteDep,
    service: SessionServiceDep,
) -> ApiEnvelope:
    return ok_response(await service.cancel_session(session_id, auth_context=auth_context))


@router.post("/approvals/{approval_id}", response_model=ApiEnvelope)
async def decide_session_approval(
    approval_id: str,
    request: Request,
    command: ApprovalDecisionCommand,
    auth_context: WriteDep,
    service: SessionServiceDep,
) -> ApiEnvelope:
    return ok_response(
        await service.decide_approval(
            approval_id=approval_id,
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            auth_context=auth_context,
            command=command,
        )
    )
