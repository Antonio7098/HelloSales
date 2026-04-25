"""In-memory agent persistence for sqlite-backed tests and local scaffolding."""

from __future__ import annotations

from dataclasses import replace

from hello_sales_backend.platform.agents.models import (
    AgentArtifact,
    AgentDiagnosticsSummary,
    AgentRun,
    AgentRunStatus,
    AgentStreamEvent,
    AgentToolCall,
    AgentTurn,
)


class InMemoryAgentStore:
    """Small in-memory store for generic-agent operational state."""

    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}
        self._turns: dict[str, AgentTurn] = {}
        self._tool_calls: dict[str, AgentToolCall] = {}
        self._artifacts: dict[str, AgentArtifact] = {}
        self._events: dict[str, AgentStreamEvent] = {}

    async def create_run(self, run: AgentRun) -> None:
        self._runs[run.run_id] = replace(run)

    async def get_run(self, run_id: str) -> AgentRun | None:
        run = self._runs.get(run_id)
        return None if run is None else replace(run)

    async def update_run(self, run: AgentRun) -> None:
        self._runs[run.run_id] = replace(run)

    async def create_turn(self, turn: AgentTurn) -> None:
        self._turns[turn.turn_id] = replace(turn)

    async def get_turn(self, turn_id: str) -> AgentTurn | None:
        turn = self._turns.get(turn_id)
        return None if turn is None else replace(turn)

    async def list_turns(self, run_id: str) -> list[AgentTurn]:
        turns = [item for item in self._turns.values() if item.run_id == run_id]
        return [replace(item) for item in sorted(turns, key=lambda item: item.sequence_no)]

    async def update_turn(self, turn: AgentTurn) -> None:
        self._turns[turn.turn_id] = replace(turn)

    async def create_tool_call(self, tool_call: AgentToolCall) -> None:
        self._tool_calls[tool_call.tool_call_id] = replace(tool_call)

    async def list_tool_calls(self, run_id: str, turn_id: str) -> list[AgentToolCall]:
        matches = [
            item
            for item in self._tool_calls.values()
            if item.run_id == run_id and item.turn_id == turn_id
        ]
        return [replace(item) for item in sorted(matches, key=lambda item: item.sequence_no)]

    async def get_tool_call_by_approval_id(self, approval_id: str) -> AgentToolCall | None:
        for tool_call in self._tool_calls.values():
            if tool_call.approval_id == approval_id:
                return replace(tool_call)
        return None

    async def update_tool_call(self, tool_call: AgentToolCall) -> None:
        self._tool_calls[tool_call.tool_call_id] = replace(tool_call)

    async def create_artifact(self, artifact: AgentArtifact) -> None:
        self._artifacts[artifact.artifact_id] = replace(artifact)

    async def append_event(self, event: AgentStreamEvent) -> None:
        self._events[event.event_id] = replace(event)

    async def list_events(self, run_id: str, limit: int = 100) -> list[AgentStreamEvent]:
        matches = [item for item in self._events.values() if item.run_id == run_id]
        ordered = sorted(matches, key=lambda item: item.sequence_no)
        return [replace(item) for item in ordered[-limit:]]

    async def list_events_after(
        self,
        run_id: str,
        *,
        after_sequence: int,
        limit: int = 100,
    ) -> list[AgentStreamEvent]:
        matches = [
            item
            for item in self._events.values()
            if item.run_id == run_id and item.sequence_no > after_sequence
        ]
        ordered = sorted(matches, key=lambda item: item.sequence_no)
        return [replace(item) for item in ordered[:limit]]

    async def next_turn_sequence(self, run_id: str) -> int:
        current = max((item.sequence_no for item in self._turns.values() if item.run_id == run_id), default=0)
        return current + 1

    async def next_tool_sequence(self, run_id: str, turn_id: str) -> int:
        current = max(
            (
                item.sequence_no
                for item in self._tool_calls.values()
                if item.run_id == run_id and item.turn_id == turn_id
            ),
            default=0,
        )
        return current + 1

    async def next_event_sequence(self, run_id: str) -> int:
        current = max((item.sequence_no for item in self._events.values() if item.run_id == run_id), default=0)
        return current + 1

    async def summarize(self, limit: int = 10) -> AgentDiagnosticsSummary:
        ordered = sorted(self._runs.values(), key=lambda item: item.created_at, reverse=True)
        return AgentDiagnosticsSummary(
            active_count=sum(1 for item in self._runs.values() if item.status == AgentRunStatus.RUNNING),
            awaiting_approval_count=sum(
                1 for item in self._runs.values() if item.status == AgentRunStatus.AWAITING_APPROVAL
            ),
            total_count=len(self._runs),
            recent_runs=[replace(item) for item in ordered[:limit]],
        )
