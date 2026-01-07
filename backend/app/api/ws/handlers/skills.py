"""Skills WebSocket handlers for skills catalog and tracking."""

import logging
import uuid
from typing import Any

from fastapi import WebSocket

from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.config import get_settings
from app.database import get_session_context
from app.domains.skills.service import (
    MaxTrackedSkillsError,
    SkillNotFoundError,
    SkillService,
    UntrackingDisabledError,
)

logger = logging.getLogger("skills")
router = get_router()


def _get_authenticated_user(manager: ConnectionManager, websocket: WebSocket) -> uuid.UUID | None:
    """Helper to fetch authenticated user_id or send NOT_AUTHENTICATED error."""

    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        # Send error synchronously; caller should return afterwards
        # Note: we can't await here, so this is only used by handlers that await explicitly
        return None
    return conn.user_id


async def _ensure_authenticated(
    websocket: WebSocket,
    manager: ConnectionManager,
) -> uuid.UUID | None:
    """Ensure the connection is authenticated; send error if not."""

    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before using skills API",
                },
            },
        )
        return None
    return conn.user_id


@router.handler("skills.list")
async def handle_skills_list(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """List all active skills with user's tracking status."""

    user_id = await _ensure_authenticated(websocket, manager)
    if not user_id:
        return

    settings = get_settings()

    async with get_session_context() as db:
        service = SkillService(db)
        skills = await service.list_skills(user_id)

    logger.info(
        "Skills catalog listed",
        extra={"service": "skills", "user_id": str(user_id), "count": len(skills)},
    )

    await manager.send_message(
        websocket,
        {
            "type": "skills.catalog",
            "payload": {
                "skills": [s.model_dump(mode="json") for s in skills],
                "betaModeEnabled": settings.beta_mode_enabled,
            },
        },
    )


@router.handler("skills.tracked")
async def handle_skills_tracked(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """List user's currently tracked skills."""

    user_id = await _ensure_authenticated(websocket, manager)
    if not user_id:
        return

    async with get_session_context() as db:
        service = SkillService(db)
        tracked = await service.get_tracked_skills(user_id)

    logger.debug(
        "Tracked skills fetched",
        extra={"service": "skills", "user_id": str(user_id), "count": len(tracked)},
    )

    await manager.send_message(
        websocket,
        {
            "type": "skills.tracked.list",
            "payload": {
                "skills": [t.model_dump(mode="json") for t in tracked],
            },
        },
    )


@router.handler("skills.track")
async def handle_skills_track(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Track a skill for the current user."""

    user_id = await _ensure_authenticated(websocket, manager)
    if not user_id:
        return

    request_id = payload.get("requestId")
    skill_id_str = payload.get("skillId")

    if not skill_id_str:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "skillId is required",
                    "requestId": request_id,
                },
            },
        )
        return

    try:
        skill_id = uuid.UUID(skill_id_str)
    except ValueError as e:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": f"Invalid skillId UUID format: {e}",
                    "requestId": request_id,
                },
            },
        )
        return

    async with get_session_context() as db:
        service = SkillService(db)
        try:
            tracked = await service.track_skill(user_id, skill_id)
        except MaxTrackedSkillsError as e:
            await manager.send_message(
                websocket,
                {
                    "type": "skills.track.error",
                    "payload": {
                        "code": "MAX_TRACKED_REACHED",
                        "message": str(e),
                        "requestId": request_id,
                    },
                },
            )
            return
        except SkillNotFoundError as e:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SKILL_NOT_FOUND",
                        "message": str(e),
                        "requestId": request_id,
                    },
                },
            )
            return
        except Exception as e:  # Fallback
            logger.error(
                "Skill track failed",
                extra={
                    "service": "skills",
                    "user_id": str(user_id),
                    "skill_id": str(skill_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SKILLS_ERROR",
                        "message": "Failed to track skill",
                        "requestId": request_id,
                    },
                },
            )
            return

    # Success response
    await manager.send_message(
        websocket,
        {
            "type": "skills.track.success",
            "payload": {
                "skill": {
                    "id": str(tracked.id),
                    "slug": tracked.slug,
                    "title": tracked.title,
                    "currentLevel": tracked.current_level,
                },
                "trackOrder": tracked.track_order,
            },
        },
    )

    # Status event for observability
    await manager.send_message(
        websocket,
        {
            "type": "status.update",
            "payload": {
                "service": "skills",
                "status": "complete",
                "metadata": {
                    "operation": "track",
                    "skillId": str(tracked.id),
                    "trackOrder": tracked.track_order,
                },
            },
        },
    )


@router.handler("skills.untrack")
async def handle_skills_untrack(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Untrack a skill for the current user."""

    user_id = await _ensure_authenticated(websocket, manager)
    if not user_id:
        return

    request_id = payload.get("requestId")
    skill_id_str = payload.get("skillId")

    if not skill_id_str:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "skillId is required",
                    "requestId": request_id,
                },
            },
        )
        return

    try:
        skill_id = uuid.UUID(skill_id_str)
    except ValueError as e:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": f"Invalid skillId UUID format: {e}",
                    "requestId": request_id,
                },
            },
        )
        return

    async with get_session_context() as db:
        service = SkillService(db)
        try:
            await service.untrack_skill(user_id, skill_id)
        except UntrackingDisabledError as e:
            await manager.send_message(
                websocket,
                {
                    "type": "skills.untrack.error",
                    "payload": {
                        "code": "UNTRACKING_DISABLED",
                        "message": str(e),
                        "requestId": request_id,
                    },
                },
            )
            return
        except SkillNotFoundError as e:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SKILL_NOT_FOUND",
                        "message": str(e),
                        "requestId": request_id,
                    },
                },
            )
            return
        except Exception as e:
            logger.error(
                "Skill untrack failed",
                extra={
                    "service": "skills",
                    "user_id": str(user_id),
                    "skill_id": str(skill_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SKILLS_ERROR",
                        "message": "Failed to untrack skill",
                        "requestId": request_id,
                    },
                },
            )
            return

    await manager.send_message(
        websocket,
        {
            "type": "skills.untrack.success",
            "payload": {"skillId": str(skill_id)},
        },
    )


