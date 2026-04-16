"""System application service."""

from __future__ import annotations

from dataclasses import asdict

from hello_sales_backend.modules.system.domain.entities import (
    ProviderRuntimeStatus,
    RuntimeStatus,
    TaskRuntimeStatus,
)
from hello_sales_backend.modules.system.use_cases.ports import (
    AgentDiagnosticsPort,
    AgentRegistryPort,
    ClockPort,
    ObservabilityPort,
)
from hello_sales_backend.modules.system.use_cases.views import (
    AgentDiagnosticsView,
    AgentProfileView,
    AgentRunSnapshotView,
    AlertView,
    OperationalEventView,
    ProviderDiagnosticsView,
    SystemDiagnosticsView,
    SystemStatusView,
    TaskDiagnosticsView,
    TaskSnapshotView,
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
        agent_registry: AgentRegistryPort,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._observability = observability
        self._providers = providers
        self._tasks = tasks
        self._workflow_runtime = workflow_runtime
        self._agent_diagnostics = agent_diagnostics
        self._agent_registry = agent_registry

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
                ProviderRuntimeStatus(name=item.name, available=item.available).model_dump()
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
            events=[
                OperationalEventView.model_validate(event.model_dump())
                for event in self._observability.recent_events(limit=20)
            ],
            alerts=[
                AlertView.model_validate(asdict(alert))
                for alert in self._observability.active_alerts(limit=20)
            ],
        )
