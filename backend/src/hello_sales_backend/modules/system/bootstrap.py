"""System module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.system.infra.clock import UtcClock
from hello_sales_backend.modules.system.use_cases.ports import (
    AgentDiagnosticsPort,
    AgentRegistryPort,
    ClockPort,
    ObservabilityPort,
)
from hello_sales_backend.modules.system.use_cases.system_service import SystemService
from hello_sales_backend.platform.composition.providers import ProviderRegistry
from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.platform.workflows.runtime import WorkflowRuntime


@dataclass(slots=True)
class SystemModule:
    """Resolved system module bundle."""

    service: SystemService


def build_system_module(
    *,
    settings: Settings,
    providers: ProviderRegistry,
    tasks: BackgroundTaskRunner,
    workflow_runtime: WorkflowRuntime,
    observability: ObservabilityPort,
    agent_diagnostics: AgentDiagnosticsPort,
    agent_registry: AgentRegistryPort,
    clock: ClockPort | None = None,
) -> SystemModule:
    """Build the system module."""

    service = SystemService(
        settings=settings,
        clock=clock or UtcClock(),
        providers=providers,
        tasks=tasks,
        workflow_runtime=workflow_runtime,
        observability=observability,
        agent_diagnostics=agent_diagnostics,
        agent_registry=agent_registry,
    )
    return SystemModule(service=service)
