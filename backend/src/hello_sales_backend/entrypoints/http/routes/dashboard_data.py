"""Dashboard data endpoints."""

from fastapi import APIRouter, Depends

from hello_sales_backend.entrypoints.http.dependencies import get_dashboard_data_service
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.dashboard_data import DashboardDataService

router = APIRouter()


@router.get("/entries", response_model=ApiEnvelope)
async def list_dashboard_entries(
    service: DashboardDataService = Depends(get_dashboard_data_service),
) -> ApiEnvelope:
    return ok_response(await service.list_entries())
