"""Profile WebSocket handlers for user profile get/update."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import WebSocket

from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.database import get_session_context
from app.domains.profile.service import ProfileService
from app.schemas.profile import UserProfileResponse, UserProfileUpdate

logger = logging.getLogger("profile")
router = get_router()


@router.handler("profile.get")
async def handle_profile_get(
    websocket: WebSocket,
    _payload: dict[str, Any] | None,
    manager: ConnectionManager,
) -> None:
    """Return the current user's profile.

    Expected payload: {}

    Sends:
    - profile.data
    """

    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before using profile API",
                },
            },
        )
        return

    user_id = conn.user_id

    start_time = time.time()

    async with get_session_context() as db:
        service = ProfileService(db)
        profile = await service.get_profile_response(user_id)

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "Profile fetched via WebSocket",
        extra={
            "service": "profile",
            "user_id": str(user_id),
            "duration_ms": duration_ms,
        },
    )

    await manager.send_message(
        websocket,
        {
            "type": "profile.data",
            "payload": profile.model_dump(mode="json"),
        },
    )


@router.handler("profile.update")
async def handle_profile_update(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Update the current user's profile (partial update).

    Expected payload fields (all optional):
        name: str
        bio: str
        goal: { title: str, description?: str }
        contexts: { title: str, description?: str }
        notes: str

    Sends on success:
    - profile.data (full profile)
    - profile.updated (ack with updatedAt)
    """

    from pydantic import ValidationError

    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before using profile API",
                },
            },
        )
        return

    user_id = conn.user_id

    # Validate payload (ignore any requestId wrapper if present)
    raw_data = {k: v for k, v in payload.items() if k != "requestId"}

    try:
        update = UserProfileUpdate.model_validate(raw_data)
    except ValidationError as e:  # pragma: no cover - defensive
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": f"Invalid profile payload: {e}",
                },
            },
        )
        return

    start_time = time.time()

    async with get_session_context() as db:
        service = ProfileService(db)
        profile = await service.upsert_profile(user_id, update)

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "Profile updated via WebSocket",
        extra={
            "service": "profile",
            "user_id": str(user_id),
            "fields": list(raw_data.keys()),
            "duration_ms": duration_ms,
        },
    )

    # Convert to response model then dump as JSON-safe dict
    profile_response = UserProfileResponse.model_validate(profile)
    profile_dict = profile_response.model_dump(mode="json")

    # Send updated profile data
    await manager.send_message(
        websocket,
        {
            "type": "profile.data",
            "payload": profile_dict,
        },
    )

    # Send lightweight updated event for observability/UI cues
    await manager.send_message(
        websocket,
        {
            "type": "profile.updated",
            "payload": {
                "success": True,
                "updatedAt": profile.updated_at.isoformat() + "Z",
            },
        },
    )
