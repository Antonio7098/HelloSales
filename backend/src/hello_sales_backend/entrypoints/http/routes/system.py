"""System status endpoints."""

from fastapi import APIRouter, Depends

from hello_sales_backend.entrypoints.http.dependencies import get_system_service
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.system import SystemService

router = APIRouter()


@router.get("/status", response_model=ApiEnvelope)
async def system_status(
    service: SystemService = Depends(get_system_service),
) -> ApiEnvelope:
    return ok_response(await service.get_status())


@router.get("/diagnostics", response_model=ApiEnvelope)
async def system_diagnostics(
    service: SystemService = Depends(get_system_service),
) -> ApiEnvelope:
    return ok_response(await service.get_diagnostics())
