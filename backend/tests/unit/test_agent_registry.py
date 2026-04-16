from __future__ import annotations

import pytest

from hello_sales_backend.application.agents.bootstrap import build_agent_registry
from hello_sales_backend.modules.jobs.use_cases.jobs_service import JobsService
from hello_sales_backend.platform.composition.overrides import AppOverrides
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import AlertPolicy, InMemoryOperationalStore, ObservabilityRuntime
from hello_sales_backend.platform.providers.llm.noop import NoopChatModel
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor
from hello_sales_backend.platform.workflows.runtime import build_workflow_runtime
from hello_sales_backend.modules.jobs.bootstrap import build_jobs_module
from hello_sales_backend.modules.system.bootstrap import build_system_module
from hello_sales_backend.shared.errors import AppError


def _build_registry():
    settings = Settings(environment="test", database_url="sqlite+aiosqlite:///registry.db")
    observability = ObservabilityRuntime(store=InMemoryOperationalStore(), alert_policy=AlertPolicy())
    tasks = BackgroundTaskRunner(observability=observability)
    workflow_runtime = build_workflow_runtime(settings)
    workflow_executor = WorkflowExecutor(runtime=workflow_runtime)
    providers = AppOverrides(llm_provider=NoopChatModel())
    jobs_module = build_jobs_module(
        providers=type("Providers", (), {"llm": NoopChatModel()})(),
        tasks=tasks,
        workflow_executor=workflow_executor,
    )
    system_module = build_system_module(
        settings=settings,
        providers=type("Providers", (), {"diagnostics": lambda self: []})(),
        tasks=tasks,
        workflow_runtime=workflow_runtime,
        observability=observability,
        agent_diagnostics=type("Diag", (), {"summarize": lambda self, limit=10: None})(),
        agent_registry=type("Registry", (), {"list_profiles": lambda self: []})(),
        clock=None,
    )
    return build_agent_registry(system_service=system_module.service, jobs_service=jobs_module.service)


def test_agent_registry_exposes_generic_and_observer_profiles():
    registry = _build_registry()

    generic = registry.require("generic")
    observer = registry.require("observer")

    assert generic.agent_id == "generic"
    assert observer.agent_id == "observer"
    assert observer.tools.has("get_runtime_status")
    assert not observer.tools.has("run_diagnostic_job")


def test_agent_registry_rejects_unknown_profile():
    registry = _build_registry()

    with pytest.raises(AppError) as exc_info:
        registry.require("missing")

    assert exc_info.value.code == "agent.profile.not_found"
