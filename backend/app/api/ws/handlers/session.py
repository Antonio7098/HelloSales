"""Session management WebSocket handlers."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select

from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.database import get_session_context
from app.domains.chat.service import SUMMARY_THRESHOLD
from app.models import Interaction, ProviderCall, Session, SessionSummary, SummaryState
from app.services.session_state import SessionStateService

logger = logging.getLogger("session")
router = get_router()


@router.handler("session.list")
async def handle_session_list(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """List user's sessions.

    Expected payload: {} (empty)

    Responds with:
    - session.list: { sessions: [{ id, messageCount, createdAt, lastMessageAt }] }
    """
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

    user_id = conn.user_id

    async with get_session_context() as db:
        # Get all sessions for user, ordered by most recent first
        result = await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.created_at.desc())
            .limit(20)  # Limit to recent sessions
        )
        sessions = result.scalars().all()

        # Get last message timestamp for each session
        session_data = []
        for session in sessions:
            # Get last interaction
            last_interaction_result = await db.execute(
                select(Interaction)
                .where(Interaction.session_id == session.id)
                .order_by(Interaction.created_at.desc())
                .limit(1)
            )
            last_interaction = last_interaction_result.scalar_one_or_none()

            # Get first user message as preview
            first_msg_result = await db.execute(
                select(Interaction)
                .where(Interaction.session_id == session.id)
                .where(Interaction.role == "user")
                .order_by(Interaction.created_at)
                .limit(1)
            )
            first_msg = first_msg_result.scalar_one_or_none()

            session_data.append(
                {
                    "id": str(session.id),
                    "messageCount": session.interaction_count,
                    "createdAt": session.created_at.isoformat(),
                    "lastMessageAt": (
                        last_interaction.created_at.isoformat() if last_interaction else None
                    ),
                    "title": session.title,
                    "preview": (
                        (first_msg.content[:50] + "...")
                        if first_msg and len(first_msg.content) > 50
                        else (first_msg.content if first_msg else "New conversation")
                    ),
                    "state": session.state,
                    "isOnboarding": session.is_onboarding,
                    # For sorting - use last message time or creation time
                    "_sortKey": (
                        last_interaction.created_at if last_interaction else session.created_at
                    ),
                }
            )

        # Sort by most recently used (last message time)
        session_data.sort(key=lambda s: s["_sortKey"], reverse=True)

        # Remove sort key before sending
        for s in session_data:
            del s["_sortKey"]

    logger.info(
        "Sessions listed",
        extra={
            "service": "session",
            "user_id": str(user_id),
            "count": len(session_data),
        },
    )

    await manager.send_message(
        websocket,
        {
            "type": "session.list",
            "payload": {
                "sessions": session_data,
            },
        },
    )


@router.handler("session.rename")
async def handle_session_rename(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Rename a session (set its title).

    Expected payload:
        { "sessionId": "uuid", "title": "string | null" }

    Responds with:
    - session.renamed: { sessionId, title }
    - error if session not found, unauthorized, or invalid payload
    """

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

    user_id = conn.user_id
    session_id_str = payload.get("sessionId")
    title_raw = payload.get("title")

    if not session_id_str:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "sessionId is required",
                },
            },
        )
        return

    try:
        session_id = UUID(session_id_str)
    except ValueError:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Invalid sessionId format",
                },
            },
        )
        return

    title: str | None
    if title_raw is None:
        title = None
    elif isinstance(title_raw, str):
        title = title_raw.strip()
        if title == "":
            title = None
        elif len(title) > 255:
            title = title[:255]
    else:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "title must be a string or null",
                },
            },
        )
        return

    async with get_session_context() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id).where(Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SESSION_NOT_FOUND",
                        "message": "Session not found or unauthorized",
                    },
                },
            )
            return

        session.title = title
        await db.commit()

    await manager.send_message(
        websocket,
        {
            "type": "session.renamed",
            "payload": {
                "sessionId": str(session_id),
                "title": title,
            },
        },
    )


