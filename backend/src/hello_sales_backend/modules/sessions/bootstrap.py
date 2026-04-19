"""Sessions module bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.agent_runs import AgentRunService
from hello_sales_backend.modules.sessions.use_cases.session_service import SessionService
from hello_sales_backend.platform.sessions.persistence import SessionStorePort


@dataclass(slots=True)
class SessionsModule:
    """Resolved sessions module bundle."""

    service: SessionService


def build_sessions_module(*, store: SessionStorePort, agent_runs: AgentRunService) -> SessionsModule:
    """Build the sessions module."""

    return SessionsModule(service=SessionService(store=store, agent_runs=agent_runs))

