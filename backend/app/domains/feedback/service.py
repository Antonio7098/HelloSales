"""Feedback service for managing user feedback events."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import FeedbackEvent
from app.schemas.feedback import FeedbackMessageFlagCreate, FeedbackReportCreate

logger = logging.getLogger("feedback")


class FeedbackService:
    """Create and query feedback events (flags + reports)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_message_flag(
        self,
        *,
        user_id: UUID,
        data: FeedbackMessageFlagCreate,
    ) -> FeedbackEvent:
        """Create a feedback event tied to a specific interaction."""

        event = FeedbackEvent(
            user_id=user_id,
            session_id=data.session_id,
            interaction_id=data.interaction_id,
            role=data.role.value,
            category=data.category.value,
            name=data.name,
            short_reason=data.short_reason,
            time_bucket=(data.time_bucket.value if data.time_bucket is not None else None),
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logger.info(
            "feedback message flag created",
            extra={
                "service": "feedback",
                "kind": "message_flag",
                "user_id": str(user_id),
                "session_id": str(data.session_id),
                "interaction_id": str(data.interaction_id),
                "category": data.category.value,
                "time_bucket": data.time_bucket.value if data.time_bucket else None,
            },
        )

        return event

    async def create_report(
        self,
        *,
        user_id: UUID,
        data: FeedbackReportCreate,
    ) -> FeedbackEvent:
        """Create a high-level feedback report (optionally tied to a session)."""

        event = FeedbackEvent(
            user_id=user_id,
            session_id=data.session_id,
            interaction_id=data.interaction_id,
            role=None,
            category=data.category.value,
            name=data.name,
            short_reason=data.description,
            time_bucket=data.time_bucket.value,
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logger.info(
            "feedback report created",
            extra={
                "service": "feedback",
                "kind": "report",
                "user_id": str(user_id),
                "session_id": str(data.session_id) if data.session_id else None,
                "interaction_id": (str(data.interaction_id) if data.interaction_id else None),
                "category": data.category.value,
                "scope": data.scope,
                "time_bucket": data.time_bucket.value,
            },
        )

        return event

    async def list_recent_feedback(
        self,
        *,
        user_id: UUID,
        limit: int = 50,
    ) -> list[FeedbackEvent]:
        """Return recent feedback events for a user (most recent first)."""

        if limit <= 0:
            limit = 1
        if limit > 100:
            limit = 100

        result = await self.db.execute(
            select(FeedbackEvent)
            .where(FeedbackEvent.user_id == user_id)
            .order_by(FeedbackEvent.created_at.desc())
            .limit(limit)
        )
        rows: Iterable[FeedbackEvent] = result.scalars().all()

        logger.info(
            "feedback events listed",
            extra={
                "service": "feedback",
                "user_id": str(user_id),
                "count": len(rows),
            },
        )

        return list(rows)

    async def list_all_feedback(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FeedbackEvent]:
        """Return all feedback events (most recent first) - admin only."""

        if limit <= 0:
            limit = 1
        if limit > 1000:
            limit = 1000

        result = await self.db.execute(
            select(FeedbackEvent)
            .order_by(FeedbackEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows: Iterable[FeedbackEvent] = result.scalars().all()

        logger.info(
            "all feedback events listed",
            extra={
                "service": "feedback",
                "count": len(rows),
                "limit": limit,
                "offset": offset,
            },
        )

        return list(rows)
