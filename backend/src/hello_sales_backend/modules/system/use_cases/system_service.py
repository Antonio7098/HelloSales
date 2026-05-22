"""System application service."""

from __future__ import annotations

from dataclasses import asdict

from hello_sales_backend.modules.system.domain.entities import (
    ProviderRuntimeStatus,
    RuntimeStatus,
    TaskRuntimeStatus,
    WorkerRuntimeStatus,
)
from hello_sales_backend.modules.system.use_cases.ports import (
    AgentDiagnosticsPort,
    AgentRegistryPort,
    ClockPort,
    ObservabilityPort,
    SessionDiagnosticsPort,
    WorkerDiagnosticsPort,
)
from hello_sales_backend.modules.salesbook.use_cases.ports import (
    SalesbookDiagnosticsPort,
)
from hello_sales_backend.modules.system.use_cases.views import (
    AgentDiagnosticsView,
    AgentProfileView,
    AgentRunSnapshotView,
    AlertView,
    MetricsDiagnosticsView,
    ObservabilityDiagnosticsView,
    OperationalEventView,
    ProviderDiagnosticsView,
    SalesbookDiagnosticsView,
    SalesbookRunSnapshotView,
    SessionDiagnosticsView,
    SessionSnapshotView,
    SystemDiagnosticsView,
    SystemStatusView,
    TaskDiagnosticsView,
    TaskSnapshotView,
    TracingDiagnosticsView,
    WorkerDiagnosticsView,
    WorkerRunSnapshotView,
)
from hello_sales_backend.platform.composition.providers import ProviderRegistry
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workflows.runtime import WorkflowRuntime


