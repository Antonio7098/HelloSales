"""Session application service."""

from __future__ import annotations

from collections.abc import AsyncIterator

from hello_sales_backend.modules.agent_runs import AgentRunService
from hello_sales_backend.modules.agent_runs.use_cases.commands import (
    AppendAgentTurnCommand,
    ApprovalDecisionCommand,
    StartAgentRunCommand,
)
from hello_sales_backend.modules.agent_runs.use_cases.views import (
    AgentApprovalView,
    AgentEventView,
)
from hello_sales_backend.modules.sessions.use_cases.commands import (
    AppendSessionMessageCommand,
    CreateSessionCommand,
)
from hello_sales_backend.modules.sessions.use_cases.views import (
    SessionDetailView,
    SessionItemView,
    SessionSummaryStateView,
    SessionSummaryView,
)
from hello_sales_backend.platform.sessions.models import (
    Session,
    SessionItem,
    SessionItemType,
    SessionStatus,
    SessionSummary,
    utc_now,
)
from hello_sales_backend.platform.sessions.persistence import SessionStorePort
from hello_sales_backend.shared.auth import (
    SESSIONS_READ_ANY_PERMISSION,
    SESSIONS_WRITE_ANY_PERMISSION,
    AuthContext,
)
from hello_sales_backend.shared.errors import app_error
from hello_sales_backend.shared.ids import new_id


