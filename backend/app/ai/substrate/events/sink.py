from __future__ import annotations

import asyncio
import logging
import uuid
from contextvars import ContextVar
from typing import Any

from app.database import get_session_context
from app.logging_config import (
    org_id_var,
    pipeline_run_id_var,
    request_id_var,
    session_id_var,
    user_id_var,
)

logger = logging.getLogger("event_sink")


def _parse_context_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


class EventSink:
    async def emit(self, *, type: str, data: dict[str, Any] | None) -> None:
        raise NotImplementedError

    def try_emit(self, *, type: str, data: dict[str, Any] | None) -> None:
        raise NotImplementedError


class NoOpEventSink(EventSink):
    async def emit(self, *, type: str, data: dict[str, Any] | None) -> None:
        _ = type, data
        return None

    def try_emit(self, *, type: str, data: dict[str, Any] | None) -> None:
        _ = type, data
        return None


class DbPipelineEventSink(EventSink):
    def __init__(self, *, run_service: str) -> None:
        self._run_service = run_service

    async def emit(self, *, type: str, data: dict[str, Any] | None) -> None:
        try:
            from app.ai.substrate import PipelineEventLogger

            pipeline_run_id = _parse_context_uuid(pipeline_run_id_var.get())
            if pipeline_run_id is None:
                return

            request_id = _parse_context_uuid(request_id_var.get())
            session_id = _parse_context_uuid(session_id_var.get())
            user_id = _parse_context_uuid(user_id_var.get())
            org_id = _parse_context_uuid(org_id_var.get())

            async with get_session_context() as db:
                event_logger = PipelineEventLogger(db)
                await event_logger.create_run(
                    pipeline_run_id=pipeline_run_id,
                    service=self._run_service,
                    request_id=request_id,
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                )
                await event_logger.emit(
                    pipeline_run_id=pipeline_run_id,
                    type=type,
                    request_id=request_id,
                    session_id=session_id,
                    user_id=user_id,
                    org_id=org_id,
                    data=data,
                )
        except Exception:
            logger.error(
                "Failed to persist pipeline event",
                extra={"service": "event_sink", "event_type": type},
                exc_info=True,
            )

    def try_emit(self, *, type: str, data: dict[str, Any] | None) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        task = loop.create_task(self.emit(type=type, data=data))
        _pending_emit_tasks.add(task)
        task.add_done_callback(_pending_emit_tasks.discard)


_event_sink_var: ContextVar[EventSink | None] = ContextVar("event_sink", default=None)
_pending_emit_tasks: set[asyncio.Task[Any]] = set()


def set_event_sink(sink: EventSink) -> None:
    _event_sink_var.set(sink)


def clear_event_sink() -> None:
    _event_sink_var.set(None)


def get_event_sink() -> EventSink:
    return _event_sink_var.get() or NoOpEventSink()


async def wait_for_event_sink_tasks() -> None:
    """Await any pending event sink emit tasks (used in tests)."""

    if not _pending_emit_tasks:
        return

    pending = list(_pending_emit_tasks)
    try:
        await asyncio.gather(*pending, return_exceptions=True)
    finally:
        for task in pending:
            _pending_emit_tasks.discard(task)
