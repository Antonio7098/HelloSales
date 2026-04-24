"""FastAPI dependency helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from fastapi import Depends, Request

from hello_sales_backend.modules.agent_runs import AgentRunService
from hello_sales_backend.modules.auth import AuthService
from hello_sales_backend.modules.company_profile import CompanyProfileService
from hello_sales_backend.modules.jobs import JobsService
from hello_sales_backend.modules.sessions import SessionService
from hello_sales_backend.modules.system import SystemService
from hello_sales_backend.modules.worker_runs import WorkerRunService
from hello_sales_backend.platform.composition.app_container import AppContainer
from hello_sales_backend.platform.observability.health import HealthService
from hello_sales_backend.shared.auth import AuthContext


async def get_container(request: Request) -> AppContainer:
    """Return the application container."""

    return cast(AppContainer, request.app.state.container)


async def get_health_service(request: Request) -> HealthService:
    """Resolve the health service from the container."""

    return (await get_container(request)).health_service


async def get_auth_service(request: Request) -> AuthService:
    """Resolve the auth service from the container."""

    return (await get_container(request)).modules.auth.service


async def get_current_auth_context(request: Request) -> AuthContext | None:
    """Return the request-scoped auth context resolved by middleware."""

    return cast(AuthContext | None, getattr(request.state, "auth_context", None))


async def require_authenticated_context(
    auth_service: AuthService = Depends(get_auth_service),
    auth_context: AuthContext | None = Depends(get_current_auth_context),
) -> AuthContext:
    """Return the current auth context or raise a structured 401."""

    return auth_service.require_authenticated(auth_context)


def require_permissions(*permissions: str) -> Callable[..., object]:
    """Return a dependency that enforces backend permissions."""

    async def dependency(
        auth_context: AuthContext = Depends(require_authenticated_context),
    ) -> AuthContext:
        auth_context.require_permissions(
            *permissions,
            operation="http.authorization",
            component="auth",
        )
        return auth_context

    return dependency


async def get_agent_run_service(request: Request) -> AgentRunService:
    """Resolve the agent-runs service from the container."""

    return (await get_container(request)).modules.agent_runs.service


async def get_system_service(request: Request) -> SystemService:
    """Resolve the system service from the container."""

    return (await get_container(request)).modules.system.service


async def get_company_profile_service(request: Request) -> CompanyProfileService:
    """Resolve the company profile service from the container."""

    return (await get_container(request)).modules.company_profile.service


async def get_session_service(request: Request) -> SessionService:
    """Resolve the sessions service from the container."""

    return (await get_container(request)).modules.sessions.service


async def get_jobs_service(request: Request) -> JobsService:
    """Resolve the jobs service from the container."""

    return (await get_container(request)).modules.jobs.service


async def get_worker_run_service(request: Request) -> WorkerRunService:
    """Resolve the worker-runs service from the container."""

    return (await get_container(request)).modules.worker_runs.service