@router.handler("session.switch")
async def handle_session_switch(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Switch to an existing session.

    Expected payload:
        { "sessionId": "uuid" }

    Responds with:
    - session.switched: { sessionId, messages: [...] }
    - error if session not found or unauthorized
    """
    logger.info(
        "Session switch request received",
        extra={
            "service": "session",
            "payload": payload,
        }
    )

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

    user_id = conn.user_id
    previous_session_id = conn.session_id
    session_id_str = payload.get("sessionId")

    if not session_id_str:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "sessionId is required",
                },
            },
        )
        return

    try:
        session_id = UUID(session_id_str)
    except ValueError:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Invalid sessionId format",
                },
            },
        )
        return

    async with get_session_context() as db:
        # Verify session belongs to user
        result = await db.execute(
            select(Session).where(Session.id == session_id).where(Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SESSION_NOT_FOUND",
                        "message": "Session not found or unauthorized",
                    },
                },
            )
            return

        async def _run_meta_catch_up() -> None:
            try:
                async with get_session_context() as meta_db:
                    result = await MetaSummaryService(meta_db).merge_latest_unprocessed_summaries(
                        user_id=user_id,
                        max_sessions=1,
                    )

                if result is None:
                    logger.info(
                        "Meta summary catch-up no-op during session.switch",
                        extra={
                            "service": "session",
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
                            "trigger": "meta_summary.catch_up.session.switch",
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
                        "Meta summary catch-up emitted to 0 connections during session.switch",
                        extra={
                            "service": "session",
                            "user_id": str(user_id),
                        },
                    )
            except Exception as exc:
                logger.warning(
                    "Meta summary catch-up failed during session.switch",
                    extra={
                        "service": "session",
                        "user_id": str(user_id),
                        "previous_session_id": str(previous_session_id)
                        if previous_session_id
                        else None,
                        "error": str(exc),
                    },
                )

        asyncio.create_task(_run_meta_catch_up())

        is_onboarding = session.is_onboarding

        # Get messages with pagination (default to latest 20 interactions ~ 40 messages)
        # We query by DESC created_at to get the latest ones, then reverse them in Python
        limit = payload.get("limit", 40)

        # Query one extra to check if there are more
        messages_result = await db.execute(
            select(Interaction)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.created_at.desc())
            .limit(limit + 1)  # Get one extra to check for hasMore
        )
        interactions = list(messages_result.scalars().all())

        has_more = len(interactions) > limit
        if has_more:
            interactions = interactions[:limit]

        interactions.reverse()  # Chronological order

        interaction_ids = [i.id for i in interactions]

        # Batch query: get latest triage log per interaction (single query)
        triage_by_interaction: dict[UUID, TriageLog] = {}
        if interaction_ids:
            triage_result = await db.execute(
                select(TriageLog)
                .where(TriageLog.interaction_id.in_(interaction_ids))
                .order_by(TriageLog.created_at.desc())
            )
            for tlog in triage_result.scalars().all():
                # Keep only the latest triage per interaction
                if tlog.interaction_id and tlog.interaction_id not in triage_by_interaction:
                    triage_by_interaction[tlog.interaction_id] = tlog

        # Batch query: get assessments per interaction (single query)
        assessment_by_interaction: dict[UUID, Assessment] = {}
        if interaction_ids:
            assessment_result = await db.execute(
                select(Assessment)
                .where(
                    Assessment.interaction_id.in_(interaction_ids),
                    Assessment.deleted_at.is_(None),
                )
                .order_by(Assessment.created_at.desc())
            )
            for assess in assessment_result.scalars().all():
                if assess.interaction_id and assess.interaction_id not in assessment_by_interaction:
                    assessment_by_interaction[assess.interaction_id] = assess

        # Batch fetch provider_calls referenced by interactions via FK to avoid N+1.
        stt_call_ids = [i.stt_provider_call_id for i in interactions if i.stt_provider_call_id]
        llm_call_ids = [i.llm_provider_call_id for i in interactions if i.llm_provider_call_id]
        tts_call_ids = [i.tts_provider_call_id for i in interactions if i.tts_provider_call_id]
        all_call_ids = {*(stt_call_ids or []), *(llm_call_ids or []), *(tts_call_ids or [])}

        calls_by_id: dict[UUID, ProviderCall] = {}
        if all_call_ids:
            calls_result = await db.execute(
                select(ProviderCall).where(ProviderCall.id.in_(all_call_ids))
            )
            for call in calls_result.scalars().all():
                calls_by_id[call.id] = call

        def _get_call(call_id: UUID | None) -> ProviderCall | None:
            if not call_id:
                return None
            return calls_by_id.get(call_id)

        messages = []
        total_cost_cents = 0
        total_latency_ms = 0
        assistant_count = 0

        for i in interactions:
            triage = triage_by_interaction.get(i.id)
            assessment = assessment_by_interaction.get(i.id)

            stt_call = _get_call(i.stt_provider_call_id)
            llm_call = _get_call(i.llm_provider_call_id)
            tts_call = _get_call(i.tts_provider_call_id)

            # Per-message metrics
            latency_ms: int | None = None
            tokens_in: int | None = None
            tokens_out: int | None = None
            message_cost_cents = 0

            if llm_call is not None:
                latency_ms = llm_call.latency_ms
                tokens_in = llm_call.tokens_in
                tokens_out = llm_call.tokens_out
                if llm_call.cost_cents is not None:
                    message_cost_cents += llm_call.cost_cents

            if stt_call is not None and stt_call.cost_cents is not None:
                message_cost_cents += stt_call.cost_cents

            if tts_call is not None and tts_call.cost_cents is not None:
                message_cost_cents += tts_call.cost_cents

            if i.role == "assistant" and latency_ms is not None:
                total_latency_ms += latency_ms
                assistant_count += 1

            total_cost_cents += message_cost_cents

            messages.append(
                {
                    "id": str(i.id),
                    "role": i.role,
                    "content": i.content,
                    "timestamp": i.created_at.isoformat(),
                    "latencyMs": latency_ms,
                    "tokensIn": tokens_in,
                    "tokensOut": tokens_out,
                    "costCents": message_cost_cents,
                    # Triage info (for "Not assessed" chips)
                    "triageDecision": triage.decision if triage else None,
                    "triageReason": triage.reason if triage else None,
                    # Assessment info (for "scored" chips - just the ID, full data via assessment.history)
                    "assessmentId": str(assessment.id) if assessment else None,
                }
            )

        # Calculate session totals
        avg_latency_ms = total_latency_ms // assistant_count if assistant_count > 0 else 0

        # Get summary state
        summary_result = await db.execute(
            select(SummaryState).where(SummaryState.session_id == session_id)
        )
        summary_state = summary_result.scalar_one_or_none()

        turns_since = summary_state.turns_since if summary_state else 0

        # Get latest summary for this session
        latest_summary_result = await db.execute(
            select(SessionSummary)
            .where(SessionSummary.session_id == session_id)
            .order_by(SessionSummary.version.desc())
            .limit(1)
        )
        latest_summary = latest_summary_result.scalar_one_or_none()
        summary_text = latest_summary.text if latest_summary else None

    # Update connection to use this session
    manager.authenticate(websocket, user_id, session_id)

    logger.info(
        "Session switched",
        extra={
            "service": "session",
            "user_id": str(user_id),
            "session_id": str(session_id),
            "message_count": len(messages),
            "has_summary": summary_text is not None,
        },
    )

    await manager.send_message(
        websocket,
        {
            "type": "session.switched",
            "payload": {
                "sessionId": str(session_id),
                "title": session.title,
                "isOnboarding": bool(is_onboarding),
                "messages": messages,
                "hasMore": has_more,  # Add hasMore flag
                "summaryText": summary_text,
                "metrics": {
                    "totalCostCents": total_cost_cents,
                    "avgLatencyMs": avg_latency_ms,
                    "messageCount": len(messages),
                },
            },
        },
    )

    # Send current summary cadence
    await manager.send_message(
        websocket,
        {
            "type": "status.update",
            "payload": {
                "service": "summary",
                "status": "idle",
                "metadata": {
                    "turns_since": turns_since,
                    "turns_until_summary": max(0, SUMMARY_THRESHOLD - turns_since),
                    "threshold": SUMMARY_THRESHOLD,
                },
            },
        },
    )


@router.handler("session.history")
async def handle_session_history(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Fetch older messages (pagination history).

    Expected payload:
        { "sessionId": "uuid", "beforeMessageId": "uuid", "limit": 20 }

    Responds with:
    - session.history: { sessionId, messages: [...], hasMore: bool }
    """
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        logger.warning("Session history request: not authenticated", extra={"service": "session"})
        return  # Silently fail or send error

    user_id = conn.user_id
    session_id_str = payload.get("sessionId")
    before_message_id_str = payload.get("beforeMessageId")
    limit = payload.get("limit", 20)

    logger.info(
        "Session history request",
        extra={
            "service": "session",
            "user_id": str(user_id),
            "session_id": session_id_str,
            "before_message_id": before_message_id_str,
            "limit": limit,
        }
    )

    if not session_id_str:
        logger.warning("Session history request: missing sessionId", extra={"service": "session"})
        return

    try:
        session_id = UUID(session_id_str)
        before_message_id = UUID(before_message_id_str) if before_message_id_str else None
    except ValueError as e:
        logger.warning(
            "Session history request: invalid UUID",
            extra={"service": "session", "error": str(e), "session_id": session_id_str, "before_message_id": before_message_id_str}
        )
        return

    async with get_session_context() as db:
        # Verify session
        result = await db.execute(
            select(Session).where(Session.id == session_id).where(Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            logger.warning(
                "Session history request: session not found",
                extra={"service": "session", "session_id": str(session_id), "user_id": str(user_id)}
            )
            return

        # Build query
        query = select(Interaction).where(Interaction.session_id == session_id)

        if before_message_id:
            # Find the timestamp of the message to paginate before
            before_msg = await db.execute(
                select(Interaction).where(Interaction.id == before_message_id)
            )
            before_msg_obj = before_msg.scalar_one_or_none()
            if before_msg_obj:
                query = query.where(Interaction.created_at < before_msg_obj.created_at)

        # Get one more than limit to check if there are more
        query = query.order_by(Interaction.created_at.desc()).limit(limit + 1)

        result = await db.execute(query)
        interactions = list(result.scalars().all())

        logger.info(
            "Session history query results",
            extra={
                "service": "session",
                "session_id": str(session_id),
                "found_interactions": len(interactions),
                "has_more": len(interactions) > limit,
            }
        )

        has_more = len(interactions) > limit
        if has_more:
            interactions = interactions[:limit]

        interactions.reverse() # Chronological

        # Hydrate with related data (same as session.switch)
        interaction_ids = [i.id for i in interactions]

        # Triage logs
        triage_by_interaction = {}
        if interaction_ids:
            triage_result = await db.execute(
                select(TriageLog)
                .where(TriageLog.interaction_id.in_(interaction_ids))
                .order_by(TriageLog.created_at.desc())
            )
            for tlog in triage_result.scalars().all():
                if tlog.interaction_id and tlog.interaction_id not in triage_by_interaction:
                    triage_by_interaction[tlog.interaction_id] = tlog

        # Assessments
        assessment_by_interaction = {}
        if interaction_ids:
            assessment_result = await db.execute(
                select(Assessment)
                .where(
                    Assessment.interaction_id.in_(interaction_ids),
                    Assessment.deleted_at.is_(None),
                )
                .order_by(Assessment.created_at.desc())
            )
            for assess in assessment_result.scalars().all():
                if assess.interaction_id and assess.interaction_id not in assessment_by_interaction:
                    assessment_by_interaction[assess.interaction_id] = assess

        # Provider calls (optional for history, but good for consistency)
        stt_call_ids = [i.stt_provider_call_id for i in interactions if i.stt_provider_call_id]
        llm_call_ids = [i.llm_provider_call_id for i in interactions if i.llm_provider_call_id]
        tts_call_ids = [i.tts_provider_call_id for i in interactions if i.tts_provider_call_id]
        all_call_ids = {*(stt_call_ids or []), *(llm_call_ids or []), *(tts_call_ids or [])}

        calls_by_id = {}
        if all_call_ids:
            calls_result = await db.execute(
                select(ProviderCall).where(ProviderCall.id.in_(all_call_ids))
            )
            for call in calls_result.scalars().all():
                calls_by_id[call.id] = call

        def _get_call(call_id):
            return calls_by_id.get(call_id) if call_id else None

        messages = []
        for i in interactions:
            triage = triage_by_interaction.get(i.id)
            assessment = assessment_by_interaction.get(i.id)

            stt_call = _get_call(i.stt_provider_call_id)
            llm_call = _get_call(i.llm_provider_call_id)
            tts_call = _get_call(i.tts_provider_call_id)

            latency_ms = llm_call.latency_ms if llm_call else None
            tokens_in = llm_call.tokens_in if llm_call else None
            tokens_out = llm_call.tokens_out if llm_call else None

            # Simple cost calc (approx)
            message_cost_cents = 0
            if llm_call and llm_call.cost_cents:
                message_cost_cents += llm_call.cost_cents
            if stt_call and stt_call.cost_cents:
                message_cost_cents += stt_call.cost_cents
            if tts_call and tts_call.cost_cents:
                message_cost_cents += tts_call.cost_cents

            messages.append(
                {
                    "id": str(i.id),
                    "role": i.role,
                    "content": i.content,
                    "timestamp": i.created_at.isoformat(),
                    "latencyMs": latency_ms,
                    "tokensIn": tokens_in,
                    "tokensOut": tokens_out,
                    "costCents": message_cost_cents,
                    "triageDecision": triage.decision if triage else None,
                    "triageReason": triage.reason if triage else None,
                    "assessmentId": str(assessment.id) if assessment else None,
                }
            )

        await manager.send_message(
            websocket,
            {
                "type": "session.history",
                "payload": {
                    "sessionId": str(session_id),
                    "messages": messages,
                    "hasMore": has_more,
                }
            }
        )

        logger.info(
            "Session history response sent",
            extra={
                "service": "session",
                "session_id": str(session_id),
                "message_count": len(messages),
                "has_more": has_more,
            }
        )


@router.handler("session.create")
async def handle_session_create(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Create a new session.

    Expected payload: {} (empty)

    Responds with:
    - session.created: { sessionId }
    """
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

    user_id = conn.user_id
    previous_session_id = conn.session_id

    async with get_session_context() as db:
        # Create new session
        session = Session(user_id=user_id)
        db.add(session)
        await db.flush()

        # Create summary state
        summary_state = SummaryState(session_id=session.id)
        db.add(summary_state)

        await db.commit()
        await db.refresh(session)

        session_id = session.id

    # Update connection to use new session
    manager.authenticate(websocket, user_id, session_id)

    async def _run_meta_catch_up() -> None:
        try:
            async with get_session_context() as meta_db:
                result = await MetaSummaryService(meta_db).merge_latest_unprocessed_summaries(
                    user_id=user_id,
                    max_sessions=1,
                )

            if result is None:
                logger.info(
                    "Meta summary catch-up no-op during session.create",
                    extra={
                        "service": "session",
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
                        "trigger": "meta_summary.catch_up.session.create",
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
                    "Meta summary catch-up emitted to 0 connections during session.create",
                    extra={
                        "service": "session",
                        "user_id": str(user_id),
                    },
                )
        except Exception as exc:
            logger.warning(
                "Meta summary catch-up failed during session.create",
                extra={
                    "service": "session",
                    "user_id": str(user_id),
                    "previous_session_id": str(previous_session_id)
                    if previous_session_id
                    else None,
                    "error": str(exc),
                },
            )

    asyncio.create_task(_run_meta_catch_up())

    logger.info(
        "New session created",
        extra={
            "service": "session",
            "user_id": str(user_id),
            "session_id": str(session_id),
        },
    )

    await manager.send_message(
        websocket,
        {
            "type": "session.created",
            "payload": {
                "sessionId": str(session_id),
                "isOnboarding": bool(session.is_onboarding),
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


@router.handler("session.onboarding")
async def handle_session_onboarding_create(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Create a new onboarding session.

    Expected payload:
        { "platform": "web" | "native" }  # optional, defaults to "native"

    Responds with:
    - session.created: { sessionId }
    """
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

    user_id = conn.user_id
    previous_session_id = conn.session_id

    async with get_session_context() as db:
        # Create new onboarding session
        session = Session(user_id=user_id, is_onboarding=True)
        db.add(session)
        await db.flush()

        # Create summary state
        summary_state = SummaryState(session_id=session.id)
        db.add(summary_state)

        await db.commit()
        await db.refresh(session)

        session_id = session.id

    # Update connection to use new session
    manager.authenticate(websocket, user_id, session_id)

    async def _run_meta_catch_up() -> None:
        try:
            async with get_session_context() as meta_db:
                result = await MetaSummaryService(meta_db).merge_latest_unprocessed_summaries(
                    user_id=user_id,
                    max_sessions=1,
                )

            if result is None:
                logger.info(
                    "Meta summary catch-up no-op during session.onboarding",
                    extra={
                        "service": "session",
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
                        "trigger": "meta_summary.catch_up.session.onboarding",
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
                    "Meta summary catch-up emitted to 0 connections during session.onboarding",
                    extra={
                        "service": "session",
                        "user_id": str(user_id),
                    },
                )
        except Exception as exc:
            logger.warning(
                "Meta summary catch-up failed during session.onboarding",
                extra={
                    "service": "session",
                    "user_id": str(user_id),
                    "previous_session_id": str(previous_session_id)
                    if previous_session_id
                    else None,
                    "error": str(exc),
                },
            )

    asyncio.create_task(_run_meta_catch_up())

    logger.info(
        "New onboarding session created",
        extra={
            "service": "session",
            "user_id": str(user_id),
            "session_id": str(session_id),
        },
    )

    await manager.send_message(
        websocket,
        {
            "type": "session.created",
            "payload": {
                "sessionId": str(session_id),
                "isOnboarding": bool(session.is_onboarding),
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


@router.handler("session.state.get")
async def handle_session_state_get(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Get session state for a session.

    Expected payload:
        { "sessionId": "uuid" }

    Responds with:
    - session.state: { sessionId, topology, behavior, config, updatedAt, kernel, channel, isOnboarding }
    - error if session not found or unauthorized
    """
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

    user_id = conn.user_id
    session_id_str = payload.get("sessionId")

    if not session_id_str:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "sessionId is required",
                },
            },
        )
        return

    try:
        session_id = UUID(session_id_str)
    except ValueError:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Invalid sessionId format",
                },
            },
        )
        return

    async with get_session_context() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id).where(Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SESSION_NOT_FOUND",
                        "message": "Session not found or unauthorized",
                    },
                },
            )
            return

        service = SessionStateService(session=db)
        try:
            state = await service.get_or_create(session_id)
        except Exception as e:
            logger.error(
                "Failed to get session state",
                extra={
                    "service": "session",
                    "session_id": str(session_id),
                    "error": str(e),
                },
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SESSION_STATE_ERROR",
                        "message": f"Failed to get session state: {str(e)}",
                    },
                },
            )
            return

        logger.info(
            "Session state retrieved",
            extra={
                "service": "session",
                "session_id": str(session_id),
                "topology": state.topology,
                "behavior": state.behavior,
            },
        )

        await manager.send_message(
            websocket,
            {
                "type": "session.state",
                "payload": {
                    "sessionId": str(session_id),
                    "topology": state.topology,
                    "behavior": state.behavior,
                    "config": state.config,
                    "updatedAt": state.updated_at.isoformat(),
                    "kernel": state.kernel,
                    "channel": state.channel,
                    "isOnboarding": state.is_onboarding,
                },
            },
        )


@router.handler("session.state.update")
async def handle_session_state_update(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Update session state for a session.

    Expected payload:
        {
            "sessionId": "uuid",
            "topology": "voice_fast" | "chat_fast" | ... (optional),
            "behavior": "practice" | "onboarding" | ... (optional),
            "config": {...} (optional, merged with existing)
        }

    Responds with:
    - session.state.updated: { sessionId, topology, behavior, config, updatedAt, kernel, channel, isOnboarding }
    - error if session not found, unauthorized, or invalid values
    """
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

    user_id = conn.user_id
    session_id_str = payload.get("sessionId")

    if not session_id_str:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "sessionId is required",
                },
            },
        )
        return

    try:
        session_id = UUID(session_id_str)
    except ValueError:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Invalid sessionId format",
                },
            },
        )
        return

    topology = payload.get("topology")
    behavior = payload.get("behavior")
    config = payload.get("config")

    if topology is not None and not isinstance(topology, str):
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "topology must be a string",
                },
            },
        )
        return

    if behavior is not None and not isinstance(behavior, str):
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "behavior must be a string",
                },
            },
        )
        return

    if config is not None and not isinstance(config, dict):
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "config must be a dictionary",
                },
            },
        )
        return

    async with get_session_context() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id).where(Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SESSION_NOT_FOUND",
                        "message": "Session not found or unauthorized",
                    },
                },
            )
            return

        service = SessionStateService(session=db)
        try:
            state = await service.update(
                session_id,
                topology=topology,
                behavior=behavior,
                config=config,
            )
        except Exception as e:
            logger.error(
                "Failed to update session state",
                extra={
                    "service": "session",
                    "session_id": str(session_id),
                    "error": str(e),
                },
            )
            error_code = "INVALID_SESSION_STATE"
            if "not supported" in str(e).lower():
                error_code = "TOPOLOGY_NOT_SUPPORTED"
            elif "not allowed" in str(e).lower():
                error_code = "BEHAVIOR_NOT_ALLOWED"
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": error_code,
                        "message": str(e),
                    },
                },
            )
            return

        logger.info(
            "Session state updated",
            extra={
                "service": "session",
                "session_id": str(session_id),
                "topology": state.topology,
                "behavior": state.behavior,
                "changes": {
                    "topology": topology is not None,
                    "behavior": behavior is not None,
                    "config": config is not None,
                },
            },
        )

        await manager.send_message(
            websocket,
            {
                "type": "session.state.updated",
                "payload": {
                    "sessionId": str(session_id),
                    "topology": state.topology,
                    "behavior": state.behavior,
                    "config": state.config,
                    "updatedAt": state.updated_at.isoformat(),
                    "kernel": state.kernel,
                    "channel": state.channel,
                    "isOnboarding": state.is_onboarding,
                },
            },
        )

        await manager.send_to_user(
            user_id,
            {
                "type": "session.state.changed",
                "payload": {
                    "sessionId": str(session_id),
                    "topology": state.topology,
                    "behavior": state.behavior,
                    "isOnboarding": state.is_onboarding,
                },
            },
        )
