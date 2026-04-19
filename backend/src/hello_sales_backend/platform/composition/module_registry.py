"""Typed module registry."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.agent_runs.bootstrap import AgentRunsModule
from hello_sales_backend.modules.jobs.bootstrap import JobsModule
from hello_sales_backend.modules.sessions.bootstrap import SessionsModule
from hello_sales_backend.modules.system.bootstrap import SystemModule
from hello_sales_backend.modules.worker_runs.bootstrap import WorkerRunsModule


@dataclass(slots=True)
class ModuleRegistry:
    """Resolved module bundles."""

    agent_runs: AgentRunsModule
    jobs: JobsModule
    sessions: SessionsModule
    system: SystemModule
    worker_runs: WorkerRunsModule
