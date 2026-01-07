"""Voice message WebSocket handlers."""

import asyncio
import base64
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket

from app.ai.substrate import (
    PipelineEventLogger,
    error_summary_to_stages_patch,
    error_summary_to_string,
    summarize_pipeline_error,
)
from app.ai.substrate.events import DbPipelineEventSink, set_event_sink
from app.api.ws.manager import ConnectionManager, PipelineMode
from app.api.ws.router import get_router
from app.database import get_session_context
from app.domains.assessment.meta_summary import MetaSummaryService
from app.domains.assessment.pipeline import (
    run_assessment_background,
    run_assessment_foreground,
)
from app.domains.assessment.summary import SummaryService
from app.domains.chat.service import SUMMARY_THRESHOLD, PrefetchedEnrichers
from app.domains.voice.service import VoiceService
from app.logging_config import set_request_context
from app.models import PipelineRun, Session, SummaryState

logger = logging.getLogger("voice")


# Timing helper
def now_ms() -> int:
    return int(time.time() * 1000)


# Filler phrases for accurate_filler mode (randomized later if needed)
FILLER_PHRASES = [
    "Let me think about that for a moment.",
    "One moment while I analyze your response.",
    "Give me a second to process that.",
]


async def _prefetch_enrichers_standalone(session_id: uuid.UUID) -> PrefetchedEnrichers:
    """Run enricher prefetch with its own DB session.

    This ensures the prefetch task survives after the voice.start handler exits,
    since it doesn't depend on the handler's DB session lifecycle.
    """
    from app.ai.providers.factory import get_llm_provider
    from app.domains.chat.service import ChatService

    async with get_session_context() as db:
        chat = ChatService(db, llm_provider=get_llm_provider())
        return await chat.prefetch_enrichers(session_id)


# Store VoiceService instances per user (need to persist recording state)
# In production, this should be handled differently (e.g., Redis)
_voice_services: dict[uuid.UUID, VoiceService] = {}


async def _send_filler_audio(
    *,
    manager: ConnectionManager,
    websocket: Any,
    session_id: uuid.UUID,
    send_status: Any,
) -> None:
    """Synthesize and send filler audio to cover assessment latency.

    Used in accurate_filler mode to provide feedback while waiting.
    """
    import random

    from app.ai.providers.factory import get_tts_provider

    filler_text = random.choice(FILLER_PHRASES)

    try:
        if send_status:
            await send_status(
                "filler",
                "started",
                {"text": filler_text},
            )

        tts = get_tts_provider()
        tts_result = await tts.synthesize(
            text=filler_text,
            voice="male",
            format="mp3",
            speed=1.0,
        )

        # Send as a voice audio chunk
        import base64 as b64

        audio_b64 = b64.b64encode(tts_result.audio_data).decode("utf-8")
        await manager.send_message(
            websocket,
            {
                "type": "voice.audio.chunk",
                "payload": {
                    "sessionId": str(session_id),
                    "data": audio_b64,
                    "format": "mp3",
                    "durationMs": tts_result.duration_ms,
                    "isFinal": False,
                    "isFiller": True,  # Mark as filler so client can handle differently
                },
            },
        )

        if send_status:
            await send_status(
                "filler",
                "complete",
                {"durationMs": tts_result.duration_ms},
            )

        logger.debug(
            "Filler audio sent",
            extra={
                "service": "voice",
                "session_id": str(session_id),
                "filler_text": filler_text,
                "duration_ms": tts_result.duration_ms,
            },
        )

    except Exception as e:
        logger.warning(
            "Failed to send filler audio",
            extra={
                "service": "voice",
                "session_id": str(session_id),
                "error": str(e),
            },
            exc_info=True,
        )
        # Non-fatal - continue without filler


async def _get_voice_service(user_id: uuid.UUID) -> VoiceService:
    """Get or create a VoiceService for a user.

    Note: VoiceService holds recording state in memory, so we reuse
    the same instance for a user across handlers. The database session
    is passed to methods that need it rather than stored.
    """
    if user_id not in _voice_services:
        _voice_services[user_id] = VoiceService(db=None)
    return _voice_services[user_id]


