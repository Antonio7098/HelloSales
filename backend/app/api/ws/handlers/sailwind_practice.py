"""Sailwind practice WebSocket handlers.

Implements the protocol described in SWD-SPR-003:
- sailwind.practice.start
- sailwind.practice.message

These handlers reuse the existing chat streaming semantics (chat.token/chat.complete)
while injecting Strategy text as additional system context.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select

from app.ai.providers.factory import get_llm_provider
from app.ai.substrate.stages import PipelineOrchestrator
from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.database import get_session_context
from app.domains.assessment.summary import SummaryService
from app.domains.chat.service import ChatService
from app.domains.sailwind.practice import (
    PracticeNotFoundError,
    PracticeSessionService,
    PracticeValidationError,
)
from app.logging_config import set_request_context
from app.models import SummaryState
from app.models.sailwind_playbook import Strategy
from app.models.sailwind_practice import PracticeSession

logger = logging.getLogger("sailwind.ws")
router = get_router()


def _parse_uuid(value: Any, *, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {field}") from exc


async def _send_error(
    websocket: WebSocket,
    manager: ConnectionManager,
    *,
    code: str,
    message: str,
    request_id: str | None,
    pipeline_run_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if request_id is not None:
        payload["requestId"] = request_id
    if pipeline_run_id is not None:
        payload["pipelineRunId"] = pipeline_run_id
    await manager.send_message(websocket, {"type": "error", "payload": payload})


@router.handler("sailwind.practice.start")
async def handle_practice_start(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Start a Sailwind practice session.

    Expected payload:
        { "strategyId": "uuid", "repAssignmentId"?: "uuid" }

    Responds:
        - sailwind.practice.started { practiceSessionId, chatSessionId }
        - status.update (service=sailwind, status=started)
    """

    conn = manager.get_connection(websocket)
    request_id = payload.get("requestId")

    if not conn or not conn.authenticated or not conn.user_id:
        await _send_error(
            websocket,
            manager,
            code="NOT_AUTHENTICATED",
            message="Must authenticate before starting practice",
            request_id=request_id,
        )
        return

    org_id = getattr(conn, "org_id", None)
    if not org_id:
        await _send_error(
            websocket,
            manager,
            code="ORG_CONTEXT_REQUIRED",
            message="Organization context required",
            request_id=request_id,
        )
        return

    try:
        strategy_id = _parse_uuid(payload.get("strategyId"), field="strategyId")
    except ValueError as exc:
        await _send_error(
            websocket,
            manager,
            code="INVALID_PAYLOAD",
            message=str(exc),
            request_id=request_id,
        )
        return

    rep_assignment_id_raw = payload.get("repAssignmentId")
    rep_assignment_id: UUID | None = None
    if rep_assignment_id_raw is not None:
        try:
            rep_assignment_id = _parse_uuid(rep_assignment_id_raw, field="repAssignmentId")
        except ValueError as exc:
            await _send_error(
                websocket,
                manager,
                code="INVALID_PAYLOAD",
                message=str(exc),
                request_id=request_id,
            )
            return

    async with get_session_context() as db:
        service = PracticeSessionService(db)
        try:
            practice = await service.start_practice_session(
                organization_id=org_id,
                user_id=conn.user_id,
                strategy_id=strategy_id,
                rep_assignment_id=rep_assignment_id,
                actor_user_id=conn.user_id,
            )
        except PracticeNotFoundError as exc:
            await _send_error(
                websocket,
                manager,
                code="NOT_FOUND",
                message=str(exc),
                request_id=request_id,
            )
            return
        except PracticeValidationError as exc:
            await _send_error(
                websocket,
                manager,
                code="BAD_REQUEST",
                message=str(exc),
                request_id=request_id,
            )
            return

    # Attach chat session to connection for downstream handlers (do not call manager.authenticate
    # to avoid duplicating ws_id in user connection list).
    if conn and practice.chat_session_id:
        conn.session_id = practice.chat_session_id

    await manager.send_message(
        websocket,
        {
            "type": "sailwind.practice.started",
            "payload": {
                "practiceSessionId": str(practice.id),
                "chatSessionId": str(practice.chat_session_id) if practice.chat_session_id else None,
            },
        },
    )

    await manager.send_message(
        websocket,
        {
            "type": "status.update",
            "payload": {
                "service": "sailwind",
                "status": "started",
                "metadata": {
                    "operation": "practice.start",
                    "practiceSessionId": str(practice.id),
                    "chatSessionId": str(practice.chat_session_id) if practice.chat_session_id else None,
                    "requestId": request_id,
                },
            },
        },
    )


