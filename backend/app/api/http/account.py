"""HTTP endpoints for account-level operations (e.g. deletion)."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.http.dependencies import get_current_user
from app.api.ws.manager import get_connection_manager
from app.database import get_session
from app.models import User

router = APIRouter(prefix="/api/v1", tags=["account"])
logger = logging.getLogger("account")


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    started_at = datetime.utcnow()
    user_id = user.id

    logger.info(
        "Account deletion requested",
        extra={
            "service": "account",
            "user_id": str(user_id),
        },
    )

    # Re-fetch user in this session to avoid cross-session ownership issues
    user_to_delete = await session.get(User, user_id)
    if user_to_delete is None:
        # User already deleted or doesn't exist
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    await session.delete(user_to_delete)

    manager = get_connection_manager()
    disconnected = await manager.disconnect_user(user_id)

    duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)

    logger.info(
        "Account deletion completed",
        extra={
            "service": "account",
            "user_id": str(user_id),
            "disconnected_ws": disconnected,
            "duration_ms": duration_ms,
        },
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
