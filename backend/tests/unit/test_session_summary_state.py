from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hello_sales_backend.platform.sessions.memory import InMemorySessionStore
from hello_sales_backend.platform.sessions.models import Session, SessionStatus


@pytest.mark.asyncio
async def test_summary_state_update_does_not_overwrite_session_lifecycle() -> None:
    store = InMemorySessionStore()
    session = Session(
        session_id="session-1",
        status=SessionStatus.ACTIVE,
        profile_name="generic",
        latest_item_id="item-current",
        latest_run_id="run-current",
        completed_at=None,
    )
    await store.create_session(session)

    await store.update_session_summary_state(
        session_id=session.session_id,
        summary_task_id="summary-task",
        summary_status="completed",
        last_summarized_item_sequence=8,
        updated_at=datetime(2026, 4, 25, tzinfo=UTC),
    )

    updated = await store.get_session(session.session_id)
    assert updated is not None
    assert updated.status == SessionStatus.ACTIVE
    assert updated.latest_item_id == "item-current"
    assert updated.latest_run_id == "run-current"
    assert updated.completed_at is None
    assert updated.summary_task_id == "summary-task"
    assert updated.summary_status == "completed"
    assert updated.last_summarized_item_sequence == 8
