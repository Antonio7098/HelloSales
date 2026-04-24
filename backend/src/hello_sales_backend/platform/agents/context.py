"""Agent context assembly contracts and default sources."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from hello_sales_backend.platform.agents.models import AgentRun, AgentTurn
from hello_sales_backend.platform.llm import EffectivePromptRef
from hello_sales_backend.platform.providers.llm.contracts import ChatMessage
from hello_sales_backend.platform.sessions.models import SessionItem, SessionItemType
from hello_sales_backend.platform.sessions.persistence import SessionStorePort
from hello_sales_backend.shared.errors import AppError, app_error

BASIC_CONTEXT_PROFILE_ID = "basic-session-v1"
SESSION_CONTEXT_SOURCE_ID = "session-history"


class AgentContextSourceCategory(StrEnum):
    """Stable source categories for model-visible agent context."""

    SESSION = "session"
    SUMMARY = "summary"
    SEMANTIC_MEMORY = "semantic_memory"
    EPISODIC_MEMORY = "episodic_memory"
    PROCEDURAL_MEMORY = "procedural_memory"
    RETRIEVAL = "retrieval"


class AgentContextSourceScope(StrEnum):
    """Supported context-source scopes."""

    TURN = "turn"
    SESSION = "session"
    ACTOR = "actor"
    ORG = "org"
    AGENT = "agent"
    GLOBAL = "global"


class AgentContextFailurePolicy(StrEnum):
    """How a profile treats source failure."""

    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass(frozen=True, slots=True)
class AgentContextBudget:
    """Simple model-visible context budget."""

    max_context_messages: int | None = None


@dataclass(frozen=True, slots=True)
class AgentContextSourceRef:
    """One source entry inside a context profile."""

    source_id: str
    category: AgentContextSourceCategory
    scope: AgentContextSourceScope
    failure_policy: AgentContextFailurePolicy = AgentContextFailurePolicy.REQUIRED


@dataclass(frozen=True, slots=True)
class AgentContextProfile:
    """Named context profile selected independently from an agent definition."""

    profile_id: str
    version: str
    description: str
    sources: tuple[AgentContextSourceRef, ...]
    budget: AgentContextBudget = field(default_factory=AgentContextBudget)
    parameters: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentContextBuildRequest:
    """Runtime-local data available to context sources."""

    run: AgentRun
    turn: AgentTurn
    base_messages: tuple[ChatMessage, ...]
    effective_prompt: EffectivePromptRef | None
    profile_id: str


@dataclass(frozen=True, slots=True)
class AgentContextProvenance:
    """Redacted provenance for context that entered model-visible messages."""

    source_id: str
    category: AgentContextSourceCategory
    scope: AgentContextSourceScope
    item_count: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentContextSourceResult:
    """Messages and provenance produced by one context source."""

    source_id: str
    category: AgentContextSourceCategory
    scope: AgentContextSourceScope
    messages: tuple[ChatMessage, ...] = ()
    provenance: tuple[AgentContextProvenance, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AgentContextSkippedSource:
    """Redacted skip/failure metadata for a source."""

    source_id: str
    category: AgentContextSourceCategory
    scope: AgentContextSourceScope
    reason: str
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class AgentContextTruncation:
    """A source-level truncation decision."""

    source_id: str
    original_message_count: int
    emitted_message_count: int
    reason: str


@dataclass(frozen=True, slots=True)
class AgentContextBuildResult:
    """Final assembled messages plus redacted assembly metadata."""

    profile: AgentContextProfile
    messages: tuple[ChatMessage, ...]
    source_results: tuple[AgentContextSourceResult, ...]
    skipped_sources: tuple[AgentContextSkippedSource, ...] = ()
    truncations: tuple[AgentContextTruncation, ...] = ()
    warnings: tuple[str, ...] = ()

    def event_payload(self) -> dict[str, object]:
        """Return event-safe profile/source metadata without raw context text."""

        return {
            "context_profile_id": self.profile.profile_id,
            "context_profile_version": self.profile.version,
            "context_source_count": len(self.source_results),
            "context_message_count": sum(len(result.messages) for result in self.source_results),
            "context_sources": [
                {
                    "source_id": result.source_id,
                    "category": result.category.value,
                    "scope": result.scope.value,
                    "message_count": len(result.messages),
                    "provenance": [
                        {
                            "source_id": item.source_id,
                            "category": item.category.value,
                            "scope": item.scope.value,
                            "item_count": item.item_count,
                            "metadata": item.metadata,
                        }
                        for item in result.provenance
                    ],
                    "warnings": list(result.warnings),
                }
                for result in self.source_results
            ],
            "context_skipped_sources": [
                {
                    "source_id": item.source_id,
                    "category": item.category.value,
                    "scope": item.scope.value,
                    "reason": item.reason,
                    "error_code": item.error_code,
                }
                for item in self.skipped_sources
            ],
            "context_truncations": [
                {
                    "source_id": item.source_id,
                    "original_message_count": item.original_message_count,
                    "emitted_message_count": item.emitted_message_count,
                    "reason": item.reason,
                }
                for item in self.truncations
            ],
            "context_warnings": list(self.warnings),
        }


class AgentContextSource(Protocol):
    """Source that can provide model-visible context for a run."""

    source_id: str
    category: AgentContextSourceCategory
    scope: AgentContextSourceScope

    async def build(self, request: AgentContextBuildRequest) -> AgentContextSourceResult: ...


class AgentContextAssembler(Protocol):
    """Assemble final model-visible messages from a named profile."""

    async def build(self, request: AgentContextBuildRequest) -> AgentContextBuildResult: ...


@dataclass(slots=True)
class ProfiledAgentContextAssembler:
    """Deterministic source/profile based context assembler."""

    profiles: dict[str, AgentContextProfile]
    sources: dict[str, AgentContextSource]

    async def build(self, request: AgentContextBuildRequest) -> AgentContextBuildResult:
        profile = self.profiles.get(request.profile_id)
        if profile is None:
            raise app_error(
                "Agent context profile was not found",
                code="agent.context.profile_not_found",
                category="validation",
                status_code=400,
                details={
                    "profile_id": request.profile_id,
                    "available_profile_ids": sorted(self.profiles),
                    "run_id": request.run.run_id,
                    "turn_id": request.turn.turn_id,
                },
                operation="agent.context.build",
                component="agent",
            )

        context_messages: list[ChatMessage] = []
        source_results: list[AgentContextSourceResult] = []
        skipped_sources: list[AgentContextSkippedSource] = []
        truncations: list[AgentContextTruncation] = []
        warnings: list[str] = []
        remaining_messages = profile.budget.max_context_messages

        for source_ref in profile.sources:
            source = self.sources.get(source_ref.source_id)
            if source is None:
                skipped = AgentContextSkippedSource(
                    source_id=source_ref.source_id,
                    category=source_ref.category,
                    scope=source_ref.scope,
                    reason="source_not_registered",
                    error_code="agent.context.source_not_registered",
                )
                if source_ref.failure_policy == AgentContextFailurePolicy.REQUIRED:
                    raise self._source_error(
                        message="Required agent context source is not registered",
                        source_ref=source_ref,
                        run=request.run,
                        turn=request.turn,
                        profile=profile,
                    )
                skipped_sources.append(skipped)
                continue

            try:
                result = await source.build(request)
            except AppError as exc:
                if source_ref.failure_policy == AgentContextFailurePolicy.REQUIRED:
                    raise self._source_error(
                        message="Required agent context source failed",
                        source_ref=source_ref,
                        run=request.run,
                        turn=request.turn,
                        profile=profile,
                        exc=exc,
                    ) from exc
                skipped_sources.append(
                    AgentContextSkippedSource(
                        source_id=source_ref.source_id,
                        category=source_ref.category,
                        scope=source_ref.scope,
                        reason="source_failed",
                        error_code=exc.code,
                    )
                )
                warnings.append(f"optional source failed: {source_ref.source_id}")
                continue
            except Exception as exc:
                if source_ref.failure_policy == AgentContextFailurePolicy.REQUIRED:
                    raise self._source_error(
                        message="Required agent context source failed unexpectedly",
                        source_ref=source_ref,
                        run=request.run,
                        turn=request.turn,
                        profile=profile,
                        exc=exc,
                    ) from exc
                skipped_sources.append(
                    AgentContextSkippedSource(
                        source_id=source_ref.source_id,
                        category=source_ref.category,
                        scope=source_ref.scope,
                        reason="source_failed",
                        error_code="agent.context.source_failed",
                    )
                )
                warnings.append(f"optional source failed: {source_ref.source_id}")
                continue

            result_messages = list(result.messages)
            original_count = len(result_messages)
            if remaining_messages is not None:
                if remaining_messages <= 0:
                    result_messages = []
                else:
                    result_messages = result_messages[:remaining_messages]
                remaining_messages -= len(result_messages)
            if len(result_messages) != original_count:
                truncations.append(
                    AgentContextTruncation(
                        source_id=result.source_id,
                        original_message_count=original_count,
                        emitted_message_count=len(result_messages),
                        reason="max_context_messages",
                    )
                )

            emitted_result = AgentContextSourceResult(
                source_id=result.source_id,
                category=result.category,
                scope=result.scope,
                messages=tuple(result_messages),
                provenance=result.provenance,
                warnings=result.warnings,
            )
            context_messages.extend(result_messages)
            source_results.append(emitted_result)
            warnings.extend(result.warnings)

        return AgentContextBuildResult(
            profile=profile,
            messages=tuple(self._insert_context(request.base_messages, tuple(context_messages))),
            source_results=tuple(source_results),
            skipped_sources=tuple(skipped_sources),
            truncations=tuple(truncations),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _insert_context(
        base_messages: tuple[ChatMessage, ...], context_messages: tuple[ChatMessage, ...]
    ) -> tuple[ChatMessage, ...]:
        if base_messages and base_messages[0].role == "system":
            return (base_messages[0], *context_messages, *base_messages[1:])
        return (*context_messages, *base_messages)

    @staticmethod
    def _source_error(
        *,
        message: str,
        source_ref: AgentContextSourceRef,
        run: AgentRun,
        turn: AgentTurn,
        profile: AgentContextProfile,
        exc: BaseException | None = None,
    ) -> AppError:
        return app_error(
            message,
            code="agent.context.source_failed",
            category="internal",
            status_code=500,
            details={
                "profile_id": profile.profile_id,
                "profile_version": profile.version,
                "source_id": source_ref.source_id,
                "source_category": source_ref.category.value,
                "source_scope": source_ref.scope.value,
                "run_id": run.run_id,
                "turn_id": turn.turn_id,
            },
            operation="agent.context.build",
            component="agent",
            exc=exc,
        )


@dataclass(frozen=True, slots=True)
class BasicSessionContextOptions:
    """Profile parameters for the default session context behavior."""

    recent_item_limit: int = 16


@dataclass(slots=True)
class BasicSessionContextSource:
    """Preserve the original summary-plus-recent-session-item context shape."""

    session_store: SessionStorePort
    options: BasicSessionContextOptions = field(default_factory=BasicSessionContextOptions)
    source_id: str = SESSION_CONTEXT_SOURCE_ID
    category: AgentContextSourceCategory = AgentContextSourceCategory.SESSION
    scope: AgentContextSourceScope = AgentContextSourceScope.SESSION

    async def build(self, request: AgentContextBuildRequest) -> AgentContextSourceResult:
        if request.run.session_id is None:
            return AgentContextSourceResult(
                source_id=self.source_id,
                category=self.category,
                scope=self.scope,
                provenance=(
                    AgentContextProvenance(
                        source_id=self.source_id,
                        category=self.category,
                        scope=self.scope,
                        item_count=0,
                        metadata={"reason": "run_has_no_session"},
                    ),
                ),
            )

        summary = await self.session_store.get_latest_summary(request.run.session_id)
        items = await self.session_store.list_items(request.run.session_id)
        prior_items = self._prior_message_items(items=items, current_input=request.turn.input_text)

        messages: list[ChatMessage] = []
        covered_by_summary = 0
        summary_included = False
        if summary is not None and summary.status.value == "completed" and summary.summary_text.strip():
            messages.append(
                ChatMessage(
                    role="system",
                    content=(
                        "Conversation summary for older turns. Treat this as historical context, "
                        "not as fresh evidence unless confirmed by tool results in this turn.\n"
                        f"{summary.summary_text.strip()}"
                    ),
                )
            )
            before_filter_count = len(prior_items)
            prior_items = [
                item for item in prior_items if item.sequence_no > summary.coverage_end_sequence
            ]
            covered_by_summary = before_filter_count - len(prior_items)
            summary_included = True

        recent_items = prior_items[-self.options.recent_item_limit :]
        for item in recent_items:
            if item.item_type == SessionItemType.USER_MESSAGE:
                text = item.payload.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(ChatMessage(role="user", content=text))
            elif item.item_type == SessionItemType.ASSISTANT_MESSAGE:
                text = item.payload.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(ChatMessage(role="assistant", content=text))
            elif item.item_type == SessionItemType.TOOL_RESULT:
                result_payload = item.payload.get("result")
                if isinstance(result_payload, dict):
                    messages.append(
                        ChatMessage(
                            role="system",
                            content=(
                                "Recent tool result context from this session. Reuse any entity refs, "
                                "versions, and bounded tool evidence it contains when relevant.\n"
                                f"{json.dumps(result_payload, separators=(',', ':'), sort_keys=True)}"
                            ),
                        )
                    )

        return AgentContextSourceResult(
            source_id=self.source_id,
            category=self.category,
            scope=self.scope,
            messages=tuple(messages),
            provenance=(
                AgentContextProvenance(
                    source_id=self.source_id,
                    category=self.category,
                    scope=self.scope,
                    item_count=len(messages),
                    metadata={
                        "session_id": request.run.session_id,
                        "summary_included": summary_included,
                        "summary_covered_item_count": covered_by_summary,
                        "recent_item_limit": self.options.recent_item_limit,
                        "eligible_recent_item_count": len(recent_items),
                    },
                ),
            ),
        )

    @staticmethod
    def _prior_message_items(*, items: list[SessionItem], current_input: str) -> list[SessionItem]:
        message_items = [
            item
            for item in items
            if item.item_type
            in {
                SessionItemType.USER_MESSAGE,
                SessionItemType.ASSISTANT_MESSAGE,
                SessionItemType.TOOL_RESULT,
            }
        ]
        if not message_items:
            return []

        latest = message_items[-1]
        latest_text = latest.payload.get("text")
        if (
            latest.item_type == SessionItemType.USER_MESSAGE
            and isinstance(latest_text, str)
            and latest_text == current_input
        ):
            return message_items[:-1]
        return message_items


@dataclass(frozen=True, slots=True)
class FutureConversationRetrievalQuery:
    """Consumer-side query contract for future retrieval implementations."""

    run_id: str
    turn_id: str
    session_id: str | None
    actor_id: str | None
    org_id: str | None
    agent_profile_name: str
    input_text: str
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RankedContextBlock:
    """Ranked retrieval output accepted by the future retrieval source port."""

    block_id: str
    text: str
    rank: int
    score: float | None = None
    ref: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class FutureConversationRetrievalPort(Protocol):
    """Future retrieval seam with no vector/index/chunking commitment."""

    async def retrieve(
        self, query: FutureConversationRetrievalQuery
    ) -> tuple[RankedContextBlock, ...]: ...


@dataclass(slots=True)
class RetrievalContextSource:
    """Adapter from future ranked context blocks to model-visible messages."""

    retrieval: FutureConversationRetrievalPort
    source_id: str = "conversation-retrieval"
    category: AgentContextSourceCategory = AgentContextSourceCategory.RETRIEVAL
    scope: AgentContextSourceScope = AgentContextSourceScope.ACTOR

    async def build(self, request: AgentContextBuildRequest) -> AgentContextSourceResult:
        blocks = await self.retrieval.retrieve(
            FutureConversationRetrievalQuery(
                run_id=request.run.run_id,
                turn_id=request.turn.turn_id,
                session_id=request.run.session_id,
                actor_id=request.run.actor_id,
                org_id=request.run.org_id,
                agent_profile_name=request.run.profile_name,
                input_text=request.turn.input_text,
                permissions=request.run.permissions,
            )
        )
        ordered = sorted(blocks, key=lambda item: item.rank)
        messages = tuple(
            ChatMessage(
                role="system",
                content=(
                    "Retrieved conversation context. Treat this as potentially relevant historical "
                    f"context, not as fresh evidence.\n{block.text.strip()}"
                ),
            )
            for block in ordered
            if block.text.strip()
        )
        return AgentContextSourceResult(
            source_id=self.source_id,
            category=self.category,
            scope=self.scope,
            messages=messages,
            provenance=(
                AgentContextProvenance(
                    source_id=self.source_id,
                    category=self.category,
                    scope=self.scope,
                    item_count=len(messages),
                    metadata={
                        "block_refs": [
                            {"block_id": block.block_id, "rank": block.rank, "ref": block.ref}
                            for block in ordered
                        ],
                    },
                ),
            ),
        )


@dataclass(slots=True)
class FakeAgentContextSource:
    """Deterministic fake/no-op source for unit and integration tests."""

    source_id: str
    category: AgentContextSourceCategory
    scope: AgentContextSourceScope
    messages: tuple[ChatMessage, ...] = ()
    fail_with: AppError | None = None

    async def build(self, request: AgentContextBuildRequest) -> AgentContextSourceResult:
        del request
        if self.fail_with is not None:
            raise self.fail_with
        return AgentContextSourceResult(
            source_id=self.source_id,
            category=self.category,
            scope=self.scope,
            messages=self.messages,
            provenance=(
                AgentContextProvenance(
                    source_id=self.source_id,
                    category=self.category,
                    scope=self.scope,
                    item_count=len(self.messages),
                    metadata={"fake": True},
                ),
            ),
        )


@dataclass(slots=True)
class FakeLongTermMemoryContextSource(FakeAgentContextSource):
    """Fake semantic-memory source used to prove profile-level memory switching."""

    def __init__(
        self,
        *,
        source_id: str = "fake-long-term-memory",
        messages: tuple[ChatMessage, ...] = (),
        fail_with: AppError | None = None,
    ) -> None:
        self.source_id = source_id
        self.category = AgentContextSourceCategory.SEMANTIC_MEMORY
        self.scope = AgentContextSourceScope.ACTOR
        self.messages = messages
        self.fail_with = fail_with


def basic_session_context_profile(
    *,
    profile_id: str = BASIC_CONTEXT_PROFILE_ID,
    recent_item_limit: int = 16,
) -> AgentContextProfile:
    """Return the default behavior-preserving session context profile."""

    return AgentContextProfile(
        profile_id=profile_id,
        version="v1",
        description="Session summary plus recent session items.",
        sources=(
            AgentContextSourceRef(
                source_id=SESSION_CONTEXT_SOURCE_ID,
                category=AgentContextSourceCategory.SESSION,
                scope=AgentContextSourceScope.SESSION,
                failure_policy=AgentContextFailurePolicy.REQUIRED,
            ),
        ),
        parameters={"recent_item_limit": recent_item_limit},
    )


def build_basic_context_assembler(
    session_store: SessionStorePort | None,
    *,
    profile_id: str = BASIC_CONTEXT_PROFILE_ID,
    recent_item_limit: int = 16,
) -> ProfiledAgentContextAssembler:
    """Build the default assembler used by the composed generic runtime."""

    sources: dict[str, AgentContextSource] = {}
    profile = basic_session_context_profile(
        profile_id=profile_id,
        recent_item_limit=recent_item_limit,
    )
    if session_store is not None:
        sources[SESSION_CONTEXT_SOURCE_ID] = BasicSessionContextSource(
            session_store=session_store,
            options=BasicSessionContextOptions(recent_item_limit=recent_item_limit),
        )
    else:
        profile = AgentContextProfile(
            profile_id=profile.profile_id,
            version=profile.version,
            description=profile.description,
            sources=(),
            budget=profile.budget,
            parameters=profile.parameters,
        )
    return ProfiledAgentContextAssembler(
        profiles={profile_id: profile},
        sources=sources,
    )
