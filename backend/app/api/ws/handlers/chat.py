"""Chat message WebSocket handler."""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import WebSocket

from app.ai.providers.factory import get_llm_provider
from app.ai.substrate import (
    PipelineEventLogger,
    error_summary_to_stages_patch,
    error_summary_to_string,
    summarize_pipeline_error,
)
from app.ai.substrate.events import DbPipelineEventSink, set_event_sink
from app.ai.substrate.policy.gateway import PolicyDecision
from app.ai.substrate.stages import PipelineOrchestrator
from app.ai.stageflow.pipeline import get_chat_pipeline_runner
from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.database import get_session_context
from app.domains.summary.meta_summary import MetaSummaryService
from app.domains.chat.service import SUMMARY_THRESHOLD, ChatService
from app.logging_config import set_request_context
from app.models import Session, SummaryState
from app.models.observability import PipelineRun
from app.services.session_state import SessionStateService

logger = logging.getLogger("chat")

router = get_router()


async def send_chat_complete_once(
    *,
    full_response: str,
    assistant_message_id: uuid.UUID,
) -> None:
    """Send chat.complete event exactly once."""
    # This is a placeholder - the actual implementation would send to WebSocket
    pass


@router.handler("chat.typed")
async def handle_chat_typed(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle typed chat message (text input)."""
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate first",
                },
            },
        )
        return

    # Extract required fields
    content = payload.get("content", "")
    session_id_raw = payload.get("sessionId")
    topology = payload.get("topology", "chat_fast")
    behavior = payload.get("behavior", "fast")
    skill_ids_raw = payload.get("skillIds")
    platform = payload.get("platform", "web")

    # Validate session ID
    try:
        session_id = uuid.UUID(str(session_id_raw))
    except (ValueError, TypeError):
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_SESSION_ID",
                    "message": "Invalid session ID",
                },
            },
        )
        return

    user_id = conn.user_id
    org_id = conn.org_id
    request_id = str(uuid.uuid4())
    request_id_uuid = uuid.UUID(request_id)
    session_id_for_log = str(session_id)

    logger.info(
        "Handling typed chat message",
        extra={
            "service": "chat",
            "ws_id": id(websocket),
            "session_id": session_id_for_log,
            "user_id": str(user_id),
            "topology": topology,
            "behavior": behavior,
        },
    )

    # Create pipeline run for observability
    pipeline_run_id = uuid.uuid4()
    set_event_sink(DbPipelineEventSink())

    async def send_status(status: str, message_type: str, data: dict[str, Any] | None = None):
        await manager.send_message(
            websocket,
            {
                "type": message_type,
                "payload": {
                    "status": status,
                    "pipelineRunId": str(pipeline_run_id),
                    "requestId": request_id,
                    **(data or {}),
                },
            },
        )

    async def send_token(token: str):
        await manager.send_message(
            websocket,
            {
                "type": "chat.token",
                "payload": {
                    "token": token,
                    "pipelineRunId": str(pipeline_run_id),
                    "requestId": request_id,
                },
            },
        )

    # Skip assessment for typed input (always fast mode)
    skip_assessment = True
    is_accurate_mode = behavior == "accurate" and not skip_assessment

    # Process message with database session
    try:
        async with get_session_context() as db:
            chat_service = ChatService(db, llm_provider=get_llm_provider())
            # Note: SkillService disabled as skills feature is removed

            # Hybrid skills context resolution:
            # 1) Frontend sends skillIds (optional)
            # 2) Backend validates and fetches rubrics
            # 3) Fallback to tracked skills or generic prompt
            skills_context = None
            try:
                parsed_ids: list[uuid.UUID] | None = None
                if isinstance(skill_ids_raw, list) and skill_ids_raw:
                    parsed_ids = []
                    for raw in skill_ids_raw:
                        try:
                            parsed_ids.append(uuid.UUID(str(raw)))
                        except (ValueError, TypeError):
                            continue
                    if not parsed_ids:
                        parsed_ids = None
            except Exception as e:
                logger.warning(
                    "Failed to parse skill IDs",
                    extra={
                        "service": "chat",
                        "session_id": session_id_for_log,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                skills_context = None

            # Get effective model ID for this connection
            model_id = manager.get_model_id(websocket)

            # For accurate mode, assessment is disabled
            foreground_result = None

            # Handle the message (streams tokens via callbacks)
            full_response, assistant_message_id = await chat_service.handle_message_dag(
                session_id=session_id,
                user_id=user_id,
                content=content.strip(),
                message_id=None,
                send_status=send_status,
                send_token=send_token,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id_uuid,
                org_id=org_id,
                topology=topology,
                skills_context=skills_context,
                model_id=model_id,
                platform=platform,
                behavior=behavior,
                skill_ids=parsed_ids,
                db=db,
            )

            # Note: SummaryService disabled as assessment feature is removed
            await send_chat_complete_once(
                full_response=full_response,
                assistant_message_id=assistant_message_id,
            )

        async with get_session_context() as obs_db:
            event_logger = PipelineEventLogger(obs_db)
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.completed",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={"assistant_message_id": str(assistant_message_id)},
            )
            run = await obs_db.get(PipelineRun, pipeline_run_id)
            if run is not None:
                run.success = True
                run.error = None
                run.interaction_id = assistant_message_id

        logger.info(
            "Chat message handled successfully",
            extra={
                "service": "chat",
                "ws_id": id(websocket),
                "session_id": session_id_for_log,
                "assistant_message_id": str(assistant_message_id),
                "request_id": request_id,
            },
        )

    except Exception as e:
        logger.error(
            "Chat message handling failed",
            extra={
                "service": "chat",
                "ws_id": id(websocket),
                "session_id": session_id_for_log,
                "error": str(e),
            },
            exc_info=True,
        )

        # Send error to client
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "CHAT_ERROR",
                    "message": "Failed to process message",
                    "requestId": request_id,
                },
            },
        )

        # Log pipeline error
        async with get_session_context() as obs_db:
            event_logger = PipelineEventLogger(obs_db)
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.error",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={
                    "error": str(e),
                    "error_summary": summarize_pipeline_error(e),
                    "error_summary_stages": error_summary_to_stages_patch(e),
                    "error_summary_string": error_summary_to_string(e),
                },
            )
            run = await obs_db.get(PipelineRun, pipeline_run_id)
            if run is not None:
                run.success = False
                run.error = str(e)


@router.handler("chat.voice")
async def handle_chat_voice(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle voice chat message."""
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate first",
                },
            },
        )
        return

    # Extract required fields
    content = payload.get("content", "")
    session_id_raw = payload.get("sessionId")
    topology = payload.get("topology", "voice_fast")
    behavior = payload.get("behavior", "fast")
    skill_ids_raw = payload.get("skillIds")
    platform = payload.get("platform", "native")

    # Validate session ID
    try:
        session_id = uuid.UUID(str(session_id_raw))
    except (ValueError, TypeError):
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_SESSION_ID",
                    "message": "Invalid session ID",
                },
            },
        )
        return

    user_id = conn.user_id
    org_id = conn.org_id
    request_id = str(uuid.uuid4())
    request_id_uuid = uuid.UUID(request_id)
    session_id_for_log = str(session_id)

    logger.info(
        "Handling voice chat message",
        extra={
            "service": "chat",
            "ws_id": id(websocket),
            "session_id": session_id_for_log,
            "user_id": str(user_id),
            "topology": topology,
            "behavior": behavior,
        },
    )

    # Create pipeline run for observability
    pipeline_run_id = uuid.uuid4()
    set_event_sink(DbPipelineEventSink())

    async def send_status(status: str, message_type: str, data: dict[str, Any] | None = None):
        await manager.send_message(
            websocket,
            {
                "type": message_type,
                "payload": {
                    "status": status,
                    "pipelineRunId": str(pipeline_run_id),
                    "requestId": request_id,
                    **(data or {}),
                },
            },
        )

    async def send_token(token: str):
        await manager.send_message(
            websocket,
            {
                "type": "chat.token",
                "payload": {
                    "token": token,
                    "pipelineRunId": str(pipeline_run_id),
                    "requestId": request_id,
                },
            },
        )

    # Process message with database session
    try:
        async with get_session_context() as db:
            chat_service = ChatService(db, llm_provider=get_llm_provider())
            # Note: SkillService disabled as skills feature is removed

            # Hybrid skills context resolution:
            # 1) Frontend sends skillIds (optional)
            # 2) Backend validates and fetches rubrics
            # 3) Fallback to tracked skills or generic prompt
            skills_context = None
            try:
                parsed_ids: list[uuid.UUID] | None = None
                if isinstance(skill_ids_raw, list) and skill_ids_raw:
                    parsed_ids = []
                    for raw in skill_ids_raw:
                        try:
                            parsed_ids.append(uuid.UUID(str(raw)))
                        except (ValueError, TypeError):
                            continue
                    if not parsed_ids:
                        parsed_ids = None
            except Exception as e:
                logger.warning(
                    "Failed to parse skill IDs",
                    extra={
                        "service": "chat",
                        "session_id": session_id_for_log,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                skills_context = None

            # Get effective model ID for this connection
            model_id = manager.get_model_id(websocket)

            # For accurate mode, assessment is disabled
            foreground_result = None

            # Handle the message (streams tokens via callbacks)
            full_response, assistant_message_id = await chat_service.handle_message_dag(
                session_id=session_id,
                user_id=user_id,
                content=content.strip(),
                message_id=None,
                send_status=send_status,
                send_token=send_token,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id_uuid,
                org_id=org_id,
                topology=topology,
                skills_context=skills_context,
                model_id=model_id,
                platform=platform,
                behavior=behavior,
                skill_ids=parsed_ids,
                db=db,
            )

            # Note: SummaryService disabled as assessment feature is removed
            await send_chat_complete_once(
                full_response=full_response,
                assistant_message_id=assistant_message_id,
            )

        async with get_session_context() as obs_db:
            event_logger = PipelineEventLogger(obs_db)
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.completed",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={"assistant_message_id": str(assistant_message_id)},
            )
            run = await obs_db.get(PipelineRun, pipeline_run_id)
            if run is not None:
                run.success = True
                run.error = None
                run.interaction_id = assistant_message_id

        logger.info(
            "Voice chat message handled successfully",
            extra={
                "service": "chat",
                "ws_id": id(websocket),
                "session_id": session_id_for_log,
                "assistant_message_id": str(assistant_message_id),
                "request_id": request_id,
            },
        )

    except Exception as e:
        logger.error(
            "Voice chat message handling failed",
            extra={
                "service": "chat",
                "ws_id": id(websocket),
                "session_id": session_id_for_log,
                "error": str(e),
            },
            exc_info=True,
        )

        # Send error to client
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "CHAT_ERROR",
                    "message": "Failed to process message",
                    "requestId": request_id,
                },
            },
        )

        # Log pipeline error
        async with get_session_context() as obs_db:
            event_logger = PipelineEventLogger(obs_db)
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.error",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={
                    "error": str(e),
                    "error_summary": summarize_pipeline_error(e),
                    "error_summary_stages": error_summary_to_stages_patch(e),
                    "error_summary_string": error_summary_to_string(e),
                },
            )
            run = await obs_db.get(PipelineRun, pipeline_run_id)
            if run is not None:
                run.success = False
                run.error = str(e)
