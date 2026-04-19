"""Agent-runs module assembly."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.agent_runs.use_cases.agent_run_service import AgentRunService
from hello_sales_backend.platform.agents.contracts import AgentDefinitionResolverPort
from hello_sales_backend.platform.agents.persistence import AgentStorePort
from hello_sales_backend.platform.agents.runtime import AgentExecutionRuntime
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner


@dataclass(slots=True)
class AgentRunsModule:
    """Resolved agent-runs module bundle."""

    service: AgentRunService


def build_agent_runs_module(
    *,
    store: AgentStorePort,
    runtime: AgentExecutionRuntime,
    tasks: BackgroundTaskRunner,
    agents: AgentDefinitionResolverPort,
) -> AgentRunsModule:
    """Build the agent-runs module."""

    return AgentRunsModule(
        service=AgentRunService(
            store=store,
            runtime=runtime,
            tasks=tasks,
            agents=agents,
        )
    )
