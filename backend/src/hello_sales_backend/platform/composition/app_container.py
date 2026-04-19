"""Top-level application container."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from hello_sales_backend.application.agents.bootstrap import build_agent_registry
from hello_sales_backend.application.workers.bootstrap import build_worker_registry
from hello_sales_backend.modules.agent_runs.bootstrap import build_agent_runs_module
from hello_sales_backend.modules.jobs.bootstrap import build_jobs_module
from hello_sales_backend.modules.sessions.bootstrap import build_sessions_module
from hello_sales_backend.modules.system.bootstrap import build_system_module
from hello_sales_backend.modules.worker_runs.bootstrap import build_worker_runs_module
from hello_sales_backend.platform.agents.config import AgentRuntimeConfig
from hello_sales_backend.platform.agents.contracts import (
    AgentProfileCatalogPort,
)
from hello_sales_backend.platform.agents.memory import InMemoryAgentStore
from hello_sales_backend.platform.agents.persistence import AgentStorePort
from hello_sales_backend.platform.agents.runtime import GenericAgentRuntime
from hello_sales_backend.platform.composition.module_registry import ModuleRegistry
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.composition.providers import (
    ProviderRegistry,
    build_provider_registry,
)
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.db.engine import build_engine
from hello_sales_backend.platform.db.repositories import (
    SqlAlchemyAgentStore,
    SqlAlchemySessionStore,
    SqlAlchemyTaskRunStore,
)
from hello_sales_backend.platform.db.session import build_session_factory
from hello_sales_backend.platform.db.uow import UnitOfWorkFactory, build_uow_factory
from hello_sales_backend.platform.observability.health import HealthService
from hello_sales_backend.platform.observability.runtime import (
    AlertPolicy,
    InMemoryOperationalStore,
    ObservabilityRuntime,
    build_metrics_runtime,
    build_tracing_runtime,
)
from hello_sales_backend.platform.sessions.attachment import SessionAttachmentStore
from hello_sales_backend.platform.sessions.memory import InMemorySessionStore
from hello_sales_backend.platform.sessions.persistence import SessionStorePort
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workers import InMemoryWorkerStore, WorkerRuntime, WorkerStorePort
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor
from hello_sales_backend.platform.workflows.registry import WorkflowRegistry
from hello_sales_backend.platform.workflows.runtime import WorkflowRuntime, build_workflow_runtime


@dataclass(slots=True)
class AgentRegistryDiagnosticsAdapter:
    """Late-bound adapter used by system diagnostics to inspect registered agents."""

    registry: AgentProfileCatalogPort | None = None

    def list_profiles(self) -> list[tuple[str, str]]:
        if self.registry is None:
            return []
        return self.registry.list_profiles()


@dataclass(slots=True)
class DatabaseRuntime:
    """Resolved database runtime resources."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    uow_factory: UnitOfWorkFactory
    task_run_store: SqlAlchemyTaskRunStore
    agent_store: AgentStorePort
    session_store: SessionStorePort
    worker_store: WorkerStorePort


@dataclass(slots=True)
class AppContainer:
    """Resolved application runtime graph."""

    settings: Settings
    db: DatabaseRuntime
    providers: ProviderRegistry
    tasks: BackgroundTaskRunner
    workflow_runtime: WorkflowRuntime
    workflow_executor: WorkflowExecutor
    workflow_registry: WorkflowRegistry
    agent_runtime: GenericAgentRuntime
    worker_runtime: WorkerRuntime
    health_service: HealthService
    observability: ObservabilityRuntime
    modules: ModuleRegistry


