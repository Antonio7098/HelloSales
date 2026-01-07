"""Unit tests for FeedbackService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.feedback.service import FeedbackService
from app.models.feedback import FeedbackEvent
from app.schemas.feedback import (
    FeedbackCategory,
    FeedbackMessageFlagCreate,
    FeedbackReportCreate,
    FeedbackRole,
    TimeBucket,
)


@pytest.fixture
def mock_db() -> AsyncSession:
    """Create a mocked AsyncSession so tests do not touch a real database."""

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_create_message_flag_creates_event_and_commits(mock_db: AsyncSession) -> None:
    """create_message_flag should persist a FeedbackEvent for an interaction."""

    service = FeedbackService(mock_db)
    user_id = uuid.uuid4()

    data = FeedbackMessageFlagCreate(
        session_id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        role=FeedbackRole.ASSISTANT,
        category=FeedbackCategory.BAD_ASSISTANT,
        name="Bad answer",
        short_reason="Off-topic",
        time_bucket=TimeBucket.JUST_NOW,
    )

    event = await service.create_message_flag(user_id=user_id, data=data)

    assert isinstance(event, FeedbackEvent)
    assert event.user_id == user_id
    assert event.session_id == data.session_id
    assert event.interaction_id == data.interaction_id
    assert event.role == data.role.value
    assert event.category == data.category.value
    assert event.name == data.name
    assert event.short_reason == data.short_reason
    assert event.time_bucket == data.time_bucket.value

    mock_db.add.assert_called_once_with(event)
    mock_db.commit.assert_awaited()
    mock_db.refresh.assert_awaited_with(event)


@pytest.mark.asyncio
async def test_create_message_flag_supports_triage_incorrect(mock_db: AsyncSession) -> None:
    """create_message_flag should accept category=triage_incorrect for triage review flags."""

    service = FeedbackService(mock_db)
    user_id = uuid.uuid4()

    data = FeedbackMessageFlagCreate(
        session_id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        role=FeedbackRole.ASSISTANT,
        category=FeedbackCategory.TRIAGE_INCORRECT,
        name="Triage was wrong",
        short_reason="Should have been assessed",
        time_bucket=None,
    )

    event = await service.create_message_flag(user_id=user_id, data=data)

    assert event.category == FeedbackCategory.TRIAGE_INCORRECT.value


@pytest.mark.asyncio
async def test_create_report_creates_global_report(mock_db: AsyncSession) -> None:
    """create_report should persist a high-level report event."""

    service = FeedbackService(mock_db)
    user_id = uuid.uuid4()

    data = FeedbackReportCreate(
        category=FeedbackCategory.BUG,
        name="App crash",
        description="Crashed on open",
        scope="app",
        time_bucket=TimeBucket.EARLIER_TODAY,
        session_id=None,
        interaction_id=None,
    )

    event = await service.create_report(user_id=user_id, data=data)

    assert isinstance(event, FeedbackEvent)
    assert event.user_id == user_id
    assert event.session_id is None
    assert event.interaction_id is None
    assert event.role is None
    assert event.category == data.category.value
    assert event.name == data.name
    assert event.short_reason == data.description
    assert event.time_bucket == data.time_bucket.value

    mock_db.add.assert_called_once_with(event)
    mock_db.commit.assert_awaited()
    mock_db.refresh.assert_awaited_with(event)


@pytest.mark.asyncio
async def test_list_recent_feedback_returns_events(mock_db: AsyncSession) -> None:
    """list_recent_feedback should return events from the database in order."""

    service = FeedbackService(mock_db)
    user_id = uuid.uuid4()

    e1 = FeedbackEvent(
        user_id=user_id,
        session_id=uuid.uuid4(),
        interaction_id=None,
        role="assistant",
        category="bad_assistant",
        name="One",
    )
    e2 = FeedbackEvent(
        user_id=user_id,
        session_id=uuid.uuid4(),
        interaction_id=None,
        role="assistant",
        category="improvement",
        name="Two",
    )

    result = MagicMock()
    result.scalars.return_value.all.return_value = [e1, e2]
    mock_db.execute.return_value = result

    items = await service.list_recent_feedback(user_id=user_id, limit=10)

    assert items == [e1, e2]
    mock_db.execute.assert_awaited()