class SessionService:
    """Expose session-first conversational actions through a stable facade."""

    def __init__(
        self,
        *,
        store: SessionStorePort,
        agent_runs: AgentRunService,
    ) -> None:
        self._store = store
        self._agent_runs = agent_runs

    async def create_session(
        self,
        *,
        request_id: str | None,
        trace_id: str | None,
        auth_context: AuthContext,
        command: CreateSessionCommand,
    ) -> SessionSummaryView:
        session = Session(
            session_id=new_id(),
            status=SessionStatus.ACTIVE,
            profile_name=command.profile_name,
            actor_id=auth_context.actor_id,
            user_id=auth_context.user_id,
            org_id=auth_context.org_id,
            request_id=request_id,
            trace_id=trace_id,
        )
        await self._store.create_session(session)
        run = await self._agent_runs.start_run(
            request_id=request_id,
            trace_id=trace_id,
            auth_context=auth_context,
            session_id=session.session_id,
            command=StartAgentRunCommand(
                input_text=command.input_text,
                profile_name=command.profile_name,
            ),
        )
        refreshed = await self._require_session(session.session_id)
        refreshed.latest_run_id = run.run_id
        await self._append_user_message(
            session=refreshed,
            input_text=command.input_text,
            actor_id=auth_context.actor_id,
            run_id=run.run_id,
        )
        await self._store.update_session(refreshed)
        return self._summary_view(await self._require_session(session.session_id))

    async def append_message(
        self,
        *,
        session_id: str,
        request_id: str | None,
        trace_id: str | None,
        auth_context: AuthContext,
        command: AppendSessionMessageCommand,
    ) -> SessionSummaryView:
        session = await self._require_session(session_id)
        self._ensure_session_access(session, auth_context, write=True)
        if session.status in {SessionStatus.CANCELLED, SessionStatus.FAILED}:
            raise app_error(
                "Session is not available for more messages",
                code="session.not_appendable",
                category="validation",
                status_code=409,
                details={"session_id": session_id, "status": session.status.value},
                operation="session.append_message",
                component="sessions",
            )
        if session.latest_run_id is None:
            raise app_error(
                "Session is missing its attached execution reference",
                code="session.attached_execution_missing",
                category="internal",
                status_code=500,
                details={"session_id": session_id},
                operation="session.append_message",
                component="sessions",
            )
        run = await self._agent_runs.append_turn(
            run_id=session.latest_run_id,
            request_id=request_id,
            trace_id=trace_id,
            auth_context=auth_context,
            command=AppendAgentTurnCommand(input_text=command.input_text),
        )
        session.request_id = request_id or session.request_id
        session.trace_id = trace_id or session.trace_id
        session.actor_id = auth_context.actor_id or session.actor_id
        session.user_id = auth_context.user_id or session.user_id
        session.org_id = auth_context.org_id or session.org_id
        session.latest_run_id = run.run_id
        session.status = SessionStatus.ACTIVE
        session.completed_at = None
        session.error_code = None
        session.error_category = None
        session.error_message = None
        session.updated_at = utc_now()
        await self._append_user_message(
            session=session,
            input_text=command.input_text,
            actor_id=auth_context.actor_id,
            run_id=run.run_id,
        )
        await self._store.update_session(session)
        return self._summary_view(await self._require_session(session_id))

    async def get_session(
        self,
        session_id: str,
        *,
        auth_context: AuthContext,
    ) -> SessionDetailView | None:
        session = await self._store.get_session(session_id)
        if session is None:
            return None
        self._ensure_session_access(session, auth_context, write=False)
        items = await self._store.list_items(session_id)
        summary = await self._store.get_latest_summary(session_id)
        return SessionDetailView(
            **self._summary_view(session).model_dump(),
            summary=None if summary is None else self._materialized_summary_view(summary),
            items=[self._item_view(item) for item in items],
        )

    async def list_sessions(
        self,
        *,
        auth_context: AuthContext,
        limit: int = 50,
    ) -> list[SessionSummaryView]:
        items = await self._store.list_sessions(limit=max(limit, 500))
        if auth_context.has_permission(SESSIONS_READ_ANY_PERMISSION):
            return [self._summary_view(item) for item in items[:limit]]
        owned = [item for item in items if item.actor_id == auth_context.actor_id]
        return [self._summary_view(item) for item in owned[:limit]]

    async def list_items(
        self,
        session_id: str,
        *,
        auth_context: AuthContext,
        limit: int = 500,
    ) -> list[SessionItemView]:
        session = await self._require_session(session_id)
        self._ensure_session_access(session, auth_context, write=False)
        return [
            self._item_view(item) for item in await self._store.list_items(session_id, limit=limit)
        ]

    async def decide_approval(
        self,
        *,
        approval_id: str,
        request_id: str | None,
        trace_id: str | None,
        auth_context: AuthContext,
        command: ApprovalDecisionCommand,
    ) -> AgentApprovalView:
        return await self._agent_runs.decide_approval(
            approval_id=approval_id,
            request_id=request_id,
            trace_id=trace_id,
            auth_context=auth_context,
            command=command,
        )

    async def cancel_session(
        self,
        session_id: str,
        *,
        auth_context: AuthContext,
    ) -> SessionSummaryView:
        session = await self._require_session(session_id)
        self._ensure_session_access(session, auth_context, write=True)
        if session.latest_run_id is not None:
            await self._agent_runs.cancel_run(session.latest_run_id)
        session.status = SessionStatus.CANCELLED
        session.updated_at = utc_now()
        session.completed_at = session.updated_at
        await self._store.update_session(session)
        refreshed = await self._require_session(session_id)
        return self._summary_view(refreshed)

    async def list_events(
        self,
        session_id: str,
        *,
        auth_context: AuthContext,
        limit: int = 100,
    ) -> list[AgentEventView]:
        session = await self._require_session(session_id)
        self._ensure_session_access(session, auth_context, write=False)
        if session.latest_run_id is None:
            return []
        return await self._agent_runs.list_events(session.latest_run_id, limit=limit)

    async def observe_events(
        self,
        session_id: str,
        *,
        auth_context: AuthContext,
        after_sequence: int = 0,
        poll_interval_seconds: float = 0.05,
    ) -> AsyncIterator[AgentEventView]:
        session = await self._require_session(session_id)
        self._ensure_session_access(session, auth_context, write=False)
        if session.latest_run_id is None:
            return
        async for event in self._agent_runs.observe_events(
            session.latest_run_id,
            after_sequence=after_sequence,
            poll_interval_seconds=poll_interval_seconds,
        ):
            yield event

    async def _require_session(self, session_id: str) -> Session:
        session = await self._store.get_session(session_id)
        if session is None:
            raise app_error(
                "Session was not found",
                code="session.not_found",
                category="validation",
                status_code=404,
                details={"session_id": session_id},
                operation="session.require",
                component="sessions",
            )
        return session

    @staticmethod
    def _ensure_session_access(
        session: Session,
        auth_context: AuthContext,
        *,
        write: bool,
    ) -> None:
        if session.actor_id == auth_context.actor_id:
            return
        elevated_permission = (
            SESSIONS_WRITE_ANY_PERMISSION if write else SESSIONS_READ_ANY_PERMISSION
        )
        if auth_context.has_permission(elevated_permission):
            return
        if session.actor_id is None and session.org_id is not None and session.org_id == auth_context.org_id:
            return
        raise app_error(
            "Authenticated actor is not allowed to access this session",
            code="session.forbidden",
            category="validation",
            status_code=403,
            severity="warning",
            details={
                "session_id": session.session_id,
                "actor_id": auth_context.actor_id,
                "org_id": auth_context.org_id,
                "write": write,
            },
            operation="session.authorize",
            component="sessions",
        )

    @staticmethod
    def _summary_view(session: Session) -> SessionSummaryView:
        return SessionSummaryView(
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
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            error_code=session.error_code,
            error_category=session.error_category,
            error_message=session.error_message,
        )

    @staticmethod
    def _item_view(item: SessionItem) -> SessionItemView:
        return SessionItemView(
            item_id=item.item_id,
            sequence_no=item.sequence_no,
            item_type=item.item_type.value,
            actor_id=item.actor_id,
            run_id=item.run_id,
            turn_id=item.turn_id,
            tool_call_id=item.tool_call_id,
            payload=item.payload,
            created_at=item.created_at.isoformat(),
        )

    @staticmethod
    def _materialized_summary_view(summary: SessionSummary) -> SessionSummaryStateView:
        return SessionSummaryStateView(
            summary_id=summary.summary_id,
            status=summary.status.value,
            coverage_start_sequence=summary.coverage_start_sequence,
            coverage_end_sequence=summary.coverage_end_sequence,
            summary_text=summary.summary_text,
            task_id=summary.task_id,
            provider_name=summary.provider_name,
            model_name=summary.model_name,
            prompt_id=summary.prompt.prompt_id,
            prompt_version=summary.prompt.version,
            error_code=summary.error_code,
            error_category=summary.error_category,
            error_message=summary.error_message,
            created_at=summary.created_at.isoformat(),
            updated_at=summary.updated_at.isoformat(),
            completed_at=summary.completed_at.isoformat() if summary.completed_at else None,
        )

    async def _append_user_message(
        self,
        *,
        session: Session,
        input_text: str,
        actor_id: str | None,
        run_id: str,
    ) -> None:
        item = SessionItem(
            item_id=new_id(),
            session_id=session.session_id,
            sequence_no=await self._store.next_item_sequence(session.session_id),
            item_type=SessionItemType.USER_MESSAGE,
            payload={"text": input_text},
            actor_id=actor_id,
            run_id=run_id,
        )
        await self._store.create_item(item)
        session.latest_item_id = item.item_id
        session.updated_at = utc_now()
