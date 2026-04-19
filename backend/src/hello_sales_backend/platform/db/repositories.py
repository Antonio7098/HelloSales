"""Operational repository adapters."""

from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hello_sales_backend.platform.agents.models import (
    AgentArtifact,
    AgentDiagnosticsSummary,
    AgentRun,
    AgentRunStatus,
    AgentStreamEvent,
    AgentToolCall,
    AgentToolCallStatus,
    AgentTurn,
    AgentTurnStatus,
)
from hello_sales_backend.platform.db.models import (
    AgentArtifactRecord,
    AgentRunRecord,
    AgentStreamEventRecord,
    AgentToolCallRecord,
    AgentTurnRecord,
    TaskRunRecord,
)
from hello_sales_backend.platform.llm import EffectivePromptRef
from hello_sales_backend.platform.tasks.models import TaskSnapshot


class SqlAlchemyTaskRunStore:
    """Persist background task snapshots."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert(self, snapshot: TaskSnapshot) -> None:
        async with self._session_factory() as session:
            record = await session.get(TaskRunRecord, snapshot.metadata.task_id)
            if record is None:
                record = TaskRunRecord(
                    task_id=snapshot.metadata.task_id,
                    purpose=snapshot.metadata.purpose,
                    status=snapshot.status.value,
                    request_id=snapshot.metadata.request_id,
                    trace_id=snapshot.metadata.trace_id,
                    actor_id=snapshot.metadata.actor_id,
                    error_type=snapshot.error_type,
                    error_message=snapshot.error_message,
                    error_code=snapshot.error_code,
                    error_category=snapshot.error_category,
                    created_at=snapshot.created_at,
                    started_at=snapshot.started_at,
                    finished_at=snapshot.finished_at,
                )
                record.set_error_details(snapshot.error_details)
                session.add(record)
            else:
                record.purpose = snapshot.metadata.purpose
                record.status = snapshot.status.value
                record.request_id = snapshot.metadata.request_id
                record.trace_id = snapshot.metadata.trace_id
                record.actor_id = snapshot.metadata.actor_id
                record.error_type = snapshot.error_type
                record.error_message = snapshot.error_message
                record.error_code = snapshot.error_code
                record.error_category = snapshot.error_category
                record.set_error_details(snapshot.error_details)
                record.started_at = snapshot.started_at
                record.finished_at = snapshot.finished_at
            await session.commit()

    async def list_recent(self, limit: int = 20) -> list[TaskRunRecord]:
        async with self._session_factory() as session:
            result = await session.execute(select(TaskRunRecord).order_by(TaskRunRecord.created_at.desc()).limit(limit))
            return list(result.scalars())


def _load_json(payload: str | None) -> dict[str, object] | None:
    if payload is None:
        return None
    loaded = json.loads(payload)
    return loaded if isinstance(loaded, dict) else None


def _prompt_kwargs(prompt: EffectivePromptRef | None) -> dict[str, object]:
    return {
        "prompt_id": None if prompt is None else prompt.prompt_id,
        "prompt_version": None if prompt is None else prompt.version,
        "prompt_owner_kind": None if prompt is None else prompt.owner_kind,
        "prompt_owner_id": None if prompt is None else prompt.owner_id,
        "prompt_purpose": None if prompt is None else prompt.purpose,
        "prompt_checksum": None if prompt is None else prompt.checksum,
    }


def _map_prompt(
    *,
    prompt_id: str | None,
    prompt_version: str | None,
    prompt_owner_kind: str | None,
    prompt_owner_id: str | None,
    prompt_purpose: str | None,
    prompt_checksum: str | None,
) -> EffectivePromptRef | None:
    if (
        prompt_id is None
        or prompt_version is None
        or prompt_owner_kind is None
        or prompt_owner_id is None
        or prompt_purpose is None
    ):
        return None
    return EffectivePromptRef(
        prompt_id=prompt_id,
        version=prompt_version,
        owner_kind=prompt_owner_kind,  # type: ignore[arg-type]
        owner_id=prompt_owner_id,
        purpose=prompt_purpose,
        checksum=prompt_checksum,
    )


class SqlAlchemyAgentStore:
    """Persist generic-agent run state."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_run(self, run: AgentRun) -> None:
        async with self._session_factory() as session:
            record = AgentRunRecord(
                run_id=run.run_id,
                profile_name=run.profile_name,
                status=run.status.value,
                request_id=run.request_id,
                trace_id=run.trace_id,
                actor_id=run.actor_id,
                **_prompt_kwargs(run.prompt),
                latest_turn_id=run.latest_turn_id,
                error_code=run.error_code,
                error_category=run.error_category,
                error_message=run.error_message,
                created_at=run.created_at,
                updated_at=run.updated_at,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
            record.set_error_details(run.error_details)
            session.add(record)
            await session.commit()

    async def get_run(self, run_id: str) -> AgentRun | None:
        async with self._session_factory() as session:
            record = await session.get(AgentRunRecord, run_id)
            return None if record is None else self._map_run(record)

    async def update_run(self, run: AgentRun) -> None:
        async with self._session_factory() as session:
            record = await session.get(AgentRunRecord, run.run_id)
            if record is None:
                return
            record.profile_name = run.profile_name
            record.status = run.status.value
            record.request_id = run.request_id
            record.trace_id = run.trace_id
            record.actor_id = run.actor_id
            record.prompt_id = run.prompt.prompt_id if run.prompt else None
            record.prompt_version = run.prompt.version if run.prompt else None
            record.prompt_owner_kind = run.prompt.owner_kind if run.prompt else None
            record.prompt_owner_id = run.prompt.owner_id if run.prompt else None
            record.prompt_purpose = run.prompt.purpose if run.prompt else None
            record.prompt_checksum = run.prompt.checksum if run.prompt else None
            record.latest_turn_id = run.latest_turn_id
            record.error_code = run.error_code
            record.error_category = run.error_category
            record.error_message = run.error_message
            record.set_error_details(run.error_details)
            record.updated_at = run.updated_at
            record.started_at = run.started_at
            record.completed_at = run.completed_at
            await session.commit()

    async def create_turn(self, turn: AgentTurn) -> None:
        async with self._session_factory() as session:
            record = AgentTurnRecord(
                turn_id=turn.turn_id,
                run_id=turn.run_id,
                sequence_no=turn.sequence_no,
                input_text=turn.input_text,
                status=turn.status.value,
                **_prompt_kwargs(turn.prompt),
                response_text=turn.response_text,
                error_code=turn.error_code,
                error_category=turn.error_category,
                error_message=turn.error_message,
                created_at=turn.created_at,
                started_at=turn.started_at,
                completed_at=turn.completed_at,
            )
            record.set_error_details(turn.error_details)
            session.add(record)
            await session.commit()

    async def get_turn(self, turn_id: str) -> AgentTurn | None:
        async with self._session_factory() as session:
            record = await session.get(AgentTurnRecord, turn_id)
            return None if record is None else self._map_turn(record)

    async def list_turns(self, run_id: str) -> list[AgentTurn]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentTurnRecord)
                .where(AgentTurnRecord.run_id == run_id)
                .order_by(AgentTurnRecord.sequence_no.asc())
            )
            return [self._map_turn(item) for item in result.scalars()]

    async def update_turn(self, turn: AgentTurn) -> None:
        async with self._session_factory() as session:
            record = await session.get(AgentTurnRecord, turn.turn_id)
            if record is None:
                return
            record.status = turn.status.value
            record.prompt_id = turn.prompt.prompt_id if turn.prompt else None
            record.prompt_version = turn.prompt.version if turn.prompt else None
            record.prompt_owner_kind = turn.prompt.owner_kind if turn.prompt else None
            record.prompt_owner_id = turn.prompt.owner_id if turn.prompt else None
            record.prompt_purpose = turn.prompt.purpose if turn.prompt else None
            record.prompt_checksum = turn.prompt.checksum if turn.prompt else None
            record.response_text = turn.response_text
            record.error_code = turn.error_code
            record.error_category = turn.error_category
            record.error_message = turn.error_message
            record.set_error_details(turn.error_details)
            record.started_at = turn.started_at
            record.completed_at = turn.completed_at
            await session.commit()

    async def create_tool_call(self, tool_call: AgentToolCall) -> None:
        async with self._session_factory() as session:
            record = AgentToolCallRecord(
                tool_call_id=tool_call.tool_call_id,
                run_id=tool_call.run_id,
                turn_id=tool_call.turn_id,
                sequence_no=tool_call.sequence_no,
                tool_name=tool_call.tool_name,
                status=tool_call.status.value,
                requires_approval=tool_call.requires_approval,
                approval_id=tool_call.approval_id,
                error_code=tool_call.error_code,
                error_category=tool_call.error_category,
                error_message=tool_call.error_message,
                created_at=tool_call.created_at,
                started_at=tool_call.started_at,
                completed_at=tool_call.completed_at,
            )
            record.set_arguments(tool_call.arguments)
            record.set_result_payload(tool_call.result_payload)
            record.set_error_details(tool_call.error_details)
            session.add(record)
            await session.commit()

    async def list_tool_calls(self, run_id: str, turn_id: str) -> list[AgentToolCall]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentToolCallRecord)
                .where(AgentToolCallRecord.run_id == run_id, AgentToolCallRecord.turn_id == turn_id)
                .order_by(AgentToolCallRecord.sequence_no.asc())
            )
            return [self._map_tool_call(item) for item in result.scalars()]

    async def get_tool_call_by_approval_id(self, approval_id: str) -> AgentToolCall | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentToolCallRecord).where(AgentToolCallRecord.approval_id == approval_id).limit(1)
            )
            record = result.scalar_one_or_none()
            return None if record is None else self._map_tool_call(record)

    async def update_tool_call(self, tool_call: AgentToolCall) -> None:
        async with self._session_factory() as session:
            record = await session.get(AgentToolCallRecord, tool_call.tool_call_id)
            if record is None:
                return
            record.status = tool_call.status.value
            record.requires_approval = tool_call.requires_approval
            record.approval_id = tool_call.approval_id
            record.error_code = tool_call.error_code
            record.error_category = tool_call.error_category
            record.error_message = tool_call.error_message
            record.started_at = tool_call.started_at
            record.completed_at = tool_call.completed_at
            record.set_arguments(tool_call.arguments)
            record.set_result_payload(tool_call.result_payload)
            record.set_error_details(tool_call.error_details)
            await session.commit()

    async def create_artifact(self, artifact: AgentArtifact) -> None:
        async with self._session_factory() as session:
            record = AgentArtifactRecord(
                artifact_id=artifact.artifact_id,
                run_id=artifact.run_id,
                turn_id=artifact.turn_id,
                artifact_type=artifact.artifact_type,
                created_at=artifact.created_at,
            )
            record.set_payload(artifact.payload)
            session.add(record)
            await session.commit()

    async def append_event(self, event: AgentStreamEvent) -> None:
        async with self._session_factory() as session:
            record = AgentStreamEventRecord(
                event_id=event.event_id,
                run_id=event.run_id,
                turn_id=event.turn_id,
                sequence_no=event.sequence_no,
                event_type=event.event_type,
                severity=event.severity,
                code=event.code,
                created_at=event.created_at,
            )
            record.set_payload(event.payload)
            session.add(record)
            await session.commit()

    async def list_events(self, run_id: str, limit: int = 100) -> list[AgentStreamEvent]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentStreamEventRecord)
                .where(AgentStreamEventRecord.run_id == run_id)
                .order_by(AgentStreamEventRecord.sequence_no.asc())
                .limit(limit)
            )
            return [self._map_event(item) for item in result.scalars()]

    async def next_turn_sequence(self, run_id: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.max(AgentTurnRecord.sequence_no)).where(AgentTurnRecord.run_id == run_id)
            )
            current = result.scalar_one_or_none()
            return (int(current) if current is not None else 0) + 1

    async def next_tool_sequence(self, run_id: str, turn_id: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.max(AgentToolCallRecord.sequence_no)).where(
                    AgentToolCallRecord.run_id == run_id,
                    AgentToolCallRecord.turn_id == turn_id,
                )
            )
            current = result.scalar_one_or_none()
            return (int(current) if current is not None else 0) + 1

    async def next_event_sequence(self, run_id: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.max(AgentStreamEventRecord.sequence_no)).where(AgentStreamEventRecord.run_id == run_id)
            )
            current = result.scalar_one_or_none()
            return (int(current) if current is not None else 0) + 1

    async def summarize(self, limit: int = 10) -> AgentDiagnosticsSummary:
        async with self._session_factory() as session:
            total_count = await session.scalar(select(func.count()).select_from(AgentRunRecord))
            active_count = await session.scalar(
                select(func.count()).select_from(AgentRunRecord).where(AgentRunRecord.status == AgentRunStatus.RUNNING.value)
            )
            awaiting_count = await session.scalar(
                select(func.count())
                .select_from(AgentRunRecord)
                .where(AgentRunRecord.status == AgentRunStatus.AWAITING_APPROVAL.value)
            )
            recent_result = await session.execute(
                select(AgentRunRecord).order_by(AgentRunRecord.created_at.desc()).limit(limit)
            )
            return AgentDiagnosticsSummary(
                active_count=int(active_count or 0),
                awaiting_approval_count=int(awaiting_count or 0),
                total_count=int(total_count or 0),
                recent_runs=[self._map_run(item) for item in recent_result.scalars()],
            )

    @staticmethod
    def _map_run(record: AgentRunRecord) -> AgentRun:
        return AgentRun(
            run_id=record.run_id,
            profile_name=record.profile_name,
            status=AgentRunStatus(record.status),
            request_id=record.request_id,
            trace_id=record.trace_id,
            actor_id=record.actor_id,
            prompt=_map_prompt(
                prompt_id=record.prompt_id,
                prompt_version=record.prompt_version,
                prompt_owner_kind=record.prompt_owner_kind,
                prompt_owner_id=record.prompt_owner_id,
                prompt_purpose=record.prompt_purpose,
                prompt_checksum=record.prompt_checksum,
            ),
            created_at=record.created_at,
            updated_at=record.updated_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            latest_turn_id=record.latest_turn_id,
            error_code=record.error_code,
            error_category=record.error_category,
            error_message=record.error_message,
            error_details=_load_json(record.error_details),
        )

    @staticmethod
    def _map_turn(record: AgentTurnRecord) -> AgentTurn:
        return AgentTurn(
            turn_id=record.turn_id,
            run_id=record.run_id,
            sequence_no=record.sequence_no,
            input_text=record.input_text,
            status=AgentTurnStatus(record.status),
            prompt=_map_prompt(
                prompt_id=record.prompt_id,
                prompt_version=record.prompt_version,
                prompt_owner_kind=record.prompt_owner_kind,
                prompt_owner_id=record.prompt_owner_id,
                prompt_purpose=record.prompt_purpose,
                prompt_checksum=record.prompt_checksum,
            ),
            created_at=record.created_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            response_text=record.response_text,
            error_code=record.error_code,
            error_category=record.error_category,
            error_message=record.error_message,
            error_details=_load_json(record.error_details),
        )

    @staticmethod
    def _map_tool_call(record: AgentToolCallRecord) -> AgentToolCall:
        return AgentToolCall(
            tool_call_id=record.tool_call_id,
            run_id=record.run_id,
            turn_id=record.turn_id,
            sequence_no=record.sequence_no,
            tool_name=record.tool_name,
            status=AgentToolCallStatus(record.status),
            arguments=_load_json(record.arguments_json) or {},
            requires_approval=record.requires_approval,
            approval_id=record.approval_id,
            created_at=record.created_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            result_payload=_load_json(record.result_payload_json),
            error_code=record.error_code,
            error_category=record.error_category,
            error_message=record.error_message,
            error_details=_load_json(record.error_details),
        )

    @staticmethod
    def _map_event(record: AgentStreamEventRecord) -> AgentStreamEvent:
        return AgentStreamEvent(
            event_id=record.event_id,
            run_id=record.run_id,
            turn_id=record.turn_id,
            sequence_no=record.sequence_no,
            event_type=record.event_type,
            severity=record.severity,
            code=record.code,
            payload=_load_json(record.payload_json) or {},
            created_at=record.created_at,
        )
