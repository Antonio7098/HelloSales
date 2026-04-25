"""In-memory session persistence."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from hello_sales_backend.platform.sessions.models import Session, SessionItem, SessionSummary


class InMemorySessionStore:
    """Small in-memory session store for local and sqlite-backed tests."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._items: dict[str, SessionItem] = {}
        self._summaries: dict[str, SessionSummary] = {}

    async def create_session(self, session: Session) -> None:
        self._sessions[session.session_id] = replace(session)

    async def get_session(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        return None if session is None else replace(session)

    async def update_session(self, session: Session) -> None:
        self._sessions[session.session_id] = replace(session)

    async def update_session_summary_state(
        self,
        *,
        session_id: str,
        summary_task_id: str | None,
        summary_status: str | None,
        last_summarized_item_sequence: int | None,
        updated_at: datetime,
    ) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        next_session = replace(
            session,
            summary_task_id=summary_task_id,
            summary_status=summary_status,
            updated_at=updated_at,
        )
        if last_summarized_item_sequence is not None:
            next_session.last_summarized_item_sequence = last_summarized_item_sequence
        self._sessions[session_id] = next_session

    async def list_sessions(self, *, limit: int = 50) -> list[Session]:
        ordered = sorted(self._sessions.values(), key=lambda item: item.created_at, reverse=True)
        return [replace(item) for item in ordered[:limit]]

    async def create_item(self, item: SessionItem) -> None:
        self._items[item.item_id] = replace(item)

    async def list_items(self, session_id: str, *, limit: int = 500) -> list[SessionItem]:
        matches = [item for item in self._items.values() if item.session_id == session_id]
        ordered = sorted(matches, key=lambda item: item.sequence_no)
        return [replace(item) for item in ordered[:limit]]

    async def next_item_sequence(self, session_id: str) -> int:
        current = max((item.sequence_no for item in self._items.values() if item.session_id == session_id), default=0)
        return current + 1

    async def upsert_summary(self, summary: SessionSummary) -> None:
        self._summaries[summary.session_id] = replace(summary)

    async def get_latest_summary(self, session_id: str) -> SessionSummary | None:
        summary = self._summaries.get(session_id)
        return None if summary is None else replace(summary)