def build_app_container(settings: Settings, overrides: AppOverrides | None = None) -> AppContainer:
    """Build the application composition root."""

    resolved_overrides = overrides or AppOverrides()
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    task_run_store = SqlAlchemyTaskRunStore(session_factory)
    agent_store: AgentStorePort
    session_store: SessionStorePort
    if settings.database_url.startswith("sqlite+aiosqlite"):
        agent_store = InMemoryAgentStore()
        session_store = InMemorySessionStore()
    else:
        agent_store = SqlAlchemyAgentStore(session_factory)
        session_store = SqlAlchemySessionStore(session_factory)
    worker_store: WorkerStorePort = InMemoryWorkerStore()
    db = DatabaseRuntime(
        engine=engine,
        session_factory=session_factory,
        uow_factory=build_uow_factory(session_factory),
        task_run_store=task_run_store,
        agent_store=agent_store,
        session_store=session_store,
        worker_store=worker_store,
    )
    providers = build_provider_registry(settings=settings, llm_provider=resolved_overrides.llm_provider)
    task_event_sink = resolved_overrides.task_event_sink
    if task_event_sink is None and not settings.database_url.startswith("sqlite+aiosqlite"):
        task_event_sink = task_run_store
    observability = resolved_overrides.observability_runtime or ObservabilityRuntime(
        store=InMemoryOperationalStore(),
        alert_policy=AlertPolicy(),
        metrics=build_metrics_runtime(settings),
        tracing=build_tracing_runtime(settings),
    )
    tasks = resolved_overrides.task_runner or BackgroundTaskRunner(
        event_sink=task_event_sink,
        observability=observability,
    )
    workflow_runtime = resolved_overrides.workflow_runtime or build_workflow_runtime(settings)
    workflow_executor = WorkflowExecutor(runtime=workflow_runtime)
    workflow_registry = WorkflowRegistry()
    health_service = HealthService(
        settings=settings,
        session_factory=session_factory,
        workflows=workflow_runtime,
        observability=observability,
    )
    jobs_module = build_jobs_module(
        providers=providers,
        tasks=tasks,
        workflow_executor=workflow_executor,
    )
    worker_registry = build_worker_registry()
    worker_runtime = WorkerRuntime(
        llm_provider=providers.llm,
        store=worker_store,
        workers=worker_registry,
        observability=observability,
    )
    agent_registry_diagnostics = AgentRegistryDiagnosticsAdapter()
    system_module = build_system_module(
        settings=settings,
        providers=providers,
        tasks=tasks,
        workflow_runtime=workflow_runtime,
        observability=observability,
        agent_diagnostics=agent_store,
        session_diagnostics=session_store,
        worker_diagnostics=worker_store,
        agent_registry=agent_registry_diagnostics,
        clock=resolved_overrides.system_clock,
    )
    agent_registry = build_agent_registry(
        system_service=system_module.service,
        jobs_service=jobs_module.service,
    )
    agent_registry_diagnostics.registry = agent_registry
    agent_runtime = GenericAgentRuntime(
        config=AgentRuntimeConfig(),
        workflow_runtime=workflow_runtime,
        llm_provider=providers.llm,
        store=agent_store,
        agents=agent_registry,
        observability=observability,
        sessions=SessionAttachmentStore(
            session_store,
            tasks=tasks,
            llm_provider=providers.llm,
            settings=settings,
        ),
    )
    agent_runs_module = build_agent_runs_module(
        store=agent_store,
        runtime=agent_runtime,
        tasks=tasks,
        agents=agent_registry,
    )
    sessions_module = build_sessions_module(
        store=session_store,
        agent_runs=agent_runs_module.service,
    )
    worker_runs_module = build_worker_runs_module(
        store=worker_store,
        runtime=worker_runtime,
        tasks=tasks,
        workflow_executor=workflow_executor,
        workers=worker_registry,
    )
    modules = ModuleRegistry(
        agent_runs=agent_runs_module,
        jobs=jobs_module,
        sessions=sessions_module,
        system=system_module,
        worker_runs=worker_runs_module,
    )
    return AppContainer(
        settings=settings,
        db=db,
        providers=providers,
        tasks=tasks,
        workflow_runtime=workflow_runtime,
        workflow_executor=workflow_executor,
        workflow_registry=workflow_registry,
        agent_runtime=agent_runtime,
        worker_runtime=worker_runtime,
        health_service=health_service,
        observability=observability,
        modules=modules,
    )
