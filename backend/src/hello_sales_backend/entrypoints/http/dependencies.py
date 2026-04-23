"""FastAPI dependency helpers."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from hello_sales_backend.modules.agent_runs import AgentRunService
from hello_sales_backend.modules.company_profile import CompanyProfileService
from hello_sales_backend.modules.jobs import JobsService
from hello_sales_backend.modules.sessions import SessionService
from hello_sales_backend.modules.system import SystemService
from hello_sales_backend.modules.worker_runs import WorkerRunService
from hello_sales_backend.platform.composition.app_container import AppContainer
from hello_sales_backend.platform.observability.health import HealthService


async def get_container(request: Request) -> AppContainer:
    """Return the application container."""

    return cast(AppContainer, request.app.state.container)


async def get_health_service(request: Request) -> HealthService:
    """Resolve the health service from the container."""

    return (await get_container(request)).health_service


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