@get_router().handler("voice.recording")
async def handle_voice_recording(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before sending voice messages",
                },
            },
        )
        return

    audio_data_raw = payload.get("audioData")
    if not audio_data_raw:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Missing audioData",
                    "requestId": payload.get("requestId"),
                },
            },
        )
        return

    request_id = payload.get("requestId")
    audio_format = payload.get("format")
    if not audio_format and isinstance(audio_data_raw, str) and audio_data_raw.startswith("data:audio/"):
        try:
            header = audio_data_raw.split(";base64,", 1)[0]
            audio_format = header.split("data:audio/", 1)[1]
        except Exception:
            audio_format = None
    audio_format = str(audio_format or "wav")

    try:
        audio_b64 = audio_data_raw
        if isinstance(audio_data_raw, str) and "base64," in audio_data_raw:
            audio_b64 = audio_data_raw.split("base64,", 1)[1]
        audio_bytes = base64.b64decode(audio_b64)
    except Exception as exc:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "DECODE_ERROR",
                    "message": f"Failed to decode audioData: {exc}",
                    "requestId": request_id,
                },
            },
        )
        return

    await handle_voice_start(
        websocket,
        {
            "sessionId": payload.get("sessionId"),
            "format": audio_format,
            "requestId": request_id,
            "skillIds": payload.get("skillIds"),
        },
        manager,
    )

    async with get_session_context() as db:
        voice_service = await _get_voice_service(conn.user_id)
        voice_service._ensure_db_components(db)
        voice_service.add_chunk(conn.user_id, audio_bytes)

    await handle_voice_end(
        websocket,
        {
            "messageId": payload.get("messageId"),
            "requestId": request_id,
        },
        manager,
    )


@get_router().handler("voice.start")
async def handle_voice_start(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle voice.start - begin recording.

    Expected payload:
    {
        "sessionId": "uuid" | null,  // null to create new session
        "format": "webm"             // audio format (optional, default: webm)
    }

    Sends:
    - session.created (if new session was created)
    - status.update (mic: recording)
    - error (if something fails)
    """
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before sending voice messages",
                },
            },
        )
        return

    user_id = conn.user_id
    previous_session_id = conn.session_id
    request_id = payload.get("requestId")

    # Parse session ID and optional skill IDs
    session_id_str = payload.get("sessionId")
    audio_format = payload.get("format", "webm")
    skill_ids_raw = payload.get("skillIds")  # optional list of skill IDs (strings)
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
                    request_id_uuid = None
                    try:
                        request_id_uuid = uuid.UUID(str(request_id)) if request_id else None
                    except (ValueError, TypeError):
                        request_id_uuid = None

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
                            "Meta summary catch-up no-op during voice session creation",
                            extra={
                                "service": "voice",
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
                                "trigger": "meta_summary.catch_up.voice.session_created",
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
                            "Meta summary catch-up emitted to 0 connections during voice session creation",
                            extra={
                                "service": "voice",
                                "user_id": str(user_id),
                            },
                        )
                except Exception as exc:
                    logger.warning(
                        "Meta summary catch-up failed during voice session creation",
                        extra={
                            "service": "voice",
                            "user_id": str(user_id),
                            "previous_session_id": str(previous_session_id)
                            if previous_session_id
                            else None,
                            "error": str(exc),
                        },
                    )

            asyncio.create_task(_run_meta_catch_up())

            logger.info(
                "Session created for voice",
                extra={
                    "service": "voice",
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

    # Parse skill IDs to UUIDs (ignore any invalid values)
    parsed_skill_ids: list[uuid.UUID] | None = None
    if isinstance(skill_ids_raw, list) and skill_ids_raw:
        parsed_skill_ids = []
        for raw in skill_ids_raw:
            try:
                parsed_skill_ids.append(uuid.UUID(str(raw)))
            except (ValueError, TypeError):
                continue
        if not parsed_skill_ids:
            parsed_skill_ids = None

    # Initialize voice service, optionally prefetch enrichers, and start recording
    async with get_session_context() as db:
        voice_service = await _get_voice_service(user_id)

        # Kick off enricher prefetch in the background for this session to reduce
        # latency in the later build_context step. This runs independently of STT.
        enricher_prefetch_task: asyncio.Task | None = None
        try:
            enricher_prefetch_task = asyncio.create_task(_prefetch_enrichers_standalone(session_id))
        except Exception:
            # Defensive: if prefetch setup fails, continue without it.
            logger.exception(
                "Failed to start enricher prefetch task for voice session",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                },
            )

        # Parse optional skill IDs
        skill_ids: list[uuid.UUID] | None = None
        if isinstance(skill_ids_raw, list):
            parsed_ids: list[uuid.UUID] = []
            for raw_id in skill_ids_raw:
                try:
                    parsed_ids.append(uuid.UUID(str(raw_id)))
                except (ValueError, TypeError):
                    logger.warning(
                        "Invalid skill ID in voice.start payload",
                        extra={
                            "service": "voice",
                            "user_id": str(user_id),
                            "session_id": str(session_id),
                            "raw_id": str(raw_id),
                        },
                    )
            if parsed_ids:
                skill_ids = parsed_ids

        voice_service._ensure_db_components(db)
        voice_service.start_recording(
            session_id=session_id,
            user_id=user_id,
            audio_format=audio_format,
            skill_ids=skill_ids,
            enricher_prefetch_task=enricher_prefetch_task,
        )

    logger.info(
        "Voice recording started",
        extra={
            "service": "voice",
            "user_id": str(user_id),
            "session_id": str(session_id),
            "format": audio_format,
            "new_session": created_new_session,
        },
    )

    # Send recording status
    await manager.send_message(
        websocket,
        {
            "type": "status.update",
            "payload": {
                "service": "mic",
                "status": "recording",
                "metadata": {
                    "sessionId": str(session_id),
                    "format": audio_format,
                },
            },
        },
    )


@get_router().handler("voice.chunk")
async def handle_voice_chunk(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle voice.chunk - receive audio data during recording.

    Expected payload:
    {
        "data": "base64_encoded_audio"
    }

    Sends:
    - error (if no active recording or decode fails)
    """
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        return  # Silently ignore if not authenticated

    user_id = conn.user_id

    # Decode base64 audio data
    data_b64 = payload.get("data")
    if not data_b64:
        logger.warning(
            "Voice chunk missing data",
            extra={"service": "voice", "user_id": str(user_id)},
        )
        return

    try:
        # Allow data URIs (e.g., "data:audio/wav;base64,...") by stripping header
        if isinstance(data_b64, str) and data_b64.startswith("data:"):
            try:
                data_b64 = data_b64.split(",", 1)[1]
            except IndexError:
                raise ValueError("Invalid data URI payload")
        audio_data = base64.b64decode(data_b64)
    except Exception as e:
        logger.warning(
            "Failed to decode voice chunk",
            extra={"service": "voice", "user_id": str(user_id), "error": str(e)},
        )
        return

    # Add chunk to recording
    async with get_session_context() as db:
        voice_service = await _get_voice_service(user_id)
        voice_service._ensure_db_components(db)
        success = voice_service.add_chunk(user_id, audio_data)

    if not success:
        logger.warning(
            "No active recording for voice chunk",
            extra={"service": "voice", "user_id": str(user_id)},
        )
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NO_ACTIVE_RECORDING",
                    "message": "No active recording. Call voice.start first.",
                },
            },
        )


