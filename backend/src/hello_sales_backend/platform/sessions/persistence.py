"""Persistence contracts for sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from hello_sales_backend.platform.sessions.models import Session, SessionItem, SessionSummary


class SessionStorePort(Protocol):
    """Persistence contract for session state and chronology."""

    async def create_session(self, session: Session) -> None: ...

    async def get_session(self, session_id: str) -> Session | None: ...

    async def update_session(self, session: Session) -> None: ...

    async def update_session_summary_state(
        self,
        *,
        session_id: str,
        summary_task_id: str | None,
        summary_status: str | None,
        last_summarized_item_sequence: int | None,
        updated_at: datetime,
    ) -> None: ...

    async def list_sessions(self, *, limit: int = 50) -> list[Session]: ...

    async def create_item(self, item: SessionItem) -> None: ...

    async def list_items(self, session_id: str, *, limit: int = 500) -> list[SessionItem]: ...

    async def next_item_sequence(self, session_id: str) -> int: ...

    async def upsert_summary(self, summary: SessionSummary) -> None: ...

    async def get_latest_summary(self, session_id: str) -> SessionSummary | None: ...
