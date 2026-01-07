"""WebSocket handlers for feedback (flags and reports)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket
from pydantic import ValidationError

from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.database import get_session_context
from app.domains.feedback.service import FeedbackService
from app.schemas.feedback import FeedbackMessageFlagCreate, FeedbackReportCreate

logger = logging.getLogger("feedback.ws")
router = get_router()


async def _send_error(
    websocket: WebSocket,
    manager: ConnectionManager,
    code: str,
    message: str,
    request_id: str | None,
) -> None:
    await manager.send_message(
        websocket,
        {
            "type": "error",
            "payload": {
                "code": code,
                "message": message,
                "requestId": request_id,
            },
        },
    )


@router.handler("feedback.message_flag")
async def handle_feedback_message_flag(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle per-message feedback flags from chat/voice transcripts.

    Expected payload fields:
        sessionId?: string (UUID)  # falls back to connection.session_id when absent
        interactionId: string (UUID)
        role: "assistant" | "user"
        category: "bad_assistant" | "bug" | "improvement" | "like" | "triage_incorrect"
        name: string
        shortReason?: string
        timeBucket?: "just_now" | "earlier_today" | "earlier_this_week"
        requestId?: string
    """

    conn = manager.get_connection(websocket)
    request_id = payload.get("requestId")

    if not conn or not conn.authenticated or not conn.user_id:
        await _send_error(
            websocket,
            manager,
            "NOT_AUTHENTICATED",
            "Must authenticate before sending feedback",
            request_id,
        )
        return

    # Build data dict for Pydantic validation, ignoring requestId wrapper
    raw_data: dict[str, Any] = {k: v for k, v in payload.items() if k != "requestId"}

    # If sessionId missing and connection has an attached session, fall back to it.
    # Otherwise, allow session_id to be null (feedback can still be useful without
    # a concrete session context, e.g. generic assistant behaviour flags).
    if "sessionId" not in raw_data and conn.session_id is not None:
        raw_data["sessionId"] = str(conn.session_id)

    # Normalise keys to snake_case expected by schemas
    normalised: dict[str, Any] = {}
    key_map = {
        "sessionId": "session_id",
        "interactionId": "interaction_id",
        "shortReason": "short_reason",
        "timeBucket": "time_bucket",
    }
    for key, value in raw_data.items():
        normalised[key_map.get(key, key)] = value

    try:
        create = FeedbackMessageFlagCreate.model_validate(normalised)
    except ValidationError as e:  # pragma: no cover - defensive
        await _send_error(
            websocket,
            manager,
            "INVALID_PAYLOAD",
            f"Invalid feedback.message_flag payload: {e}",
            request_id,
        )
        return

    async with get_session_context() as db:
        service = FeedbackService(db)
        event = await service.create_message_flag(user_id=conn.user_id, data=create)

    await manager.send_message(
        websocket,
        {
            "type": "feedback.ack",
            "payload": {
                "success": True,
                "feedbackId": str(event.id),
                "requestId": request_id,
            },
        },
    )


@router.handler("feedback.report")
async def handle_feedback_report(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle high-level feedback reports from Reporting tab.

    Expected payload fields:
        category: "bug" | "improvement" | "like" | "bad_assistant"
        name: string
        description?: string
        scope?: "chat" | "voice" | "app"
        timeBucket: "just_now" | "earlier_today" | "earlier_this_week"
        sessionId?: string (UUID)
        interactionId?: string (UUID)
        requestId?: string
    """

    conn = manager.get_connection(websocket)
    request_id = payload.get("requestId")

    if not conn or not conn.authenticated or not conn.user_id:
        await _send_error(
            websocket,
            manager,
            "NOT_AUTHENTICATED",
            "Must authenticate before sending feedback",
            request_id,
        )
        return

    raw_data: dict[str, Any] = {k: v for k, v in payload.items() if k != "requestId"}

    # Optional: if sessionId missing but connection has one, use it as a default
    if "sessionId" not in raw_data and conn.session_id is not None:
        raw_data["sessionId"] = str(conn.session_id)

    # Normalise keys to snake_case expected by schemas
    normalised: dict[str, Any] = {}
    key_map = {
        "sessionId": "session_id",
        "interactionId": "interaction_id",
        "timeBucket": "time_bucket",
    }
    for key, value in raw_data.items():
        normalised[key_map.get(key, key)] = value

    try:
        create = FeedbackReportCreate.model_validate(normalised)
    except ValidationError as e:  # pragma: no cover - defensive
        await _send_error(
            websocket,
            manager,
            "INVALID_PAYLOAD",
            f"Invalid feedback.report payload: {e}",
            request_id,
        )
        return

    async with get_session_context() as db:
        service = FeedbackService(db)
        event = await service.create_report(user_id=conn.user_id, data=create)

    await manager.send_message(
        websocket,
        {
            "type": "feedback.ack",
            "payload": {
                "success": True,
                "feedbackId": str(event.id),
                "requestId": request_id,
            },
        },
    )
