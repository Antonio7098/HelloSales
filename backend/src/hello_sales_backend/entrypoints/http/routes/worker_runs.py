"""Worker-runs endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from hello_sales_backend.entrypoints.http.dependencies import (
    get_worker_run_service,
    require_permissions,
)
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.worker_runs import WorkerRunService
from hello_sales_backend.modules.worker_runs.use_cases.commands import StartWorkerRunCommand
from hello_sales_backend.shared.auth import (
    APP_ACCESS_PERMISSION,
    WORKERS_CANCEL_PERMISSION,
    WORKERS_READ_PERMISSION,
    WORKERS_RUN_PERMISSION,
    AuthContext,
)

router = APIRouter()
WorkerRunServiceDep = Annotated[WorkerRunService, Depends(get_worker_run_service)]
RunDep = Annotated[AuthContext, Depends(require_permissions(APP_ACCESS_PERMISSION, WORKERS_RUN_PERMISSION))]
ReadDep = Annotated[AuthContext, Depends(require_permissions(APP_ACCESS_PERMISSION, WORKERS_READ_PERMISSION))]
CancelDep = Annotated[
    AuthContext,
    Depends(require_permissions(APP_ACCESS_PERMISSION, WORKERS_CANCEL_PERMISSION)),
]


@router.post("", response_model=ApiEnvelope)
async def start_worker_run(
    request: Request,
    command: StartWorkerRunCommand,
    auth_context: RunDep,
    service: WorkerRunServiceDep,
) -> ApiEnvelope:
    return ok_response(
        await service.start_run(
            request_id=getattr(request.state, "request_id", None),
            trace_id=getattr(request.state, "trace_id", None),
            actor_id=auth_context.actor_id,
            command=command,
        )
    )


@router.get("/{run_id}", response_model=ApiEnvelope)
async def get_worker_run(run_id: str, _auth: ReadDep, service: WorkerRunServiceDep) -> ApiEnvelope:
    return ok_response(await service.get_run(run_id))


@router.get("/{run_id}/events", response_model=ApiEnvelope)
async def get_worker_run_events(
    run_id: str,
    _auth: ReadDep,
    service: WorkerRunServiceDep,
) -> ApiEnvelope:
    return ok_response(await service.list_events(run_id))


@router.post("/{run_id}/cancel", response_model=ApiEnvelope)
async def cancel_worker_run(
    run_id: str,
    _auth: CancelDep,
    service: WorkerRunServiceDep,
) -> ApiEnvelope:
    return ok_response(await service.cancel_run(run_id))
