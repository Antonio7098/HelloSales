"""Company profile and product endpoints."""

from fastapi import APIRouter, Depends

from hello_sales_backend.entrypoints.http.dependencies import get_company_profile_service
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.company_profile import CompanyProfileService
from hello_sales_backend.modules.company_profile.use_cases.views import (
    CompanyProfileUpsertRequest,
    ProductCreateRequest,
    ProductUpdateRequest,
)

router = APIRouter()


@router.get("/company-profile", response_model=ApiEnvelope)
async def get_company_profile(
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.get_company_profile())


@router.put("/company-profile", response_model=ApiEnvelope)
async def upsert_company_profile(
    request: CompanyProfileUpsertRequest,
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.upsert_company_profile(request))


@router.get("/company-context", response_model=ApiEnvelope)
async def get_company_context(
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.get_company_context())


@router.get("/products", response_model=ApiEnvelope)
async def list_products(
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.list_products())


@router.post("/products", response_model=ApiEnvelope)
async def create_product(
    request: ProductCreateRequest,
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.create_product(request))


@router.get("/products/{product_id}", response_model=ApiEnvelope)
async def get_product(
    product_id: str,
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.get_product(product_id))


@router.patch("/products/{product_id}", response_model=ApiEnvelope)
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.update_product(product_id, request))


@router.delete("/products/{product_id}", response_model=ApiEnvelope)
async def delete_product(
    product_id: str,
    service: CompanyProfileService = Depends(get_company_profile_service),
) -> ApiEnvelope:
    return ok_response(await service.delete_product(product_id))