class SystemService:
    """Return operational runtime metadata through a stable module facade."""

    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockPort,
        observability: ObservabilityPort,
        providers: ProviderRegistry,
        tasks: BackgroundTaskRunner,
        workflow_runtime: WorkflowRuntime,
        agent_diagnostics: AgentDiagnosticsPort,
        session_diagnostics: SessionDiagnosticsPort,
        worker_diagnostics: WorkerDiagnosticsPort,
        agent_registry: AgentRegistryPort,
        salesbook_diagnostics: SalesbookDiagnosticsPort,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._observability = observability
        self._providers = providers
        self._tasks = tasks
        self._workflow_runtime = workflow_runtime
        self._agent_diagnostics = agent_diagnostics
        self._session_diagnostics = session_diagnostics
        self._worker_diagnostics = worker_diagnostics
        self._agent_registry = agent_registry
        self._salesbook_diagnostics = salesbook_diagnostics

    async def get_status(self) -> SystemStatusView:
        runtime_status = RuntimeStatus(
            app_name=self._settings.app_name,
            environment=self._settings.environment,
            workflow_engine=self._workflow_runtime.engine_name,
            workflow_installed=self._workflow_runtime.installed,
            current_time_utc=self._clock.now_iso(),
        )
        return SystemStatusView.model_validate(runtime_status.model_dump())

    async def get_diagnostics(self) -> SystemDiagnosticsView:
        providers = [
            ProviderDiagnosticsView.model_validate(
                ProviderRuntimeStatus(
                    name=item.name,
                    available=item.available,
                    kind=item.kind,
                    required=item.required,
                    degraded=item.degraded,
                ).model_dump()
            )
            for item in self._providers.diagnostics()
        ]
        task_snapshots = [
            TaskSnapshotView.model_validate(
                TaskRuntimeStatus(
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
                    error_details=snapshot.error_details,
                    created_at=snapshot.created_at.isoformat(),
                    started_at=snapshot.started_at.isoformat() if snapshot.started_at else None,
                    finished_at=snapshot.finished_at.isoformat() if snapshot.finished_at else None,
                ).model_dump()
            )
            for snapshot in self._tasks.list_snapshots(limit=10)
        ]
        agent_summary = await self._agent_diagnostics.summarize(limit=10)
        session_summary = await self._session_diagnostics.list_sessions(limit=10)
        worker_summary = await self._worker_diagnostics.summarize(limit=10)
        salesbook_summary = await self._salesbook_diagnostics.summarize(limit=10)
        observability_diagnostics = self._observability.diagnostics()
        return SystemDiagnosticsView(
            app_name=self._settings.app_name,
            environment=self._settings.environment,
            database_scheme=self._settings.database_url.split(":", 1)[0],
            workflow_engine=self._workflow_runtime.engine_name,
            workflow_installed=self._workflow_runtime.installed,
            current_time_utc=self._clock.now_iso(),
            providers=providers,
            agent_profiles=[
                AgentProfileView(agent_id=agent_id, display_name=display_name)
                for agent_id, display_name in self._agent_registry.list_profiles()
            ],
            tasks=TaskDiagnosticsView(
                active_count=self._tasks.active_count(),
                failure_count=self._tasks.failure_count(),
                total_count=len(self._tasks.list_snapshots()),
                recent=task_snapshots,
            ),
            agents=AgentDiagnosticsView(
                active_count=agent_summary.active_count,
                awaiting_approval_count=agent_summary.awaiting_approval_count,
                total_count=agent_summary.total_count,
                recent=[
                    AgentRunSnapshotView(
                        run_id=item.run_id,
                        profile_name=item.profile_name,
                        status=item.status.value,
                        prompt_id=None if item.prompt is None else item.prompt.prompt_id,
                        prompt_version=None if item.prompt is None else item.prompt.version,
                        request_id=item.request_id,
                        trace_id=item.trace_id,
                        actor_id=item.actor_id,
                        latest_turn_id=item.latest_turn_id,
                        error_code=item.error_code,
                        error_category=item.error_category,
                        error_message=item.error_message,
                        created_at=item.created_at.isoformat(),
                        updated_at=item.updated_at.isoformat(),
                        started_at=item.started_at.isoformat() if item.started_at else None,
                        completed_at=item.completed_at.isoformat() if item.completed_at else None,
                    )
                    for item in agent_summary.recent_runs
                ],
            ),
            sessions=SessionDiagnosticsView(
                total_count=len(session_summary),
                active_count=sum(1 for item in session_summary if item.status.value == "active"),
                awaiting_approval_count=sum(
                    1 for item in session_summary if item.status.value == "awaiting_approval"
                ),
                recent=[
                    SessionSnapshotView(
                        session_id=item.session_id,
                        status=item.status.value,
                        profile_name=item.profile_name,
                        latest_run_id=item.latest_run_id,
                        latest_item_id=item.latest_item_id,
                        summary_task_id=item.summary_task_id,
                        summary_status=item.summary_status,
                        last_summarized_item_sequence=item.last_summarized_item_sequence,
                        request_id=item.request_id,
                        trace_id=item.trace_id,
                        actor_id=item.actor_id,
                        user_id=item.user_id,
                        org_id=item.org_id,
                        error_code=item.error_code,
                        error_category=item.error_category,
                        error_message=item.error_message,
                        created_at=item.created_at.isoformat(),
                        updated_at=item.updated_at.isoformat(),
                        completed_at=item.completed_at.isoformat() if item.completed_at else None,
                    )
                    for item in session_summary
                ],
            ),
            workers=WorkerDiagnosticsView(
                active_count=worker_summary.active_count,
                total_count=worker_summary.total_count,
                recent=[
                    WorkerRunSnapshotView.model_validate(
                        WorkerRuntimeStatus(
                            run_id=item.run_id,
                            worker_name=item.worker_name,
                            status=item.status.value,
                            prompt_id=None if item.prompt is None else item.prompt.prompt_id,
                            prompt_version=None if item.prompt is None else item.prompt.version,
                            execution_mode=item.execution_mode.value,
                            request_id=item.request_id,
                            trace_id=item.trace_id,
                            actor_id=item.actor_id,
                            task_id=item.task_id,
                            attempt_count=item.attempt_count,
                            max_attempts=item.max_attempts,
                            timeout_seconds=item.timeout_seconds,
                            provider_name=item.provider_name,
                            model_name=item.model_name,
                            error_code=item.error_code,
                            error_category=item.error_category,
                            error_message=item.error_message,
                            created_at=item.created_at.isoformat(),
                            updated_at=item.updated_at.isoformat(),
                            started_at=item.started_at.isoformat() if item.started_at else None,
                            completed_at=item.completed_at.isoformat() if item.completed_at else None,
                        ).model_dump()
                    )
                    for item in worker_summary.recent_runs
                ],
            ),
            observability=ObservabilityDiagnosticsView(
                metrics=MetricsDiagnosticsView.model_validate(asdict(observability_diagnostics.metrics)),
                tracing=TracingDiagnosticsView.model_validate(asdict(observability_diagnostics.tracing)),
            ),
            events=[
                OperationalEventView.model_validate(event.model_dump())
                for event in self._observability.recent_events(limit=20)
            ],
            alerts=[
                AlertView.model_validate(asdict(alert))
                for alert in self._observability.active_alerts(limit=20)
            ],
            salesbook=SalesbookDiagnosticsView(
                active_count=salesbook_summary.active_count,
                total_count=salesbook_summary.total_count,
                recent=[
                    SalesbookRunSnapshotView(
                        log_id=item.log_id,
                        profile_id=item.profile_id,
                        deal_id=item.deal_id,
                        action_type=item.action_type,
                        action_detail=item.action_detail,
                        action_result=item.action_result,
                        next_step=item.next_step,
                        channel=item.channel,
                        agent_id=item.agent_id,
                        timestamp=item.timestamp.isoformat(),
                    )
                    for item in salesbook_summary.recent_runs
                ],
            ),
        )
