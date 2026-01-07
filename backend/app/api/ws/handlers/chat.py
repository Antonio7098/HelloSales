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
from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.database import get_session_context
from app.domains.assessment.meta_summary import MetaSummaryService
from app.domains.assessment.pipeline import (
    ForegroundAssessmentResult,
    run_assessment_background,
    run_assessment_foreground,
)
from app.domains.assessment.summary import SummaryService
from app.domains.chat.service import SUMMARY_THRESHOLD, ChatService
from app.domains.skills.service import SkillService
from app.logging_config import set_request_context
from app.models import Session, SummaryState
from app.models.observability import PipelineRun
from app.services.session_state import SessionStateService

logger = logging.getLogger("chat")

router = get_router()


@router.handler("chat.message")
async def handle_chat_message(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle incoming chat.message from client (full assessment pipeline)."""
    await _handle_chat_message_common(
        websocket=websocket,
        payload=payload,
        manager=manager,
        skip_assessment=False,
    )


@router.handler("chat.typed")
async def handle_chat_typed(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle incoming chat.typed from client (typed input, skips assessment)."""
    await _handle_chat_message_common(
        websocket=websocket,
        payload=payload,
        manager=manager,
        skip_assessment=True,
    )


async def _handle_chat_message_common(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
    *,
    skip_assessment: bool,
) -> None:
    """Common handler for chat.message and chat.typed.

    Expected payload:
    {
        "sessionId": "uuid" | null,  // null to create new session
        "messageId": "uuid",          // optional, client-generated for deduplication
        "content": "Hello!",
        "skillIds": ["uuid1", "uuid2"]  // optional, tracked skill IDs for context
    }

    Sends:
    - session.created (if new session was created)
    - status.update (llm started/streaming/complete)
    - chat.token (streamed tokens)
    - chat.complete (final message)
    - error (if something fails)
    """
    # Get connection info
    conn = manager.get_connection(websocket)
    if not conn:
        logger.error(
            "Connection not found for chat message",
            extra={"service": "chat", "ws_id": id(websocket)},
        )
        return

    if not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before sending chat messages",
                },
            },
        )
        return

    user_id = conn.user_id
    platform = getattr(conn, "platform", None)
    previous_session_id = conn.session_id
    org_id = getattr(conn, "org_id", None)

    # Validate payload
    session_id_str = payload.get("sessionId")
    content = payload.get("content")
    message_id_str = payload.get("messageId")
    request_id_raw = payload.get("requestId")
    try:
        request_id_uuid = uuid.UUID(str(request_id_raw)) if request_id_raw else uuid.uuid4()
    except (ValueError, TypeError):
        request_id_uuid = uuid.uuid4()
    request_id = str(request_id_uuid)
    skill_ids_raw = payload.get("skillIds")  # optional list of skill IDs (strings)

    pipeline_run_id = uuid.uuid4()

    if not content or not content.strip():
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "content is required and cannot be empty",
                    "requestId": request_id,
                },
            },
        )
        return

    # Parse message ID
    try:
        message_id = uuid.UUID(message_id_str) if message_id_str else None
    except ValueError as e:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": f"Invalid messageId UUID format: {e}",
                    "requestId": request_id,
                },
            },
        )
        return

    # Handle session - create if null/empty
    session_id: uuid.UUID | None = None
    created_new_session = False

    if session_id_str:
        try:
            session_id = uuid.UUID(session_id_str)
        except ValueError as e:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "INVALID_PAYLOAD",
                        "message": f"Invalid sessionId UUID format: {e}",
                        "requestId": request_id,
                    },
                },
            )
            return

    # Create session if needed
    if not session_id:
        async with get_session_context() as db:
            session = Session(user_id=user_id)
            db.add(session)
            await db.flush()

            summary_state = SummaryState(session_id=session.id)
            db.add(summary_state)
            await db.commit()

            session_id = session.id
            created_new_session = True

            # Update connection with new session
            manager.authenticate(websocket, user_id, session_id)

            async def _run_meta_catch_up() -> None:
                try:
                    async with get_session_context() as meta_db:
                        result = await MetaSummaryService(
                            meta_db
                        ).merge_latest_unprocessed_summaries(
                            user_id=user_id,
                            max_sessions=1,
                            request_id=request_id_uuid,
                        )

                    if result is None:
                        logger.info(
                            "Meta summary catch-up no-op during implicit session creation",
                            extra={
                                "service": "chat",
                                "user_id": str(user_id),
                            },
                        )
                        return

                    meta, merged = result
                    source = merged[-1]

                    sent_count = await manager.send_to_user(
                        user_id,
                        {
                            "type": "meta_summary.updated",
                            "payload": {
                                "userId": str(user_id),
                                "trigger": "meta_summary.catch_up.chat.session_created",
                                "metaSummaryId": str(meta.id),
                                "text": meta.summary_text,
                                "updatedAt": meta.updated_at.isoformat(),
                                "sourceSessionId": str(source.session_id),
                                "sourceSessionSummaryId": str(source.id),
                            },
                        },
                    )
                    if sent_count == 0:
                        logger.info(
                            "Meta summary catch-up emitted to 0 connections during implicit session creation",
                            extra={
                                "service": "chat",
                                "user_id": str(user_id),
                            },
                        )
                except Exception as exc:
                    logger.warning(
                        "Meta summary catch-up failed during implicit session creation",
                        extra={
                            "service": "chat",
                            "user_id": str(user_id),
                            "previous_session_id": str(previous_session_id)
                            if previous_session_id
                            else None,
                            "error": str(exc),
                        },
                    )

            asyncio.create_task(_run_meta_catch_up())

            logger.info(
                "Session created on first message",
                extra={
                    "service": "chat",
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                },
            )

            # Notify client of new session
            await manager.send_message(
                websocket,
                {
                    "type": "session.created",
                    "payload": {
                        "sessionId": str(session_id),
                    },
                },
            )

            # Send initial summary cadence
            await manager.send_message(
                websocket,
                {
                    "type": "status.update",
                    "payload": {
                        "service": "summary",
                        "status": "idle",
                        "metadata": {
                            "turns_since": 0,
                            "turns_until_summary": SUMMARY_THRESHOLD,
                            "threshold": SUMMARY_THRESHOLD,
                        },
                    },
                },
            )

    session_id_for_log = str(session_id)

    set_request_context(
        request_id=request_id,
        user_id=str(user_id),
        session_id=session_id_for_log,
        pipeline_run_id=str(pipeline_run_id),
        org_id=str(org_id) if org_id else None,
    )

    set_event_sink(DbPipelineEventSink(run_service="chat"))

    if not skip_assessment:
        async with get_session_context() as obs_db:
            event_logger = PipelineEventLogger(obs_db)
            await event_logger.create_run(
                pipeline_run_id=pipeline_run_id,
                service="chat",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
            )
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.created",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={
                    "trigger": "chat.typed" if skip_assessment else "chat.message",
                    "message_id": str(message_id) if message_id else None,
                },
            )
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.started",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data=None,
            )

    logger.info(
        "Processing chat message",
        extra={
            "service": "chat",
            "ws_id": id(websocket),
            "user_id": str(user_id),
            "session_id": session_id_for_log,
            "message_id": message_id_str,
            "content_length": len(content),
            "request_id": request_id,
            "new_session": created_new_session,
        },
    )

    # Create callbacks for status and token streaming
    async def send_status(service: str, status: str, metadata: dict[str, Any] | None) -> None:
        raw_status = status
        normalized_status = status
        if status == "complete":
            normalized_status = "completed"
        elif status == "error":
            normalized_status = "failed"

        event_metadata = metadata or {}
        event_metadata.setdefault("requestId", request_id)
        event_metadata.setdefault("pipelineRunId", str(pipeline_run_id))
        event_metadata.setdefault("request_id", request_id)
        event_metadata.setdefault("pipeline_run_id", str(pipeline_run_id))
        await manager.send_message(
            websocket,
            {
                "type": "status.update",
                "payload": {
                    "service": service,
                    "status": normalized_status,
                    "metadata": event_metadata,
                },
            },
        )

        # Eval-only observability events (do not send to native clients)
        if conn and conn.user_id:
            if (
                service == "summary"
                and status == "idle"
                and event_metadata.get("event") == "summary.cadence"
            ):
                await manager.send_to_user_platform(
                    conn.user_id,
                    "web",
                    {
                        "type": "summary.cadence",
                        "payload": {
                            "sessionId": event_metadata.get("sessionId") or session_id_for_log,
                            "turnsSince": event_metadata.get("turns_since"),
                            "turnsUntilSummary": event_metadata.get("turns_until_summary"),
                            "threshold": event_metadata.get("threshold"),
                        },
                    },
                )

            if service == "summary" and raw_status == "complete" and event_metadata.get("summary_text"):
                await manager.send_to_user_platform(
                    conn.user_id,
                    "web",
                    {
                        "type": "summary.generated",
                        "payload": {
                            "sessionId": session_id_for_log,
                            "version": event_metadata.get("version"),
                            "interactionCount": event_metadata.get("interaction_count"),
                            "durationMs": event_metadata.get("duration_ms"),
                            "summaryText": event_metadata.get("summary_text"),
                            "transcriptSlice": event_metadata.get("transcript_slice"),
                            "transcriptSliceTotal": event_metadata.get("transcript_slice_total"),
                        },
                    },
                )

    # Track streaming state
    streaming_complete = False

    async def send_token(token: str, is_complete: bool = False) -> None:
        nonlocal streaming_complete
        if is_complete and not streaming_complete:
            streaming_complete = True
        await manager.send_message(
            websocket,
            {
                "type": "chat.token",
                "payload": {
                    "sessionId": session_id_for_log,
                    "token": token,
                    "isComplete": is_complete,
                },
            },
        )

    # Get pipeline mode for this connection (fallback for legacy clients)
    pipeline_mode = manager.get_pipeline_mode(websocket)
    is_accurate_mode = pipeline_mode in ("accurate", "accurate_filler")

    # Get topology and behavior from SessionState (with fallback to connection mode)
    async with get_session_context() as db:
        session_state_service = SessionStateService(session=db)
        try:
            state = await session_state_service.get_or_create(session_id)
            topology = state.topology
            behavior = state.behavior
        except Exception as e:
            logger.warning(
                "Failed to load session state, using defaults",
                extra={
                    "service": "chat",
                    "session_id": session_id_for_log,
                    "error": str(e),
                },
            )
            topology = "chat_accurate" if is_accurate_mode else "chat_fast"
            behavior = pipeline_mode or "practice"

    chat_complete_sent = False

    async def send_chat_complete_once(
        *, full_response: str, assistant_message_id: uuid.UUID
    ) -> None:
        nonlocal chat_complete_sent
        if chat_complete_sent:
            logger.warning(
                "Skipping duplicate chat.complete send",
                extra={
                    "service": "chat",
                    "ws_id": id(websocket),
                    "session_id": session_id_for_log,
                    "request_id": request_id,
                    "pipeline_run_id": str(pipeline_run_id),
                },
            )
            return
        chat_complete_sent = True
        await manager.send_message(
            websocket,
            {
                "type": "chat.complete",
                "payload": {
                    "sessionId": session_id_for_log,
                    "messageId": str(assistant_message_id),
                    "content": full_response,
                    "role": "assistant",
                    "requestId": request_id,
                    "pipelineRunId": str(pipeline_run_id),
                },
            },
        )

    logger.info(
        "Chat pipeline mode",
        extra={
            "service": "chat",
            "session_id": session_id_for_log,
            "pipeline_mode": pipeline_mode,
            "is_accurate_mode": is_accurate_mode,
            "skip_assessment": skip_assessment,
        },
    )

    if skip_assessment:
        orchestrator = PipelineOrchestrator()

        try:
            await send_status(
                "pipeline",
                "running",
                {
                    "behavior": "typed",
                    "topology": topology,
                },
            )

            async def _runner(
                wrapped_send_status,
                wrapped_send_token,
            ) -> dict[str, Any]:
                async with get_session_context() as db:
                    chat_service = ChatService(db, llm_provider=get_llm_provider())
                    skill_service = SkillService(db)

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

                        skills_context = await skill_service.get_skill_context_for_llm(
                            user_id=user_id,
                            skill_ids=parsed_ids,
                        )
                    except Exception as e:  # pragma: no cover - defensive
                        logger.warning(
                            "Failed to build skills context for chat",
                            extra={
                                "service": "chat",
                                "user_id": str(user_id),
                                "session_id": session_id_for_log,
                                "error": str(e),
                            },
                            exc_info=True,
                        )
                        skills_context = None

                    model_id = manager.get_model_id(websocket)

                    full_response, assistant_message_id = await chat_service.handle_message_dag(
                        session_id=session_id,
                        user_id=user_id,
                        content=content.strip(),
                        message_id=message_id,
                        send_status=wrapped_send_status,
                        send_token=wrapped_send_token,
                        pipeline_run_id=pipeline_run_id,
                        request_id=request_id_uuid,
                        org_id=org_id,
                        topology="chat_fast",  # chat.typed skips assessment
                        skills_context=skills_context,
                        model_id=model_id,
                        platform=platform,
                        behavior="fast",  # chat.typed skips assessment
                        skill_ids=parsed_ids,
                        db=db,
                    )

                    summary_service = SummaryService(db)
                    await summary_service.check_and_trigger(session_id, wrapped_send_status)

                    await send_chat_complete_once(
                        full_response=full_response,
                        assistant_message_id=assistant_message_id,
                    )

                    try:
                        await manager.send_message(
                            websocket,
                            {
                                "type": "assessment.skipped",
                                "payload": {
                                    "reason": "typed_input",
                                    "interactionId": str(message_id) if message_id else None,
                                },
                            },
                        )
                    except Exception as exc:  # pragma: no cover - best-effort only
                        logger.warning(
                            "Failed to send assessment.skipped for typed message",
                            extra={
                                "service": "chat",
                                "ws_id": id(websocket),
                                "session_id": session_id_for_log,
                                "error": str(exc),
                                "request_id": request_id,
                            },
                            exc_info=True,
                        )

                    return {
                        "assistant_message_id": str(assistant_message_id),
                        "interaction_id": str(assistant_message_id),
                        "success": bool(
                            not getattr(chat_service, "_policy_last_result", None)
                            or getattr(
                                getattr(chat_service, "_policy_last_result", None), "decision", None
                            )
                            == PolicyDecision.ALLOW
                        ),
                        "error": (
                            None
                            if (
                                not getattr(chat_service, "_policy_last_result", None)
                                or getattr(
                                    getattr(chat_service, "_policy_last_result", None),
                                    "decision",
                                    None,
                                )
                                == PolicyDecision.ALLOW
                            )
                            else "policy.blocked"
                        ),
                    }

            await orchestrator.run(
                pipeline_run_id=pipeline_run_id,
                service="chat",
                topology=topology,
                behavior=behavior,
                trigger="chat.typed",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                send_status=send_status,
                send_token=send_token,
                runner=_runner,
            )

            await send_status(
                "pipeline",
                "completed",
                {
                    "behavior": "typed",
                    "topology": topology,
                },
            )

            logger.info(
                "Chat message handled successfully",
                extra={
                    "service": "chat",
                    "ws_id": id(websocket),
                    "session_id": session_id_for_log,
                    "request_id": request_id,
                },
            )

            return
        except Exception as e:
            logger.error(
                "Chat message handling failed",
                extra={
                    "service": "chat",
                    "ws_id": id(websocket),
                    "session_id": session_id_for_log,
                    "error": str(e),
                    "request_id": request_id,
                    "pipeline_run_id": str(pipeline_run_id),
                },
                exc_info=True,
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "CHAT_ERROR",
                        "message": f"Failed to process message: {str(e)}",
                        "requestId": request_id,
                        "pipelineRunId": str(pipeline_run_id),
                    },
                },
            )

        return

    try:
        # Process message with database session
        async with get_session_context() as db:
            chat_service = ChatService(db, llm_provider=get_llm_provider())
            skill_service = SkillService(db)

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
                            # Ignore invalid IDs; backend will fall back if all invalid
                            continue
                    if not parsed_ids:
                        parsed_ids = None

                skills_context = await skill_service.get_skill_context_for_llm(
                    user_id=user_id,
                    skill_ids=parsed_ids,
                )
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(
                    "Failed to build skills context for chat",
                    extra={
                        "service": "chat",
                        "user_id": str(user_id),
                        "session_id": session_id_for_log,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                skills_context = None

            # Get effective model ID for this connection
            model_id = manager.get_model_id(websocket)

            # For accurate mode, run assessment BEFORE the LLM call
            foreground_result: ForegroundAssessmentResult | None = None

            if is_accurate_mode and not skip_assessment:
                logger.info(
                    "Running foreground assessment (accurate mode)",
                    extra={
                        "service": "chat",
                        "session_id": session_id_for_log,
                        "user_id": str(user_id),
                    },
                )

                foreground_result = await run_assessment_foreground(
                    db=db,
                    session_id=session_id,
                    user_id=user_id,
                    user_message=content.strip(),
                    raw_skill_ids=parsed_ids,
                    send_status=send_status,
                    model_id=model_id,
                    interaction_id=None,  # Not committed yet
                )

                if foreground_result.skipped:
                    # Send assessment.skipped to client
                    await manager.send_message(
                        websocket,
                        {
                            "type": "assessment.skipped",
                            "payload": {
                                "reason": foreground_result.skip_reason,
                                "interactionId": str(message_id) if message_id else None,
                            },
                        },
                    )
                    logger.info(
                        "Foreground assessment skipped",
                        extra={
                            "service": "chat",
                            "session_id": session_id_for_log,
                            "reason": foreground_result.skip_reason,
                        },
                    )
                elif foreground_result.assessment_response:
                    # Send assessment.complete to client
                    assessment_resp = foreground_result.assessment_response
                    await manager.send_message(
                        websocket,
                        {
                            "type": "assessment.complete",
                            "payload": {
                                "assessmentId": (
                                    str(assessment_resp.assessment_id)
                                    if assessment_resp.assessment_id
                                    else None
                                ),
                                "sessionId": str(session_id),
                                "interactionId": str(message_id) if message_id else None,
                                "triageDecision": assessment_resp.triage_decision,
                                "triageOverrideLabel": assessment_resp.triage_override_label,
                                "userResponse": assessment_resp.user_response,
                                "skills": [
                                    {
                                        "skillId": str(s.skill_id),
                                        "level": s.level,
                                        "confidence": s.confidence,
                                        "summary": s.summary,
                                        "feedback": {
                                            "primaryTakeaway": s.feedback.primary_takeaway,
                                            "strengths": s.feedback.strengths,
                                            "improvements": s.feedback.improvements,
                                            "exampleQuotes": [
                                                q.model_dump() for q in s.feedback.example_quotes
                                            ],
                                            "nextLevelCriteria": s.feedback.next_level_criteria,
                                        },
                                        "provider": s.provider,
                                        "model": s.model,
                                    }
                                    for s in assessment_resp.skills
                                ],
                                "metrics": (
                                    assessment_resp.metrics.model_dump()
                                    if assessment_resp.metrics
                                    else None
                                ),
                            },
                        },
                    )
                    logger.info(
                        "Foreground assessment complete, injecting into LLM context",
                        extra={
                            "service": "chat",
                            "session_id": session_id_for_log,
                            "skill_count": len(assessment_resp.skills),
                        },
                    )

            # Handle the message (streams tokens via callbacks)
            full_response, assistant_message_id = await chat_service.handle_message_dag(
                session_id=session_id,
                user_id=user_id,
                content=content.strip(),
                message_id=message_id,
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
                skill_ids=payload.get("skillIds"),
                db=db,
            )

            # After each assistant response, check whether we should generate a
            # rolling summary for long‑term context (mirrors voice pipeline).
            summary_service = SummaryService(db)
            await summary_service.check_and_trigger(session_id, send_status)

            # Send chat.complete with full response
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

        # For fast mode (non-accurate), kick off background triage + assessment
        if not skip_assessment and not is_accurate_mode:
            asyncio.create_task(
                run_assessment_background(
                    manager=manager,
                    websocket=websocket,
                    session_id=session_id,
                    user_id=user_id,
                    user_message=content.strip(),
                    raw_skill_ids=None,
                    send_status=send_status,
                    model_id=model_id,
                )
            )
        elif skip_assessment:
            # For typed messages, explicitly mark assessment as skipped
            try:
                await manager.send_message(
                    websocket,
                    {
                        "type": "assessment.skipped",
                        "payload": {
                            "reason": "typed_input",
                            "interactionId": str(message_id) if message_id else None,
                        },
                    },
                )
            except Exception as exc:  # pragma: no cover - best-effort only
                logger.warning(
                    "Failed to send assessment.skipped for typed message",
                    extra={
                        "service": "chat",
                        "ws_id": id(websocket),
                        "session_id": session_id_for_log,
                        "error": str(exc),
                        "request_id": request_id,
                    },
                    exc_info=True,
                )

    except Exception as e:
        error_summary = summarize_pipeline_error(e)
        error_text = error_summary_to_string(error_summary)
        async with get_session_context() as obs_db:
            event_logger = PipelineEventLogger(obs_db)
            await event_logger.create_run(
                pipeline_run_id=pipeline_run_id,
                service="chat",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
            )
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.failed",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={"error": error_summary},
            )
            run = await obs_db.get(PipelineRun, pipeline_run_id)
            if run is not None:
                run.success = False
                run.error = error_text
                patch = error_summary_to_stages_patch(error_summary)
                if isinstance(run.stages, dict):
                    run.stages = {**run.stages, **patch}
                else:
                    run.stages = patch

        logger.error(
            "Chat message handling failed",
            extra={
                "service": "chat",
                "ws_id": id(websocket),
                "session_id": session_id_for_log,
                "error": error_text,
                "request_id": request_id,
                "pipeline_run_id": str(pipeline_run_id),
            },
            exc_info=True,
        )
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "CHAT_ERROR",
                    "message": f"Failed to process message: {str(e)}",
                    "requestId": request_id,
                    "pipelineRunId": str(pipeline_run_id),
                },
            },
        )
