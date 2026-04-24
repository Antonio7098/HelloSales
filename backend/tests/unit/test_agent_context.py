from __future__ import annotations

import pytest

from hello_sales_backend.platform.agents.context import (
    BASIC_CONTEXT_PROFILE_ID,
    SESSION_CONTEXT_SOURCE_ID,
    AgentContextBudget,
    AgentContextBuildRequest,
    AgentContextFailurePolicy,
    AgentContextProfile,
    AgentContextSourceCategory,
    AgentContextSourceRef,
    AgentContextSourceScope,
    BasicSessionContextSource,
    FakeAgentContextSource,
    FakeLongTermMemoryContextSource,
    ProfiledAgentContextAssembler,
    basic_session_context_profile,
)
from hello_sales_backend.platform.agents.models import (
    AgentRun,
    AgentRunStatus,
    AgentTurn,
    AgentTurnStatus,
)
from hello_sales_backend.platform.llm import PromptMetadata, effective_prompt_ref
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage
from hello_sales_backend.platform.sessions.memory import InMemorySessionStore
from hello_sales_backend.platform.sessions.models import (
    SessionItem,
    SessionItemType,
    SessionSummary,
    SessionSummaryStatus,
)
from hello_sales_backend.shared.errors import AppError, app_error


def _prompt_ref():
    return effective_prompt_ref(
        PromptMetadata(
            prompt_id="agent.context.test",
            version="v1",
            owner_kind="agent",
            owner_id="generic",
            purpose="response",
        )
    )


def _request(
    *,
    input_text: str = "current question",
    session_id: str | None = "session-1",
    base_messages: tuple[ChatMessage, ...] = (ChatMessage(role="user", content="current question"),),
) -> AgentContextBuildRequest:
    run = AgentRun(
        run_id="run-1",
        profile_name="generic",
        status=AgentRunStatus.RUNNING,
        request_id="req-1",
        trace_id="trace-1",
        actor_id="actor-1",
        org_id="org-1",
        permissions=("agent:run",),
        session_id=session_id,
        prompt=_prompt_ref(),
    )
    turn = AgentTurn(
        turn_id="turn-1",
        run_id=run.run_id,
        sequence_no=1,
        input_text=input_text,
        status=AgentTurnStatus.RUNNING,
        prompt=run.prompt,
    )
    return AgentContextBuildRequest(
        run=run,
        turn=turn,
        base_messages=base_messages,
        effective_prompt=turn.prompt,
        profile_id=BASIC_CONTEXT_PROFILE_ID,
    )


@pytest.mark.asyncio
async def test_context_assembler_orders_sources_after_system_prompt() -> None:
    profile = AgentContextProfile(
        profile_id="profile-a",
        version="v1",
        description="ordered",
        sources=(
            AgentContextSourceRef(
                source_id="first",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
            ),
            AgentContextSourceRef(
                source_id="second",
                category=AgentContextSourceCategory.RETRIEVAL,
                scope=AgentContextSourceScope.SESSION,
            ),
        ),
    )
    assembler = ProfiledAgentContextAssembler(
        profiles={"profile-a": profile},
        sources={
            "first": FakeAgentContextSource(
                source_id="first",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
                messages=(ChatMessage(role="system", content="memory"),),
            ),
            "second": FakeAgentContextSource(
                source_id="second",
                category=AgentContextSourceCategory.RETRIEVAL,
                scope=AgentContextSourceScope.SESSION,
                messages=(ChatMessage(role="system", content="retrieved"),),
            ),
        },
    )
    request = _request(
        base_messages=(
            ChatMessage(role="system", content="base system"),
            ChatMessage(role="user", content="current question"),
        )
    )

    result = await assembler.build(
        AgentContextBuildRequest(
            run=request.run,
            turn=request.turn,
            base_messages=request.base_messages,
            effective_prompt=request.effective_prompt,
            profile_id="profile-a",
        )
    )

    assert [message.content for message in result.messages] == [
        "base system",
        "memory",
        "retrieved",
        "current question",
    ]
    assert result.event_payload()["context_profile_id"] == "profile-a"


@pytest.mark.asyncio
async def test_context_assembler_applies_message_budget_and_records_truncation() -> None:
    profile = AgentContextProfile(
        profile_id="budgeted",
        version="v1",
        description="budgeted",
        budget=AgentContextBudget(max_context_messages=1),
        sources=(
            AgentContextSourceRef(
                source_id="memory",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
            ),
        ),
    )
    assembler = ProfiledAgentContextAssembler(
        profiles={"budgeted": profile},
        sources={
            "memory": FakeAgentContextSource(
                source_id="memory",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
                messages=(
                    ChatMessage(role="system", content="keep"),
                    ChatMessage(role="system", content="drop"),
                ),
            )
        },
    )
    request = _request()

    result = await assembler.build(
        AgentContextBuildRequest(
            run=request.run,
            turn=request.turn,
            base_messages=request.base_messages,
            effective_prompt=request.effective_prompt,
            profile_id="budgeted",
        )
    )

    assert [message.content for message in result.messages] == ["keep", "current question"]
    assert result.truncations[0].source_id == "memory"
    assert result.truncations[0].original_message_count == 2
    assert result.truncations[0].emitted_message_count == 1


