"""Ports for company profile use cases."""

from __future__ import annotations

from typing import Protocol

from hello_sales_backend.modules.company_profile.use_cases.views import (
    CompanyProfileUpsertRequest,
    CompanyProfileView,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductView,
)


class CompanyProfileRepositoryPort(Protocol):
    """Persistence capabilities required by company profile use cases."""

    async def get_company_profile(self) -> CompanyProfileView | None: ...

    async def upsert_company_profile(self, request: CompanyProfileUpsertRequest) -> CompanyProfileView: ...

    async def list_products(self) -> list[ProductView]: ...

    async def get_product(self, product_id: str) -> ProductView | None: ...

    async def create_product(self, request: ProductCreateRequest) -> ProductView: ...

    async def update_product(self, product_id: str, request: ProductUpdateRequest) -> ProductView | None: ...

    async def delete_product(self, product_id: str) -> bool: ...
