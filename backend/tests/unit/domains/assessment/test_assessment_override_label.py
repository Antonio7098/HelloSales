"""Unit tests for general_chatter → manual assess override labeling.

Covers AssessmentService._compute_triage_override_label behaviour.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.assessment.service import AssessmentService
from app.models import TriageLog


@pytest.fixture
def mock_db() -> AsyncSession:
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_db: AsyncSession) -> AssessmentService:
    # Use a simple AsyncMock as LLM provider; it won't be used in these tests
    llm = AsyncMock()
    llm.name = "mock-llm"
    return AssessmentService(db=mock_db, llm_provider=llm)


@pytest.mark.asyncio
async def test_compute_triage_override_label_returns_none_for_non_manual(
    service: AssessmentService, mock_db: AsyncSession
) -> None:
    """When triage_decision is not 'manual', override label should be None and DB not queried."""

    label = await service._compute_triage_override_label(  # type: ignore[attr-defined]
        session_id=uuid.uuid4(),
        interaction_id=uuid.uuid4(),
        triage_decision="assess",
    )

    assert label is None
    mock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_compute_triage_override_label_detects_general_chatter_skip(
    service: AssessmentService, mock_db: AsyncSession
) -> None:
    """When triage_decision is manual and prior triage_log skip/general_chatter exists, label is set."""

    session_id = uuid.uuid4()
    interaction_id = uuid.uuid4()

    triage_row = TriageLog(
        session_id=session_id,
        interaction_id=interaction_id,
        decision="skip",
        reason="general_chatter",
        latency_ms=None,
        tokens_used=None,
        cost_cents=None,
        created_at=datetime.utcnow(),
    )

    result = MagicMock()
    result.scalar_one_or_none.return_value = triage_row
    mock_db.execute.return_value = result

    label = await service._compute_triage_override_label(  # type: ignore[attr-defined]
        session_id=session_id,
        interaction_id=interaction_id,
        triage_decision="manual",
    )

    assert label == "general_chatter_manual_assess"
    mock_db.execute.assert_awaited()