@router.handler("sailwind.practice.message")
async def handle_practice_message(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle a practice chat message.

    Expected payload:
        { "practiceSessionId": "uuid", "content": "...", "requestId"?: "uuid" }

    Responds with the standard chat streaming events:
        - chat.token
        - chat.complete
        - status.update
    """

    conn = manager.get_connection(websocket)
    request_id_raw = payload.get("requestId")
    try:
        request_id_uuid = uuid.UUID(str(request_id_raw)) if request_id_raw else uuid.uuid4()
    except (ValueError, TypeError):
        request_id_uuid = uuid.uuid4()
    request_id = str(request_id_uuid)

    if not conn or not conn.authenticated or not conn.user_id:
        await _send_error(
            websocket,
            manager,
            code="NOT_AUTHENTICATED",
            message="Must authenticate before sending practice messages",
            request_id=request_id,
        )
        return

    org_id = getattr(conn, "org_id", None)
    if not org_id:
        await _send_error(
            websocket,
            manager,
            code="ORG_CONTEXT_REQUIRED",
            message="Organization context required",
            request_id=request_id,
        )
        return

    content = payload.get("content")
    if not content or not str(content).strip():
        await _send_error(
            websocket,
            manager,
            code="INVALID_PAYLOAD",
            message="content is required and cannot be empty",
            request_id=request_id,
        )
        return

    try:
        practice_session_id = _parse_uuid(payload.get("practiceSessionId"), field="practiceSessionId")
    except ValueError as exc:
        await _send_error(
            websocket,
            manager,
            code="INVALID_PAYLOAD",
            message=str(exc),
            request_id=request_id,
        )
        return

    pipeline_run_id = uuid.uuid4()

    set_request_context(
        request_id=request_id,
        user_id=str(conn.user_id),
        session_id=str(conn.session_id) if conn.session_id else None,
        pipeline_run_id=str(pipeline_run_id),
        org_id=str(org_id),
    )

    async def send_status(service: str, status: str, metadata: dict[str, Any] | None) -> None:
        event_metadata = metadata or {}
        event_metadata.setdefault("requestId", request_id)
        event_metadata.setdefault("pipelineRunId", str(pipeline_run_id))
        event_metadata.setdefault("practiceSessionId", str(practice_session_id))
        await manager.send_message(
            websocket,
            {
                "type": "status.update",
                "payload": {
                    "service": service,
                    "status": status,
                    "metadata": event_metadata,
                },
            },
        )

    async def send_token(token: str, *, session_id: str) -> None:
        await manager.send_message(
            websocket,
            {
                "type": "chat.token",
                "payload": {
                    "sessionId": session_id,
                    "token": token,
                },
            },
        )

    pipeline_mode = manager.get_pipeline_mode(websocket)
    is_accurate_mode = pipeline_mode in ("accurate", "accurate_filler")
    quality_mode = "accurate" if is_accurate_mode else "fast"

    orchestrator = PipelineOrchestrator()

    try:
        await send_status(
            "pipeline",
            "running",
            {
                "mode": "practice",
                "quality_mode": quality_mode,
            },
        )

        async def _runner(wrapped_send_status, wrapped_send_token) -> dict[str, Any]:
            async with get_session_context() as db:
                # Validate practice session ownership and load strategy context
                practice = await db.scalar(
                    select(PracticeSession).where(
                        PracticeSession.id == practice_session_id,
                        PracticeSession.organization_id == org_id,
                        PracticeSession.user_id == conn.user_id,
                    )
                )
                if practice is None:
                    raise PracticeNotFoundError("Practice session not found")

                if not practice.chat_session_id:
                    raise PracticeValidationError("Practice session has no chat session")

                strategy = await db.scalar(
                    select(Strategy).where(
                        Strategy.id == practice.strategy_id,
                        Strategy.organization_id == org_id,
                    )
                )
                if strategy is None:
                    raise PracticeNotFoundError("Strategy not found")

                # Ensure summary_state exists to avoid schema drift / new sessions.
                existing_state = await db.scalar(
                    select(SummaryState).where(SummaryState.session_id == practice.chat_session_id)
                )
                if existing_state is None:
                    db.add(SummaryState(session_id=practice.chat_session_id))
                    await db.flush()

                chat_service = ChatService(db, llm_provider=get_llm_provider())
                chat_service.system_prompt = (
                    f"{chat_service.system_prompt}\n\n"
                    "You are running a Sailwind practice session. You must role-play as the sales client "
                    "and keep the conversation grounded in the strategy context below. Do not reveal the "
                    "strategy text verbatim; use it to guide objections, priorities, and decision criteria.\n\n"
                    f"[Strategy context]\n{strategy.strategy_text}"
                )

                session_id = practice.chat_session_id
                # Attach to connection for any downstream handlers.
                if conn:
                    conn.session_id = session_id

                model_id = manager.get_model_id(websocket)

                full_response, assistant_message_id = await chat_service.handle_message(
                    session_id=session_id,
                    user_id=conn.user_id,
                    content=str(content).strip(),
                    message_id=None,
                    send_status=wrapped_send_status,
                    send_token=wrapped_send_token,
                    pipeline_run_id=pipeline_run_id,
                    request_id=request_id_uuid,
                    skills_context=None,
                    model_id=model_id,
                    platform=(getattr(conn, "platform", None)),
                    precomputed_assessment=None,
                )

                summary_service = SummaryService(db)
                await summary_service.check_and_trigger(session_id, wrapped_send_status)

                await manager.send_message(
                    websocket,
                    {
                        "type": "chat.complete",
                        "payload": {
                            "sessionId": str(session_id),
                            "messageId": str(assistant_message_id),
                            "content": full_response,
                            "role": "assistant",
                            "requestId": request_id,
                            "pipelineRunId": str(pipeline_run_id),
                            "practiceSessionId": str(practice_session_id),
                        },
                    },
                )

                return {
                    "assistant_message_id": str(assistant_message_id),
                    "interaction_id": str(assistant_message_id),
                }

        async def _wrapped_send_status(stage: str, stage_status: str, metadata: dict[str, Any] | None) -> None:
            await send_status(stage, stage_status, metadata)

        async def _wrapped_send_token(token: str) -> None:
            # We intentionally use the underlying chat sessionId for compatibility.
            chat_session_id = str(conn.session_id) if conn and conn.session_id else None
            if not chat_session_id:
                return
            await send_token(token, session_id=chat_session_id)

        await orchestrator.run(
            pipeline_run_id=pipeline_run_id,
            service="sailwind",
            mode="practice",
            quality_mode=quality_mode,
            trigger="sailwind.practice.message",
            request_id=request_id_uuid,
            session_id=(conn.session_id if conn else None),
            user_id=conn.user_id,
            org_id=org_id,
            send_status=_wrapped_send_status,
            send_token=_wrapped_send_token,
            runner=_runner,
        )

        await send_status(
            "pipeline",
            "completed",
            {
                "mode": "practice",
                "quality_mode": quality_mode,
            },
        )

    except asyncio.CancelledError:
        return
    except PracticeNotFoundError as exc:
        await _send_error(
            websocket,
            manager,
            code="NOT_FOUND",
            message=str(exc),
            request_id=request_id,
            pipeline_run_id=str(pipeline_run_id),
        )
        return
    except PracticeValidationError as exc:
        await _send_error(
            websocket,
            manager,
            code="BAD_REQUEST",
            message=str(exc),
            request_id=request_id,
            pipeline_run_id=str(pipeline_run_id),
        )
        return
    except Exception as exc:
        logger.error(
            "Practice message handling failed",
            extra={
                "service": "sailwind",
                "ws_id": id(websocket),
                "error": str(exc),
                "request_id": request_id,
                "pipeline_run_id": str(pipeline_run_id),
            },
            exc_info=True,
        )
        await _send_error(
            websocket,
            manager,
            code="PRACTICE_ERROR",
            message=f"Failed to process practice message: {str(exc)}",
            request_id=request_id,
            pipeline_run_id=str(pipeline_run_id),
        )
        return
