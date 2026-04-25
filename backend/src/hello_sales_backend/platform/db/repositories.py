"""Operational repository adapters."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
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
    SessionItemRecord,
    SessionRecord,
    SessionSummaryRecord,
    TaskRunRecord,
)
from hello_sales_backend.platform.llm import EffectivePromptRef
from hello_sales_backend.platform.sessions.models import (
    Session,
    SessionItem,
    SessionItemType,
    SessionStatus,
    SessionSummary,
    SessionSummaryStatus,
)
from hello_sales_backend.platform.tasks.models import TaskSnapshot
from hello_sales_backend.shared.errors import app_error


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


def _load_string_list(payload: str | None) -> tuple[str, ...]:
    if payload is None:
        return ()
    loaded = json.loads(payload)
    if not isinstance(loaded, list):
        return ()
    return tuple(str(item) for item in loaded)


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

    @staticmethod
    def _tool_call_data_error(
        *,
        action: str,
        tool_call_id: str,
        run_id: str,
        turn_id: str,
        tool_name: str,
        exc: SQLAlchemyError,
    ) -> Exception:
        return app_error(
            "Failed to persist agent tool call state",
            code=f"data.agent_tool_call.{action}_failed",
            category="data",
            status_code=500,
            details={
                "tool_call_id": tool_call_id,
                "run_id": run_id,
                "turn_id": turn_id,
                "tool_name": tool_name,
            },
            operation=f"agent.tool.{action}_state",
            component="data",
            exc=exc,
        )

    async def create_run(self, run: AgentRun) -> None:
        async with self._session_factory() as session:
            record = AgentRunRecord(
                run_id=run.run_id,
                profile_name=run.profile_name,
                status=run.status.value,
                request_id=run.request_id,
                trace_id=run.trace_id,
                actor_id=run.actor_id,
                org_id=run.org_id,
                session_id=run.session_id,
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
            record.permissions_json = json.dumps(list(run.permissions), sort_keys=True)
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
            record.org_id = run.org_id
            record.permissions_json = json.dumps(list(run.permissions), sort_keys=True)
            record.session_id = run.session_id
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
        try:
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
        except SQLAlchemyError as exc:
            raise self._tool_call_data_error(
                action="create",
                tool_call_id=tool_call.tool_call_id,
                run_id=tool_call.run_id,
                turn_id=tool_call.turn_id,
                tool_name=tool_call.tool_name,
                exc=exc,
            ) from exc

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
        try:
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
        except SQLAlchemyError as exc:
            raise self._tool_call_data_error(
                action="update",
                tool_call_id=tool_call.tool_call_id,
                run_id=tool_call.run_id,
                turn_id=tool_call.turn_id,
                tool_name=tool_call.tool_name,
                exc=exc,
            ) from exc

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
                .order_by(AgentStreamEventRecord.sequence_no.desc())
                .limit(limit)
            )
            records = list(result.scalars())
            records.reverse()
            return [self._map_event(item) for item in records]

    async def list_events_after(
        self,
        run_id: str,
        *,
        after_sequence: int,
        limit: int = 100,
    ) -> list[AgentStreamEvent]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(AgentStreamEventRecord)
                .where(
                    AgentStreamEventRecord.run_id == run_id,
                    AgentStreamEventRecord.sequence_no > after_sequence,
                )
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
            org_id=record.org_id,
            permissions=_load_string_list(record.permissions_json),
            session_id=record.session_id,
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


class SqlAlchemySessionStore:
    """Persist neutral session state and chronology."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_session(self, session: Session) -> None:
        async with self._session_factory() as db:
            db.add(
                SessionRecord(
                    session_id=session.session_id,
                    status=session.status.value,
                    profile_name=session.profile_name,
                    actor_id=session.actor_id,
                    user_id=session.user_id,
                    org_id=session.org_id,
                    request_id=session.request_id,
                    trace_id=session.trace_id,
                    latest_item_id=session.latest_item_id,
                    latest_run_id=session.latest_run_id,
                    summary_task_id=session.summary_task_id,
                    summary_status=session.summary_status,
                    last_summarized_item_sequence=session.last_summarized_item_sequence,
                    error_code=session.error_code,
                    error_category=session.error_category,
                    error_message=session.error_message,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    completed_at=session.completed_at,
                )
            )
            await db.commit()

    async def get_session(self, session_id: str) -> Session | None:
        async with self._session_factory() as db:
            record = await db.get(SessionRecord, session_id)
            return None if record is None else self._map_session(record)

    async def update_session(self, session: Session) -> None:
        async with self._session_factory() as db:
            record = await db.get(SessionRecord, session.session_id)
            if record is None:
                return
            record.status = session.status.value
            record.profile_name = session.profile_name
            record.actor_id = session.actor_id
            record.user_id = session.user_id
            record.org_id = session.org_id
            record.request_id = session.request_id
            record.trace_id = session.trace_id
            record.latest_item_id = session.latest_item_id
            record.latest_run_id = session.latest_run_id
            record.summary_task_id = session.summary_task_id
            record.summary_status = session.summary_status
            record.last_summarized_item_sequence = session.last_summarized_item_sequence
            record.error_code = session.error_code
            record.error_category = session.error_category
            record.error_message = session.error_message
            record.updated_at = session.updated_at
            record.completed_at = session.completed_at
            await db.commit()

    async def update_session_summary_state(
        self,
        *,
        session_id: str,
        summary_task_id: str | None,
        summary_status: str | None,
        last_summarized_item_sequence: int | None,
        updated_at: datetime,
    ) -> None:
        async with self._session_factory() as db:
            record = await db.get(SessionRecord, session_id)
            if record is None:
                return
            record.summary_task_id = summary_task_id
            record.summary_status = summary_status
            if last_summarized_item_sequence is not None:
                record.last_summarized_item_sequence = last_summarized_item_sequence
            record.updated_at = updated_at
            await db.commit()

    async def list_sessions(self, *, limit: int = 50) -> list[Session]:
        async with self._session_factory() as db:
            result = await db.execute(select(SessionRecord).order_by(SessionRecord.created_at.desc()).limit(limit))
            return [self._map_session(item) for item in result.scalars()]

    async def create_item(self, item: SessionItem) -> None:
        async with self._session_factory() as db:
            record = SessionItemRecord(
                item_id=item.item_id,
                session_id=item.session_id,
                sequence_no=item.sequence_no,
                item_type=item.item_type.value,
                actor_id=item.actor_id,
                run_id=item.run_id,
                turn_id=item.turn_id,
                tool_call_id=item.tool_call_id,
                **_prompt_kwargs(item.prompt),
                created_at=item.created_at,
            )
            record.set_payload(item.payload)
            db.add(record)
            await db.commit()

    async def list_items(self, session_id: str, *, limit: int = 500) -> list[SessionItem]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionItemRecord)
                .where(SessionItemRecord.session_id == session_id)
                .order_by(SessionItemRecord.sequence_no.asc())
                .limit(limit)
            )
            return [self._map_item(item) for item in result.scalars()]

    async def next_item_sequence(self, session_id: str) -> int:
        async with self._session_factory() as db:
            result = await db.execute(
                select(func.max(SessionItemRecord.sequence_no)).where(SessionItemRecord.session_id == session_id)
            )
            current = result.scalar_one_or_none()
            return (int(current) if current is not None else 0) + 1

    async def upsert_summary(self, summary: SessionSummary) -> None:
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionSummaryRecord).where(SessionSummaryRecord.session_id == summary.session_id).limit(1)
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = SessionSummaryRecord(
                    summary_id=summary.summary_id,
                    session_id=summary.session_id,
                    coverage_start_sequence=summary.coverage_start_sequence,
                    coverage_end_sequence=summary.coverage_end_sequence,
                    summary_text=summary.summary_text,
                    status=summary.status.value,
                    task_id=summary.task_id,
                    provider_name=summary.provider_name,
                    model_name=summary.model_name,
                    prompt_id=summary.prompt.prompt_id,
                    prompt_version=summary.prompt.version,
                    prompt_owner_kind=summary.prompt.owner_kind,
                    prompt_owner_id=summary.prompt.owner_id,
                    prompt_purpose=summary.prompt.purpose,
                    prompt_checksum=summary.prompt.checksum,
                    error_code=summary.error_code,
                    error_category=summary.error_category,
                    error_message=summary.error_message,
                    created_at=summary.created_at,
                    updated_at=summary.updated_at,
                    completed_at=summary.completed_at,
                )
                db.add(record)
            else:
                record.summary_id = summary.summary_id
                record.coverage_start_sequence = summary.coverage_start_sequence
                record.coverage_end_sequence = summary.coverage_end_sequence
                record.summary_text = summary.summary_text
                record.status = summary.status.value
                record.task_id = summary.task_id
                record.provider_name = summary.provider_name
                record.model_name = summary.model_name
                record.prompt_id = summary.prompt.prompt_id
                record.prompt_version = summary.prompt.version
                record.prompt_owner_kind = summary.prompt.owner_kind
                record.prompt_owner_id = summary.prompt.owner_id
                record.prompt_purpose = summary.prompt.purpose
                record.prompt_checksum = summary.prompt.checksum
                record.error_code = summary.error_code
                record.error_category = summary.error_category
                record.error_message = summary.error_message
                record.updated_at = summary.updated_at
                record.completed_at = summary.completed_at
            await db.commit()

    async def get_latest_summary(self, session_id: str) -> SessionSummary | None:
        async with self._session_factory() as db:
            result = await db.execute(
                select(SessionSummaryRecord).where(SessionSummaryRecord.session_id == session_id).limit(1)
            )
            record = result.scalar_one_or_none()
            return None if record is None else self._map_summary(record)

    @staticmethod
    def _map_session(record: SessionRecord) -> Session:
        return Session(
            session_id=record.session_id,
            status=SessionStatus(record.status),
            profile_name=record.profile_name,
            actor_id=record.actor_id,
            user_id=record.user_id,
            org_id=record.org_id,
            request_id=record.request_id,
            trace_id=record.trace_id,
            latest_item_id=record.latest_item_id,
            latest_run_id=record.latest_run_id,
            summary_task_id=record.summary_task_id,
            summary_status=record.summary_status,
            last_summarized_item_sequence=record.last_summarized_item_sequence,
            created_at=record.created_at,
            updated_at=record.updated_at,
            completed_at=record.completed_at,
            error_code=record.error_code,
            error_category=record.error_category,
            error_message=record.error_message,
        )

    @staticmethod
    def _map_item(record: SessionItemRecord) -> SessionItem:
        return SessionItem(
            item_id=record.item_id,
            session_id=record.session_id,
            sequence_no=record.sequence_no,
            item_type=SessionItemType(record.item_type),
            payload=_load_json(record.payload_json) or {},
            actor_id=record.actor_id,
            run_id=record.run_id,
            turn_id=record.turn_id,
            tool_call_id=record.tool_call_id,
            prompt=_map_prompt(
                prompt_id=record.prompt_id,
                prompt_version=record.prompt_version,
                prompt_owner_kind=record.prompt_owner_kind,
                prompt_owner_id=record.prompt_owner_id,
                prompt_purpose=record.prompt_purpose,
                prompt_checksum=record.prompt_checksum,
            ),
            created_at=record.created_at,
        )

    @staticmethod
    def _map_summary(record: SessionSummaryRecord) -> SessionSummary:
        return SessionSummary(
            summary_id=record.summary_id,
            session_id=record.session_id,
            coverage_start_sequence=record.coverage_start_sequence,
            coverage_end_sequence=record.coverage_end_sequence,
            summary_text=record.summary_text,
            prompt=EffectivePromptRef(
                prompt_id=record.prompt_id,
                version=record.prompt_version,
                owner_kind=record.prompt_owner_kind,  # type: ignore[arg-type]
                owner_id=record.prompt_owner_id,
                purpose=record.prompt_purpose,
                checksum=record.prompt_checksum,
            ),
            status=SessionSummaryStatus(record.status),
            task_id=record.task_id,
            provider_name=record.provider_name,
            model_name=record.model_name,
            error_code=record.error_code,
            error_category=record.error_category,
            error_message=record.error_message,
            created_at=record.created_at,
            updated_at=record.updated_at,
            completed_at=record.completed_at,
        )
