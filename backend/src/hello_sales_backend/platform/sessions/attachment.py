"""Session attachment helpers for executor runtimes."""

from __future__ import annotations

from hello_sales_backend.platform.agents.models import AgentRun, AgentToolCall, AgentTurn
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.llm.contracts import LLMCallContext, LLMMessage, LLMProviderPort
from hello_sales_backend.platform.sessions.models import (
    Session,
    SessionItem,
    SessionItemType,
    SessionStatus,
    SessionSummary,
    SessionSummaryStatus,
    utc_now,
)
from hello_sales_backend.platform.sessions.persistence import SessionStorePort
from hello_sales_backend.platform.sessions.prompts import session_summary_prompt_ref
from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.shared.errors import AppError, app_error
from hello_sales_backend.shared.ids import new_id


class SessionAttachmentStore:
    """Append neutral session chronology and summary state for attached executor work."""

    def __init__(
        self,
        store: SessionStorePort,
        *,
        tasks: BackgroundTaskRunner,
        llm_provider: LLMProviderPort,
        settings: Settings,
    ) -> None:
        self._store = store
        self._tasks = tasks
        self._llm_provider = llm_provider
        self._settings = settings

    async def append_user_message(self, *, run: AgentRun, turn: AgentTurn) -> None:
        await self._append_item(
            run=run,
            turn=turn,
            item_type=SessionItemType.USER_MESSAGE,
            payload={"text": turn.input_text},
        )

    async def append_assistant_message(
        self, *, run: AgentRun, turn: AgentTurn, response_text: str
    ) -> None:
        await self._append_item(
            run=run,
            turn=turn,
            item_type=SessionItemType.ASSISTANT_MESSAGE,
            payload={"text": response_text},
        )
        await self._update_session_status(run=run, status=SessionStatus.COMPLETED)
        await self._schedule_summary_if_eligible(run=run)

    async def append_tool_call(
        self, *, run: AgentRun, turn: AgentTurn, tool_call: AgentToolCall
    ) -> None:
        await self._append_item(
            run=run,
            turn=turn,
            item_type=SessionItemType.TOOL_CALL,
            tool_call_id=tool_call.tool_call_id,
            payload={
                "tool_name": tool_call.tool_name,
                "arguments": tool_call.arguments,
                "status": tool_call.status.value,
                "approval_id": tool_call.approval_id,
                "requires_approval": tool_call.requires_approval,
            },
        )

    async def append_tool_result(
        self, *, run: AgentRun, turn: AgentTurn, tool_call: AgentToolCall
    ) -> None:
        await self._append_item(
            run=run,
            turn=turn,
            item_type=SessionItemType.TOOL_RESULT,
            tool_call_id=tool_call.tool_call_id,
            payload={
                "tool_name": tool_call.tool_name,
                "status": tool_call.status.value,
                "result": tool_call.result_payload,
                "error_code": tool_call.error_code,
                "error_message": tool_call.error_message,
            },
        )

    async def mark_awaiting_approval(self, *, run: AgentRun) -> None:
        await self._update_session_status(run=run, status=SessionStatus.AWAITING_APPROVAL)

    async def mark_running(self, *, run: AgentRun) -> None:
        await self._update_session_status(run=run, status=SessionStatus.ACTIVE)

    async def mark_failed(
        self, *, run: AgentRun, error_code: str | None, error_message: str | None
    ) -> None:
        session = await self._get_session(run)
        if session is None:
            return
        session.status = SessionStatus.FAILED
        session.error_code = error_code
        session.error_message = error_message
        session.updated_at = utc_now()
        session.completed_at = session.updated_at
        await self._store.update_session(session)
        if session.summary_task_id is not None:
            await self._mark_summary_failed(
                session_id=session.session_id,
                error_code=error_code or "session.summary.upstream_failed",
                error_message=error_message
                or "Attached execution failed before summary completion.",
            )

    async def mark_cancelled(self, *, run: AgentRun) -> None:
        session = await self._get_session(run)
        if session is None:
            return
        session.status = SessionStatus.CANCELLED
        session.updated_at = utc_now()
        session.completed_at = session.updated_at
        await self._store.update_session(session)

    async def _append_item(
        self,
        *,
        run: AgentRun,
        turn: AgentTurn,
        item_type: SessionItemType,
        payload: dict[str, object],
        tool_call_id: str | None = None,
    ) -> None:
        session = await self._get_session(run)
        if session is None:
            return
        item = SessionItem(
            item_id=new_id(),
            session_id=session.session_id,
            sequence_no=await self._store.next_item_sequence(session.session_id),
            item_type=item_type,
            payload=payload,
            actor_id=run.actor_id,
            run_id=run.run_id,
            turn_id=turn.turn_id,
            tool_call_id=tool_call_id,
            prompt=turn.prompt,
        )
        await self._store.create_item(item)
        session.latest_item_id = item.item_id
        session.latest_run_id = run.run_id
        session.updated_at = utc_now()
        await self._store.update_session(session)

    async def _update_session_status(self, *, run: AgentRun, status: SessionStatus) -> None:
        session = await self._get_session(run)
        if session is None:
            return
        session.status = status
        session.latest_run_id = run.run_id
        session.updated_at = utc_now()
        if status in {SessionStatus.COMPLETED, SessionStatus.CANCELLED, SessionStatus.FAILED}:
            session.completed_at = session.updated_at
        await self._store.update_session(session)

    async def _schedule_summary_if_eligible(self, *, run: AgentRun) -> None:
        session = await self._get_session(run)
        if session is None:
            return
        items = await self._store.list_items(session.session_id)
        assistant_items = [
            item for item in items if item.item_type == SessionItemType.ASSISTANT_MESSAGE
        ]
        covered = len(
            [
                item
                for item in assistant_items
                if item.sequence_no <= session.last_summarized_item_sequence
            ]
        )
        unsummarized_turns = len(assistant_items) - covered
        if unsummarized_turns < self._settings.session_summary_turn_interval:
            return
        if session.summary_status in {
            SessionSummaryStatus.QUEUED.value,
            SessionSummaryStatus.RUNNING.value,
        }:
            return
        task_id = f"session-summary-{session.session_id}"
        session.summary_task_id = task_id
        session.summary_status = SessionSummaryStatus.QUEUED.value
        session.updated_at = utc_now()
        await self._store.update_session(session)
        prompt = session_summary_prompt_ref()
        existing = await self._store.get_latest_summary(session.session_id)
        coverage_start = 1 if existing is None else existing.coverage_end_sequence + 1
        coverage_end = items[-1].sequence_no if items else 0
        await self._store.upsert_summary(
            SessionSummary(
                summary_id=new_id(),
                session_id=session.session_id,
                coverage_start_sequence=coverage_start,
                coverage_end_sequence=coverage_end,
                summary_text="",
                prompt=prompt,
                status=SessionSummaryStatus.QUEUED,
                task_id=task_id,
            )
        )
        self._tasks.start(
            TaskMetadata(
                task_id=task_id,
                purpose="session_summary_generation",
                request_id=session.request_id,
                trace_id=session.trace_id,
                actor_id=session.actor_id,
            ),
            self._generate_summary(
                session_id=session.session_id,
                coverage_start=coverage_start,
                coverage_end=coverage_end,
            ),
        )

    async def _generate_summary(
        self,
        *,
        session_id: str,
        coverage_start: int,
        coverage_end: int,
    ) -> None:
        session = await self._store.get_session(session_id)
        if session is None:
            raise app_error(
                "Session was not found while generating summary",
                code="session.summary.session_not_found",
                category="validation",
                status_code=404,
                details={"session_id": session_id},
                operation="session.summary.generate",
                component="sessions",
            )
        items = await self._store.list_items(session_id)
        prompt = session_summary_prompt_ref()
        eligible_items = [
            item for item in items if coverage_start <= item.sequence_no <= coverage_end
        ]
        running_summary = SessionSummary(
            summary_id=new_id(),
            session_id=session_id,
            coverage_start_sequence=coverage_start,
            coverage_end_sequence=coverage_end,
            summary_text="",
            prompt=prompt,
            status=SessionSummaryStatus.RUNNING,
            task_id=session.summary_task_id,
        )
        await self._store.upsert_summary(running_summary)
        session.summary_status = SessionSummaryStatus.RUNNING.value
        session.updated_at = utc_now()
        await self._store.update_session(session)
        try:
            if not self._llm_provider.is_configured():
                output_text = self._fallback_summary(eligible_items)
                provider_name = "fallback"
                model_name = "deterministic-session-summary"
            else:
                result = await self._llm_provider.generate_text(
                    [
                        LLMMessage(
                            role="system",
                            content=(
                                "Summarize the session chronology into concise operational notes. "
                                "Keep tool outcomes explicit and avoid inventing facts."
                            ),
                        ),
                        LLMMessage(role="user", content=self._render_summary_input(eligible_items)),
                    ],
                    context=LLMCallContext(
                        request_id=session.request_id,
                        trace_id=session.trace_id,
                        actor_id=session.actor_id,
                        operation="session.summary.generate_text",
                        prompt=prompt,
                    ),
                )
                output_text = result.output_text.strip()
                provider_name = result.provider
                model_name = result.model
            completed = SessionSummary(
                summary_id=running_summary.summary_id,
                session_id=session_id,
                coverage_start_sequence=coverage_start,
                coverage_end_sequence=coverage_end,
                summary_text=output_text,
                prompt=prompt,
                status=SessionSummaryStatus.COMPLETED,
                task_id=session.summary_task_id,
                provider_name=provider_name,
                model_name=model_name,
                created_at=running_summary.created_at,
                updated_at=utc_now(),
                completed_at=utc_now(),
            )
            await self._store.upsert_summary(completed)
            session.summary_status = SessionSummaryStatus.COMPLETED.value
            session.last_summarized_item_sequence = coverage_end
            session.updated_at = utc_now()
            await self._store.update_session(session)
        except AppError as exc:
            await self._mark_summary_failed(
                session_id=session_id,
                error_code=exc.code,
                error_message=exc.message,
                error_category=exc.category,
            )
            raise
        except Exception as exc:
            await self._mark_summary_failed(
                session_id=session_id,
                error_code="session.summary.unexpected_failure",
                error_message=str(exc),
                error_category="internal",
            )
            raise

    async def _mark_summary_failed(
        self,
        *,
        session_id: str,
        error_code: str,
        error_message: str,
        error_category: str | None = "provider",
    ) -> None:
        session = await self._store.get_session(session_id)
        if session is None:
            return
        latest = await self._store.get_latest_summary(session_id)
        prompt = session_summary_prompt_ref() if latest is None else latest.prompt
        failed = SessionSummary(
            summary_id=new_id() if latest is None else latest.summary_id,
            session_id=session_id,
            coverage_start_sequence=1 if latest is None else latest.coverage_start_sequence,
            coverage_end_sequence=session.last_summarized_item_sequence
            if latest is None
            else latest.coverage_end_sequence,
            summary_text="" if latest is None else latest.summary_text,
            prompt=prompt,
            status=SessionSummaryStatus.FAILED,
            task_id=session.summary_task_id,
            provider_name=None if latest is None else latest.provider_name,
            model_name=None if latest is None else latest.model_name,
            error_code=error_code,
            error_category=error_category,
            error_message=error_message,
            created_at=utc_now() if latest is None else latest.created_at,
            updated_at=utc_now(),
            completed_at=utc_now(),
        )
        await self._store.upsert_summary(failed)
        session.summary_status = SessionSummaryStatus.FAILED.value
        session.updated_at = utc_now()
        await self._store.update_session(session)

    async def _get_session(self, run: AgentRun) -> Session | None:
        if run.session_id is None:
            return None
        return await self._store.get_session(run.session_id)

    @staticmethod
    def _render_summary_input(items: list[SessionItem]) -> str:
        rendered: list[str] = []
        for item in items:
            rendered.append(f"{item.sequence_no}:{item.item_type.value}:{item.payload}")
        return "\n".join(rendered)

    @staticmethod
    def _fallback_summary(items: list[SessionItem]) -> str:
        if not items:
            return "No new eligible session turns."
        lines = ["Session summary:"]
        for item in items[-8:]:
            if item.item_type == SessionItemType.USER_MESSAGE:
                lines.append(f"user: {item.payload.get('text', '')}")
            elif item.item_type == SessionItemType.ASSISTANT_MESSAGE:
                lines.append(f"assistant: {item.payload.get('text', '')}")
            elif item.item_type == SessionItemType.TOOL_RESULT:
                lines.append(
                    f"tool: {item.payload.get('tool_name', '')} -> {item.payload.get('result')}"
                )
        return "\n".join(lines)
