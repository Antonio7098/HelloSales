"""Jobs endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from hello_sales_backend.entrypoints.http.dependencies import (
    get_jobs_service,
    require_permissions,
)
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.jobs import JobsService
from hello_sales_backend.modules.jobs.use_cases.commands import StartDiagnosticJobCommand
from hello_sales_backend.shared.auth import (
    APP_ACCESS_PERMISSION,
    JOBS_READ_PERMISSION,
    JOBS_RUN_PERMISSION,
    AuthContext,
)

router = APIRouter()
ReadDep = Annotated[AuthContext, Depends(require_permissions(APP_ACCESS_PERMISSION, JOBS_READ_PERMISSION))]
RunDep = Annotated[AuthContext, Depends(require_permissions(APP_ACCESS_PERMISSION, JOBS_RUN_PERMISSION))]


@router.get("/tasks", response_model=ApiEnvelope)
async def list_tasks(
    _auth: ReadDep,
    service: JobsService = Depends(get_jobs_service),
) -> ApiEnvelope:
    return ok_response(service.list_tasks())


@router.get("/tasks/{task_id}", response_model=ApiEnvelope)
async def get_task(
    task_id: str,
    _auth: ReadDep,
    service: JobsService = Depends(get_jobs_service),
) -> ApiEnvelope:
    return ok_response(service.get_task(task_id))


@router.post("/diagnostic", response_model=ApiEnvelope)
async def start_diagnostic_job(
    request: Request,
    command: StartDiagnosticJobCommand,
    auth_context: RunDep,
    service: JobsService = Depends(get_jobs_service),
) -> ApiEnvelope:
    return ok_response(
        service.start_diagnostic_job(
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            actor_id=auth_context.actor_id,
            command=command,
        )
    )