@pytest.mark.asyncio
async def test_context_assembler_skips_optional_source_failure() -> None:
    failure = app_error(
        "memory unavailable",
        code="memory.unavailable",
        category="internal",
        operation="memory.fake",
        component="agent",
    )
    profile = AgentContextProfile(
        profile_id="optional",
        version="v1",
        description="optional",
        sources=(
            AgentContextSourceRef(
                source_id="memory",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
                failure_policy=AgentContextFailurePolicy.OPTIONAL,
            ),
        ),
    )
    assembler = ProfiledAgentContextAssembler(
        profiles={"optional": profile},
        sources={
            "memory": FakeAgentContextSource(
                source_id="memory",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
                fail_with=failure,
            )
        },
    )
    request = _request()

    result = await assembler.build(
        AgentContextBuildRequest(
            run=request.run,
            turn=request.turn,
            base_messages=request.base_messages,
            effective_prompt=request.effective_prompt,
            profile_id="optional",
        )
    )

    assert [message.content for message in result.messages] == ["current question"]
    assert result.skipped_sources[0].source_id == "memory"
    assert result.skipped_sources[0].error_code == "memory.unavailable"


@pytest.mark.asyncio
async def test_context_assembler_fails_required_source_failure() -> None:
    profile = AgentContextProfile(
        profile_id="required",
        version="v1",
        description="required",
        sources=(
            AgentContextSourceRef(
                source_id="memory",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
                failure_policy=AgentContextFailurePolicy.REQUIRED,
            ),
        ),
    )
    assembler = ProfiledAgentContextAssembler(
        profiles={"required": profile},
        sources={
            "memory": FakeAgentContextSource(
                source_id="memory",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
                fail_with=app_error(
                    "memory unavailable",
                    code="memory.unavailable",
                    category="internal",
                    operation="memory.fake",
                    component="agent",
                ),
            )
        },
    )
    request = _request()

    with pytest.raises(AppError) as exc_info:
        await assembler.build(
            AgentContextBuildRequest(
                run=request.run,
                turn=request.turn,
                base_messages=request.base_messages,
                effective_prompt=request.effective_prompt,
                profile_id="required",
            )
        )

    assert exc_info.value.code == "agent.context.source_failed"
    assert exc_info.value.details["source_id"] == "memory"


@pytest.mark.asyncio
async def test_basic_session_profile_matches_summary_and_recent_item_shape() -> None:
    session_store = InMemorySessionStore()
    prompt = _prompt_ref()
    await session_store.upsert_summary(
        SessionSummary(
            summary_id="summary-1",
            session_id="session-1",
            coverage_start_sequence=1,
            coverage_end_sequence=2,
            summary_text="Older summary.",
            prompt=prompt,
            status=SessionSummaryStatus.COMPLETED,
        )
    )
    for item in (
        SessionItem(
            item_id="item-1",
            session_id="session-1",
            sequence_no=1,
            item_type=SessionItemType.USER_MESSAGE,
            payload={"text": "covered user"},
        ),
        SessionItem(
            item_id="item-2",
            session_id="session-1",
            sequence_no=2,
            item_type=SessionItemType.ASSISTANT_MESSAGE,
            payload={"text": "covered assistant"},
        ),
        SessionItem(
            item_id="item-3",
            session_id="session-1",
            sequence_no=3,
            item_type=SessionItemType.USER_MESSAGE,
            payload={"text": "recent user"},
        ),
        SessionItem(
            item_id="item-4",
            session_id="session-1",
            sequence_no=4,
            item_type=SessionItemType.TOOL_RESULT,
            payload={"result": {"entity_ref": "company:1", "version": 2}},
        ),
        SessionItem(
            item_id="item-5",
            session_id="session-1",
            sequence_no=5,
            item_type=SessionItemType.USER_MESSAGE,
            payload={"text": "current question"},
        ),
    ):
        await session_store.create_item(item)
    source = BasicSessionContextSource(session_store=session_store)

    result = await source.build(_request())

    assert [message.role for message in result.messages] == ["system", "user", "system"]
    assert "Conversation summary for older turns" in result.messages[0].content
    assert "Older summary." in result.messages[0].content
    assert result.messages[1].content == "recent user"
    assert (
        result.messages[2].content
        == 'Recent tool result context from this session. Reuse any entity refs, versions, and bounded tool evidence it contains when relevant.\n{"entity_ref":"company:1","version":2}'
    )
    assert result.provenance[0].metadata["recent_item_limit"] == 16


@pytest.mark.asyncio
async def test_fake_long_term_memory_source_can_be_enabled_by_profile() -> None:
    profile = AgentContextProfile(
        profile_id="memory-enabled",
        version="v1",
        description="memory enabled",
        sources=(
            AgentContextSourceRef(
                source_id="fake-long-term-memory",
                category=AgentContextSourceCategory.SEMANTIC_MEMORY,
                scope=AgentContextSourceScope.ACTOR,
                failure_policy=AgentContextFailurePolicy.OPTIONAL,
            ),
        ),
    )
    assembler = ProfiledAgentContextAssembler(
        profiles={"memory-enabled": profile},
        sources={
            "fake-long-term-memory": FakeLongTermMemoryContextSource(
                messages=(ChatMessage(role="system", content="remembered preference"),)
            )
        },
    )
    request = _request()

    result = await assembler.build(
        AgentContextBuildRequest(
            run=request.run,
            turn=request.turn,
            base_messages=request.base_messages,
            effective_prompt=request.effective_prompt,
            profile_id="memory-enabled",
        )
    )

    assert [message.content for message in result.messages] == [
        "remembered preference",
        "current question",
    ]
    assert result.source_results[0].category == AgentContextSourceCategory.SEMANTIC_MEMORY


def test_basic_profile_exposes_recent_limit_as_parameter() -> None:
    profile = basic_session_context_profile()

    assert profile.profile_id == BASIC_CONTEXT_PROFILE_ID
    assert profile.parameters["recent_item_limit"] == 16
    assert profile.sources[0].source_id == SESSION_CONTEXT_SOURCE_ID
