"""Company profile application service."""

from __future__ import annotations

from hello_sales_backend.modules.company_profile.use_cases.ports import CompanyProfileRepositoryPort
from hello_sales_backend.modules.company_profile.use_cases.views import (
    CompanyContextView,
    CompanyProfileUpsertRequest,
    CompanyProfileView,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductView,
)
from hello_sales_backend.shared.errors import app_error


class CompanyProfileService:
    """Expose company profile and product data through a stable module facade."""

    def __init__(self, *, repository: CompanyProfileRepositoryPort) -> None:
        self._repository = repository

    async def get_company_profile(self) -> CompanyProfileView | None:
        return await self._repository.get_company_profile()

    async def upsert_company_profile(self, request: CompanyProfileUpsertRequest) -> CompanyProfileView:
        return await self._repository.upsert_company_profile(request)

    async def get_company_context(self) -> CompanyContextView:
        return CompanyContextView(
            company_profile=await self._repository.get_company_profile(),
            products=await self._repository.list_products(),
        )

    async def list_products(self) -> list[ProductView]:
        return await self._repository.list_products()

    async def create_product(self, request: ProductCreateRequest) -> ProductView:
        profile = await self._repository.get_company_profile()
        if profile is None:
            raise app_error(
                "Create a company profile before adding products",
                code="company_profile.required",
                category="validation",
                status_code=409,
                severity="warning",
                details={},
                operation="company_profile.create_product",
                component="company_profile",
            )
        return await self._repository.create_product(request)

    async def get_product(self, product_id: str) -> ProductView:
        product = await self._repository.get_product(product_id)
        if product is None:
            raise self._not_found(product_id)
        return product

    async def update_product(self, product_id: str, request: ProductUpdateRequest) -> ProductView:
        product = await self._repository.update_product(product_id, request)
        if product is None:
            raise self._not_found(product_id)
        return product

    async def delete_product(self, product_id: str) -> dict[str, bool]:
        deleted = await self._repository.delete_product(product_id)
        if not deleted:
            raise self._not_found(product_id)
        return {"deleted": True}

    @staticmethod
    def _not_found(product_id: str) -> Exception:
        return app_error(
            "Product was not found",
            code="product.not_found",
            category="not_found",
            status_code=404,
            severity="warning",
            details={"product_id": product_id},
            operation="company_profile.product_lookup",
            component="company_profile",
        )
