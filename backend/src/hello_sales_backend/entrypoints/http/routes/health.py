"""Health endpoints."""

from fastapi import APIRouter, Depends, Response

from hello_sales_backend.entrypoints.http.dependencies import get_health_service
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.platform.observability.health import HealthService

router = APIRouter()


@router.get("/liveness", response_model=ApiEnvelope)
async def liveness(service: HealthService = Depends(get_health_service)) -> ApiEnvelope:
    return ok_response(await service.liveness())


@router.get("/readiness", response_model=ApiEnvelope)
async def readiness(
    response: Response,
    service: HealthService = Depends(get_health_service),
) -> ApiEnvelope:
    payload = await service.readiness()
    response.status_code = 200 if payload.status in {"ready", "degraded"} else 503
    return ok_response(payload)
