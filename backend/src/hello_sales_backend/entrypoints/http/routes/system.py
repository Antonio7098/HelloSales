"""System status endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from hello_sales_backend.entrypoints.http.dependencies import (
    get_system_service,
    require_permissions,
)
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.system import SystemService
from hello_sales_backend.shared.auth import APP_ACCESS_PERMISSION, SYSTEM_READ_PERMISSION

router = APIRouter()
ReadDep = Annotated[object, Depends(require_permissions(APP_ACCESS_PERMISSION, SYSTEM_READ_PERMISSION))]


@router.get("/status", response_model=ApiEnvelope)
async def system_status(
    _auth: ReadDep,
    service: SystemService = Depends(get_system_service),
) -> ApiEnvelope:
    return ok_response(await service.get_status())


@router.get("/diagnostics", response_model=ApiEnvelope)
async def system_diagnostics(
    _auth: ReadDep,
    service: SystemService = Depends(get_system_service),
) -> ApiEnvelope:
    return ok_response(await service.get_diagnostics())
