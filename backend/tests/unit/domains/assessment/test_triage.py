"""Unit tests for TriageService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.providers.base import LLMResponse
from app.domains.assessment.triage import TriageService
from app.schemas.assessment import ChatMessage, ChatRole, TriageDecision, TriageRequest


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession-like object."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_llm():
    """Create a mock LLM provider for triage."""
    llm = AsyncMock()
    llm.name = "mock-triage"
    return llm


@pytest.fixture
def triage_service(mock_db, mock_llm):
    """Create a TriageService with mocked dependencies."""
    return TriageService(db=mock_db, llm_provider=mock_llm)


@pytest.mark.asyncio
async def test_classify_response_assess_happy_path(triage_service, mock_db, mock_llm):
    """LLM returning assess JSON yields TriageDecision.ASSESS and logs entry."""

    session_id = uuid.uuid4()
    request = TriageRequest(
        session_id=session_id,
        user_response="I think we should definitely move forward with this proposal.",
        context=[
            ChatMessage(role=ChatRole.ASSISTANT, content="Practice pitching your proposal."),
            ChatMessage(role=ChatRole.USER, content="Okay, let me try."),
        ],
    )

    mock_llm.generate.return_value = LLMResponse(
        content='{"decision": "assess", "reason": "skill_practice_detected"}',
        model="mock-triage",
        tokens_in=10,
        tokens_out=5,
    )

    status_updates: list[tuple[str, str]] = []

    async def track_status(service: str, status: str, _meta):
        status_updates.append((service, status))

    with patch("app.domains.assessment.triage.TriageLog") as MockTriageLog:
        response = await triage_service.classify_response(request, send_status=track_status)

    # Response fields
    assert response.decision == TriageDecision.ASSESS
    assert response.reason == "skill_practice_detected"
    assert response.latency_ms is not None
    assert response.tokens_used == 15
    # Cost is derived from tokens_used; just assert it's non-negative
    assert response.cost_cents is not None
    assert response.cost_cents >= 0

    # LLM was called once with built messages
    mock_llm.generate.assert_awaited_once()

    # TriageLog entry was created and persisted
    MockTriageLog.assert_called_once()
    log_kwargs = MockTriageLog.call_args.kwargs
    assert log_kwargs["session_id"] == session_id
    assert log_kwargs["decision"] == TriageDecision.ASSESS.value
    assert log_kwargs["reason"] == "skill_practice_detected"
    assert log_kwargs["latency_ms"] == response.latency_ms
    assert log_kwargs["tokens_used"] == response.tokens_used
    assert log_kwargs["cost_cents"] == response.cost_cents

    # TriageLog must be persisted; there may be additional adds (e.g. ProviderCall)
    mock_db.add.assert_any_call(MockTriageLog.return_value)
    mock_db.flush.assert_awaited()

    # Status events
    assert ("triage", "started") in status_updates
    assert ("triage", "complete") in status_updates


@pytest.mark.asyncio
async def test_classify_response_llm_error_falls_back_to_skip(triage_service, mock_db, mock_llm):
    """If LLM raises, triage falls back to SKIP with triage_error and still logs."""

    session_id = uuid.uuid4()
    request = TriageRequest(
        session_id=session_id,
        user_response="Hi, what can you help me with?",
        context=[],
    )

    mock_llm.generate.side_effect = RuntimeError("LLM failure")

    status_updates: list[tuple[str, str]] = []

    async def track_status(service: str, status: str, _meta):
        status_updates.append((service, status))

    with patch("app.domains.assessment.triage.TriageLog") as MockTriageLog:
        response = await triage_service.classify_response(request, send_status=track_status)

    # Falls back to SKIP with generic reason
    assert response.decision == TriageDecision.SKIP
    assert response.reason == "triage_error"
    assert response.tokens_used is None
    assert response.cost_cents is None

    # Log entry is still written
    MockTriageLog.assert_called_once()
    log_kwargs = MockTriageLog.call_args.kwargs
    assert log_kwargs["session_id"] == session_id
    assert log_kwargs["decision"] == TriageDecision.SKIP.value
    assert log_kwargs["reason"] == "triage_error"

    # TriageLog must be persisted; allow additional adds from ProviderCall logging
    mock_db.add.assert_any_call(MockTriageLog.return_value)
    mock_db.flush.assert_awaited()

    # Status events include error
    assert ("triage", "started") in status_updates
    assert ("triage", "error") in status_updates


@pytest.mark.asyncio
async def test_classify_response_general_chatter_skip(triage_service, mock_db, mock_llm):
    """LLM returning skip/general_chatter yields TriageDecision.SKIP and logs entry."""

    session_id = uuid.uuid4()
    request = TriageRequest(
        session_id=session_id,
        user_response="Honestly I'm just chatting about my day, nothing to practice.",
        context=[
            ChatMessage(role=ChatRole.ASSISTANT, content="How has your day been so far?"),
            ChatMessage(role=ChatRole.USER, content="Pretty relaxed, just catching up."),
        ],
    )

    mock_llm.generate.return_value = LLMResponse(
        content='{"decision": "skip", "reason": "general_chatter"}',
        model="mock-triage",
        tokens_in=12,
        tokens_out=3,
    )

    status_updates: list[tuple[str, str]] = []

    async def track_status(service: str, status: str, _meta):
        status_updates.append((service, status))

    with patch("app.domains.assessment.triage.TriageLog") as MockTriageLog:
        response = await triage_service.classify_response(request, send_status=track_status)

    assert response.decision == TriageDecision.SKIP
    assert response.reason == "general_chatter"
    assert response.latency_ms is not None
    assert response.tokens_used == 15
    assert response.cost_cents is not None
    assert response.cost_cents >= 0

    MockTriageLog.assert_called_once()
    log_kwargs = MockTriageLog.call_args.kwargs
    assert log_kwargs["session_id"] == session_id
    assert log_kwargs["decision"] == TriageDecision.SKIP.value
    assert log_kwargs["reason"] == "general_chatter"
    assert log_kwargs["latency_ms"] == response.latency_ms
    assert log_kwargs["tokens_used"] == response.tokens_used
    assert log_kwargs["cost_cents"] == response.cost_cents

    # TriageLog must be persisted; allow additional adds from observability logging
    mock_db.add.assert_any_call(MockTriageLog.return_value)
    mock_db.flush.assert_awaited()

    assert ("triage", "started") in status_updates
    assert ("triage", "complete") in status_updates