@router.handler("skills.detail")
async def handle_skills_detail(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Get full skill detail including rubric and user progress."""

    user_id = await _ensure_authenticated(websocket, manager)
    if not user_id:
        return

    request_id = payload.get("requestId")
    skill_id_str = payload.get("skillId")

    if not skill_id_str:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "skillId is required",
                    "requestId": request_id,
                },
            },
        )
        return

    try:
        skill_id = uuid.UUID(skill_id_str)
    except ValueError as e:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": f"Invalid skillId UUID format: {e}",
                    "requestId": request_id,
                },
            },
        )
        return

    async with get_session_context() as db:
        service = SkillService(db)
        try:
            detail = await service.get_skill_detail(skill_id, user_id=user_id)
        except SkillNotFoundError as e:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SKILL_NOT_FOUND",
                        "message": str(e),
                        "requestId": request_id,
                    },
                },
            )
            return
        except Exception as e:
            logger.error(
                "Skill detail failed",
                extra={
                    "service": "skills",
                    "user_id": str(user_id),
                    "skill_id": str(skill_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "SKILLS_ERROR",
                        "message": "Failed to load skill detail",
                        "requestId": request_id,
                    },
                },
            )
            return

    await manager.send_message(
        websocket,
        {
            "type": "status.update",
            "payload": {
                "service": "skills",
                "status": "complete",
                "metadata": {
                    "operation": "detail",
                    "skillId": str(skill_id),
                },
            },
        },
    )

    await manager.send_message(
        websocket,
        {
            "type": "skills.detail",
            "payload": {
                "skill": detail.model_dump(mode="json"),
            },
        },
    )