@get_router().handler("voice.end")
async def handle_voice_end(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle voice.end - finish recording and process pipeline.

    Expected payload:
    {
        "messageId": "uuid"  // optional, client-generated for deduplication
    }

    Sends:
    - status.update (stt/llm/tts stages)
    - voice.transcript (STT result)
    - chat.token (streamed LLM tokens)
    - voice.audio (TTS result)
    - chat.complete (final message)
    - error (if processing fails)
    """
    try:
        with open("/tmp/debug_voice_handler.log", "a") as f:
            f.write(f"[{datetime.now(UTC)}] handle_voice_end entered\n")
    except Exception:
        pass

    # payload is already a dict parsed by the router
    session_id = payload.get("session_id")
    logger.info(f"Processing voice end for session {session_id}")

    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before processing voice",
                },
            },
        )
        return

    user_id = conn.user_id
    platform = getattr(conn, "platform", None)
    org_id = getattr(conn, "org_id", None)
    request_id_raw = payload.get("requestId")
    try:
        request_id_uuid = uuid.UUID(str(request_id_raw)) if request_id_raw else uuid.uuid4()
    except (ValueError, TypeError):
        request_id_uuid = uuid.uuid4()
    request_id = str(request_id_uuid)
    message_id_str = payload.get("messageId")

    pipeline_run_id = uuid.uuid4()

    # Parse message ID
    try:
        message_id = uuid.UUID(message_id_str) if message_id_str else None
    except ValueError:
        message_id = None

    # Get recording state
    start_time = now_ms()
    try:
        with open("/tmp/debug_voice_handler.log", "a") as f:
            f.write(f"[{datetime.now(UTC)}] handle_voice_end: about to get recording state for user {user_id}\n")
    except Exception:
        pass

    async with get_session_context() as db:
        voice_service = await _get_voice_service(user_id)
        voice_service._ensure_db_components(db)
        recording_state = voice_service.get_recording_state(user_id)

    try:
        with open("/tmp/debug_voice_handler.log", "a") as f:
            f.write(f"[{datetime.now(UTC)}] handle_voice_end: got recording_state={recording_state is not None}\n")
    except Exception:
        pass

    if not recording_state:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NO_ACTIVE_RECORDING",
                    "message": "No active recording to process",
                    "requestId": request_id,
                },
            },
        )
        return

    session_id = recording_state.session_id

    logger.info(
        "[TIMING][backend] voice.end_received",
        extra={
            "service": "voice",
            "t": start_time,
            "user_id": str(user_id),
            "session_id": str(session_id) if session_id else None,
            "request_id": request_id,
            "pipeline_run_id": str(pipeline_run_id),
        },
    )

    set_request_context(
        request_id=request_id,
        user_id=str(user_id),
        session_id=str(session_id),
        pipeline_run_id=str(pipeline_run_id),
        org_id=str(org_id) if org_id else None,
    )

    set_event_sink(DbPipelineEventSink(run_service="voice"))

    async with get_session_context() as obs_db:
        event_logger = PipelineEventLogger(obs_db)
        await event_logger.create_run(
            pipeline_run_id=pipeline_run_id,
            service="voice",
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
                "trigger": "voice.end",
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
        "Processing voice recording",
        extra={
            "service": "voice",
            "user_id": str(user_id),
            "session_id": str(session_id),
            "chunks": len(recording_state.chunks),
        },
    )

    # Stop recording status
    await manager.send_message(
        websocket,
        {
            "type": "status.update",
            "payload": {
                "service": "mic",
                "status": "stopped",
                "metadata": {"chunks": len(recording_state.chunks)},
            },
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

        # Debug logging for assessment events
        if service == "assessment":
            import logging
            logger = logging.getLogger("voice_handler")
            logger.info(f"[VOICE_HANDLER] Sending assessment status: {normalized_status}, metadata: {event_metadata}")

        # Debug logging for LLM events
        if service == "llm":
            import logging
            logger = logging.getLogger("voice_handler")
            logger.info(f"[VOICE_HANDLER] Sending LLM status: {normalized_status}, metadata: {event_metadata}")

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
                            "sessionId": str(session_id),
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
                            "sessionId": str(session_id),
                            "version": event_metadata.get("version"),
                            "interactionCount": event_metadata.get("interaction_count"),
                            "durationMs": event_metadata.get("duration_ms"),
                            "summaryText": event_metadata.get("summary_text"),
                            "transcriptSlice": event_metadata.get("transcript_slice"),
                            "transcriptSliceTotal": event_metadata.get("transcript_slice_total"),
                        },
                    },
                )

    async def send_token(token: str) -> None:
        logger.info(
            "[TIMING] WS send chat.token",
            extra={
                "service": "ws",
                "timing": "ws_send_chat_token",
                "session_id": str(session_id),
                "request_id": str(request_id),
                "pipeline_run_id": str(pipeline_run_id),
                "token_preview": token[:20],
            },
        )
        await manager.send_message(
            websocket,
            {
                "type": "chat.token",
                "payload": {
                    "sessionId": str(session_id),
                    "token": token,
                },
            },
        )

    async def send_transcript(
        msg_id: uuid.UUID,
        transcript: str,
        confidence: float,
        duration_ms: int,
    ) -> None:
        """Send transcript message immediately after STT completes."""
        await manager.send_message(
            websocket,
            {
                "type": "voice.transcript",
                "payload": {
                    "sessionId": str(session_id),
                    "messageId": str(msg_id),
                    "transcript": transcript,
                    "confidence": confidence,
                    "durationMs": duration_ms,
                },
            },
        )

    # Track if incremental audio was sent
    incremental_audio_sent = False

    async def send_audio_chunk(
        audio_data: bytes,
        format: str,
        duration_ms: int,
        is_final: bool,
    ) -> None:
        """Send incremental TTS audio chunk as sentences complete."""
        nonlocal incremental_audio_sent

        logger.info(
            "[TTS-CALLBACK] send_audio_chunk called",
            extra={
                "service": "voice",
                "session_id": str(session_id),
                "audio_data_len": len(audio_data) if audio_data else 0,
                "duration_ms": duration_ms,
                "is_final": is_final,
            },
        )

        if audio_data:  # Only send non-empty chunks
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            logger.info(
                "[TIMING] WS send voice.audio.chunk",
                extra={
                    "service": "ws",
                    "timing": "ws_send_voice_audio_chunk",
                    "session_id": str(session_id),
                    "request_id": str(request_id),
                    "pipeline_run_id": str(pipeline_run_id),
                    "audio_bytes": len(audio_data),
                    "duration_ms": duration_ms,
                    "is_final": is_final,
                },
            )
            logger.info(
                "[TTS-CALLBACK] About to send WebSocket message",
                extra={
                    "service": "voice",
                    "session_id": str(session_id),
                    "audio_b64_len": len(audio_b64),
                    "format": format,
                    "duration_ms": duration_ms,
                    "is_final": is_final,
                },
            )
            await manager.send_message(
                websocket,
                {
                    "type": "voice.audio.chunk",
                    "payload": {
                        "sessionId": str(session_id),
                        "data": audio_b64,
                        "format": format,
                        "durationMs": duration_ms,
                        "isFinal": is_final,
                        "interactionId": str(message_id)
                        if message_id
                        else None,  # Add correlation ID
                    },
                },
            )
            logger.info(
                "[TTS-CALLBACK] WebSocket message sent successfully",
                extra={
                    "service": "voice",
                    "session_id": str(session_id),
                },
            )
            incremental_audio_sent = True

    # Get effective pipeline mode for this connection
    pipeline_mode: PipelineMode = manager.get_pipeline_mode(websocket)

    # Convert to topology and behavior
    is_accurate = pipeline_mode in ("accurate", "accurate_filler")
    topology = "voice_accurate" if is_accurate else "voice_fast"
    behavior = pipeline_mode

    logger.info(
        "Voice pipeline mode",
        extra={
            "service": "voice",
            "user_id": str(user_id),
            "session_id": str(session_id),
            "topology": topology,
            "behavior": behavior,
        },
    )

    # Holder for triage/assessment result to include in chat.complete
    # This is populated by on_interaction_saved callback
    triage_result_holder: dict[str, Any] = {
        "completed": False,
        "skipped": False,
        "reason": None,
        "assessmentId": None,
        "mode": pipeline_mode,
    }

    async def on_interaction_saved(msg_id: uuid.UUID, transcript: str) -> None:
        """Handle triage + assessment based on pipeline mode.

        - fast: runs in background (non-blocking), no interaction_id to avoid FK issues
        - accurate: awaits assessment (blocking, ensures it's in LLM context)
        - accurate_filler: sends filler audio, then awaits assessment

        Args:
            msg_id: The interaction ID (same as message_id).
            transcript: The user's transcribed message.
        """
        logger.info(
            "on_interaction_saved invoked",
            extra={
                "service": "voice",
                "session_id": str(session_id),
                "user_id": str(user_id),
                "message_id": str(msg_id),
                "pipeline_mode": pipeline_mode,
                "transcript_length": len(transcript),
            },
        )

        if pipeline_mode == "fast":
            # Background mode - don't block the pipeline
            # Don't pass interaction_id because the interaction isn't committed yet
            # and provider_calls has FK constraint. Assessment still works without it.
            logger.info(
                "Scheduling background assessment",
                extra={
                    "service": "voice",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                },
            )
            asyncio.create_task(
                run_assessment_background(
                    manager=manager,
                    websocket=websocket,
                    session_id=session_id,
                    user_id=user_id,
                    user_message=transcript,
                    raw_skill_ids=None,
                    send_status=send_status,
                    model_id=model_id,
                    interaction_id=None,  # skip to avoid FK constraint on uncommitted row
                    client_interaction_id=msg_id,  # pass for client reporting
                )
            )
            return None
        else:
            # Accurate modes - wait for assessment to complete
            if pipeline_mode == "accurate_filler":
                # Send filler audio first to cover the latency
                await _send_filler_audio(
                    manager=manager,
                    websocket=websocket,
                    session_id=session_id,
                    send_status=send_status,
                )

            # Run foreground assessment (blocking)
            logger.info(
                "Starting foreground assessment from voice",
                extra={
                    "service": "voice",
                    "session_id": str(session_id),
                    "user_id": str(user_id),
                },
            )
            # For accurate modes, we also skip interaction_id since the interaction
            # isn't committed yet. The assessment will query for it if needed.
            async with get_session_context() as assessment_db:
                # CRITICAL: Pass interaction_id=None to run_assessment_foreground.
                # If we pass msg_id, the assessment service will try to log provider calls
                # linked to this interaction_id. But the interaction hasn't been committed
                # to the DB yet (it happens later in the pipeline). This causes a FK violation.
                #
                # We will still use msg_id for the frontend WebSocket message so the chip works.
                assessment_result = await run_assessment_foreground(
                    db=assessment_db,
                    session_id=session_id,
                    user_id=user_id,
                    user_message=transcript,
                    raw_skill_ids=None,
                    send_status=send_status,
                    model_id=model_id,
                    # interaction_id=None - interaction not committed yet
                )

                logger.info(
                    "Foreground assessment returned",
                    extra={
                        "service": "voice",
                        "session_id": str(session_id),
                        "user_id": str(user_id),
                        "skipped": assessment_result.skipped,
                        "skip_reason": assessment_result.skip_reason,
                    },
                )

                # Store result in holder for inclusion in chat.complete
                # This is more reliable than sending a separate message
                triage_result_holder["completed"] = True
                triage_result_holder["skipped"] = assessment_result.skipped
                triage_result_holder["reason"] = assessment_result.skip_reason

                if not assessment_result.skipped and assessment_result.assessment_response:
                    resp = assessment_result.assessment_response
                    triage_result_holder["assessmentId"] = (
                        str(resp.assessment_id) if resp.assessment_id else None
                    )
                    triage_result_holder["triageDecision"] = resp.triage_decision
                    # Send assessment.complete for detailed results
                    await manager.send_message(
                        websocket,
                        {
                            "type": "assessment.complete",
                            "payload": {
                                "assessmentId": triage_result_holder["assessmentId"],
                                "sessionId": str(session_id),
                                "interactionId": str(msg_id),
                                "triageDecision": resp.triage_decision,
                                "triageOverrideLabel": resp.triage_override_label,
                                "userResponse": resp.user_response,
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
                                    for s in resp.skills
                                ],
                                "metrics": (resp.metrics.model_dump() if resp.metrics else None),
                            },
                        },
                    )
                    logger.info(
                        "Sent assessment.complete for accurate mode",
                        extra={
                            "service": "voice",
                            "session_id": str(session_id),
                            "interaction_id": str(msg_id),
                            "assessment_id": triage_result_holder["assessmentId"],
                        },
                    )
                elif assessment_result.skipped:
                    # Send assessment.skipped message to client
                    await manager.send_message(
                        websocket,
                        {
                            "type": "assessment.skipped",
                            "payload": {
                                "reason": assessment_result.skip_reason,
                                "interactionId": str(msg_id),
                            },
                        },
                    )
                    logger.info(
                        "Sent assessment.skipped for accurate mode",
                        extra={
                            "service": "voice",
                            "session_id": str(session_id),
                            "interaction_id": str(msg_id),
                            "reason": assessment_result.skip_reason,
                        },
                    )
                    return None
            return None

    # Get effective model ID for this connection
    model_id = manager.get_model_id(websocket)

    logger.info(
        "Voice model selection",
        extra={
            "service": "voice",
            "user_id": str(user_id),
            "session_id": str(session_id),
            "model_id": model_id,
            "model_choice": manager.get_model_choice(websocket),
        },
    )

    try:
        # Process the recording through the full pipeline
        async with get_session_context() as db:
            # Use existing voice service with this db session
            voice_service = await _get_voice_service(user_id)
            # Reset database components to ensure fresh session
            voice_service.db = None
            voice_service._ensure_db_components(db)

            # Transfer recording state to service (in case it's missing)
            voice_service._recordings[user_id] = recording_state

            # Process pipeline (transcript sent during STT, audio chunks during LLM)
            logger.info(
                "handle_voice_end: about to call process_recording",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "pipeline_run_id": str(pipeline_run_id),
                },
            )

            result = await voice_service.process_recording(
                user_id=user_id,
                message_id=message_id,
                pipeline_run_id=pipeline_run_id,
                request_id=request_id_uuid,
                org_id=org_id,
                topology=topology,
                send_status=send_status,
                send_token=send_token,
                send_transcript=send_transcript,
                send_audio_chunk=send_audio_chunk,
                on_interaction_saved=on_interaction_saved,
                model_id=model_id,
                platform=platform,
                behavior=behavior,
            )

            logger.info(
                "handle_voice_end: process_recording completed",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "pipeline_run_id": str(pipeline_run_id),
                    "cancelled": getattr(result, 'cancelled', False),
                },
            )

            # Handle graceful cancellation (e.g., no speech detected)
            if getattr(result, 'cancelled', False):
                logger.info(
                    "Voice pipeline cancelled gracefully - no speech detected",
                    extra={
                        "service": "voice",
                        "user_id": str(user_id),
                        "session_id": str(session_id),
                        "pipeline_run_id": str(pipeline_run_id),
                        "reason": getattr(result, 'cancelled_reason', 'unknown'),
                    },
                )
                # Send voice.complete with cancelled=True so client knows to return to listening
                await manager.send_message(
                    websocket,
                    {
                        "type": "voice.complete",
                        "payload": {
                            "sessionId": str(session_id),
                            "success": True,  # Not an error, just no speech
                            "cancelled": True,
                            "cancelledReason": getattr(result, 'cancelled_reason', 'No speech detected'),
                            "requestId": request_id,
                            "pipelineRunId": str(pipeline_run_id),
                        },
                    },
                )
                # Clean up and return early - don't run normal completion flow
                if user_id in _voice_services:
                    del _voice_services[user_id]
                return

            # Only send final voice.audio if we didn't use incremental mode
            if not incremental_audio_sent and result.audio_data:
                audio_b64 = base64.b64encode(result.audio_data).decode("utf-8")
                await manager.send_message(
                    websocket,
                    {
                        "type": "voice.audio",
                        "payload": {
                            "sessionId": str(session_id),
                            "messageId": str(result.assistant_message_id),
                            "data": audio_b64,
                            "format": result.audio_format,
                            "durationMs": result.tts_duration_ms,
                        },
                    },
                )

            # Send chat.complete with triage result piggybacked
            # This is more reliable than separate triage/assessment messages
            try:
                with open("/tmp/debug_voice_handler.log", "a") as f:
                    f.write(f"[{datetime.now(UTC)}] About to send voice.complete for session {session_id}, message_id: {result.assistant_message_id}\n")
            except Exception:
                pass

            await manager.send_message(
                websocket,
                {
                    "type": "voice.complete",
                    "payload": {
                        "sessionId": str(session_id),
                        "messageId": str(result.assistant_message_id),
                        "interactionId": str(result.assistant_message_id),
                        "success": True,
                        "error": None,
                        # Don't include content here - it's already displayed via chat.token
                        # and audio is streamed via voice.audio.chunk
                        "role": "assistant",
                        "inputType": "voice",
                        "transcript": result.transcript,
                        "requestId": request_id,
                        "pipelineRunId": str(pipeline_run_id),
                        "sttCost": result.stt_cost,
                        "llmCost": result.llm_cost,
                        "ttsCost": result.tts_cost,
                        "latencyMs": result.llm_latency_ms,
                        "triage": {
                            "completed": triage_result_holder["completed"],
                            "skipped": triage_result_holder["skipped"],
                            "reason": triage_result_holder["reason"],
                            "assessmentId": triage_result_holder["assessmentId"],
                            "mode": triage_result_holder["mode"],
                        },
                    },
                },
            )

            try:
                with open("/tmp/debug_voice_handler.log", "a") as f:
                    f.write(f"[{datetime.now(UTC)}] voice.complete sent successfully for session {session_id}, interactionId: {result.assistant_message_id}, success: True\n")
            except Exception:
                pass

            # Check if summary should be generated
            summary_service = SummaryService(db)
            await summary_service.check_and_trigger(session_id, send_status)

        async with get_session_context() as obs_db:
            event_logger = PipelineEventLogger(obs_db)
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.completed",
                request_id=request_id_uuid,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={"assistant_message_id": str(result.assistant_message_id)},
            )

        # Clean up global voice service reference
        if user_id in _voice_services:
            del _voice_services[user_id]

        logger.info(
            "Voice pipeline complete",
            extra={
                "service": "voice",
                "user_id": str(user_id),
                "session_id": str(session_id),
                "transcript_length": len(result.transcript),
                "response_length": len(result.response_text),
                "total_cost": result.total_cost,
            },
        )

    except Exception as e:
        from app.ai.substrate import CircuitBreakerOpenError

        # Check if this is a circuit breaker denial (degraded mode)
        if isinstance(e, CircuitBreakerOpenError):
            # Handle degraded mode errors differently
            if "STT" in str(e):
                # STT degraded - end run and require typed input
                error_message = "Speech recognition is temporarily unavailable. Please use typed input."
                error_code = "STT_DEGRADED"
            elif "TTS" in str(e):
                # TTS degraded - this should be handled gracefully in the stages,
                # but if it bubbles up here, treat it as an error
                error_message = "Text-to-speech is temporarily unavailable. Please try again."
                error_code = "TTS_DEGRADED"
            else:
                # Generic breaker error
                error_message = "Voice service temporarily unavailable. Please try again."
                error_code = "VOICE_DEGRADED"

            error_summary = summarize_pipeline_error(e)
            error_text = error_summary_to_string(error_summary)

            async with get_session_context() as obs_db:
                event_logger = PipelineEventLogger(obs_db)
                await event_logger.create_run(
                    pipeline_run_id=pipeline_run_id,
                    service="voice",
                    request_id=request_id_uuid,
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                )
                await event_logger.emit(
                    pipeline_run_id=pipeline_run_id,
                    type="pipeline.degraded",
                    request_id=request_id_uuid,
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                    data={"error": error_summary, "degraded_service": error_code},
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

            logger.warning(
                "Voice service degraded",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "error": error_text,
                    "error_code": error_code,
                    "request_id": request_id,
                    "pipeline_run_id": str(pipeline_run_id),
                },
                exc_info=True,
            )

            # Clean up on error
            if user_id in _voice_services:
                del _voice_services[user_id]

            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": error_code,
                        "message": error_message,
                        "requestId": request_id,
                        "pipelineRunId": str(pipeline_run_id),
                        "degraded": True,
                    },
                },
            )

            # For STT degraded, also send a status update
            if error_code == "STT_DEGRADED":
                await manager.send_message(
                    websocket,
                    {
                        "type": "status.update",
                        "payload": {
                            "service": "stt",
                            "status": "degraded",
                            "metadata": {"reason": "circuit_breaker_open"},
                        },
                    },
                )
        else:
            # Regular error handling
            error_summary = summarize_pipeline_error(e)
            error_text = error_summary_to_string(error_summary)
            async with get_session_context() as obs_db:
                event_logger = PipelineEventLogger(obs_db)
                await event_logger.create_run(
                    pipeline_run_id=pipeline_run_id,
                    service="voice",
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
                "Voice processing failed",
                extra={
                    "service": "voice",
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "error": error_text,
                    "request_id": request_id,
                    "pipeline_run_id": str(pipeline_run_id),
                },
                exc_info=True,
            )

            # Clean up on error
            if user_id in _voice_services:
                del _voice_services[user_id]

            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "VOICE_ERROR",
                        "message": f"Failed to process voice: {error_text}",
                        "requestId": request_id,
                        "pipelineRunId": str(pipeline_run_id),
                },
            },
        )


@get_router().handler("voice.cancel")
async def handle_voice_cancel(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle voice.cancel - cancel active recording.

    Sends:
    - status.update (mic: cancelled)
    """
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        return

    user_id = conn.user_id

    # Cancel recording and pipeline
    async with get_session_context() as db:
        voice_service = await _get_voice_service(user_id)
        voice_service._ensure_db_components(db)

        # Cancel recording if active
        recording_cancelled = voice_service.cancel_recording(user_id)

        # Cancel pipeline if active (barge-in support)
        pipeline_cancelled = await voice_service.cancel_pipeline(user_id)

    if recording_cancelled or pipeline_cancelled:
        logger.info(
            "Voice recording/pipeline cancelled",
            extra={
                "service": "voice",
                "user_id": str(user_id),
                "recording_cancelled": recording_cancelled,
                "pipeline_cancelled": pipeline_cancelled,
            },
        )

        await manager.send_message(
            websocket,
            {
                "type": "status.update",
                "payload": {
                    "service": "mic",
                    "status": "cancelled",
                    "metadata": {},
                },
            },
        )

    # Clean up global reference
    if user_id in _voice_services:
        del _voice_services[user_id]
