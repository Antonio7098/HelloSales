from __future__ import annotations

from typing import cast

import pytest

from hello_sales_backend.application.agents.bootstrap import build_agent_registry
from hello_sales_backend.application.agents.registry import AgentRegistry
from hello_sales_backend.modules.analytics_query.use_cases.analytics_query_service import (
    AnalyticsQueryService,
)
from hello_sales_backend.modules.jobs.bootstrap import build_jobs_module
from hello_sales_backend.modules.system.bootstrap import build_system_module
from hello_sales_backend.modules.web_search.use_cases.web_search_service import WebSearchService
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.observability.runtime import (
    AlertPolicy,
    InMemoryOperationalStore,
    ObservabilityRuntime,
)
from hello_sales_backend.platform.providers.llm.noop import NoopChatModel
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor
from hello_sales_backend.platform.workflows.runtime import build_workflow_runtime
from hello_sales_backend.shared.errors import AppError


def _build_registry() -> AgentRegistry:
    settings = Settings(environment="test", database_url="sqlite+aiosqlite:///registry.db")
    observability = ObservabilityRuntime(store=InMemoryOperationalStore(), alert_policy=AlertPolicy())
    tasks = BackgroundTaskRunner(observability=observability)
    workflow_runtime = build_workflow_runtime(settings)
    workflow_executor = WorkflowExecutor(runtime=workflow_runtime)
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
    analytics_query_service = cast(AnalyticsQueryService, type("AnalyticsQueryStub", (), {"query_data": None})())
    web_search_service = cast(WebSearchService, type("WebSearchStub", (), {"search": None})())
    return build_agent_registry(
        settings=settings,
        system_service=system_module.service,
        jobs_service=jobs_module.service,
        analytics_query_service=analytics_query_service,
        web_search_service=web_search_service,
    )


def test_agent_registry_exposes_generic_and_observer_profiles() -> None:
    registry = _build_registry()

    generic = registry.require("generic")
    observer = registry.require("observer")

    assert generic.agent_id == "generic"
    assert observer.agent_id == "observer"
    assert generic.tools.has("query_analytics_data")
    assert generic.tools.has("search_web")
    assert observer.tools.has("get_runtime_status")
    assert not observer.tools.has("run_diagnostic_job")


def test_agent_registry_rejects_unknown_profile() -> None:
    registry = _build_registry()

    with pytest.raises(AppError) as exc_info:
        registry.require("missing")

    assert exc_info.value.code == "agent.profile.not_found"
