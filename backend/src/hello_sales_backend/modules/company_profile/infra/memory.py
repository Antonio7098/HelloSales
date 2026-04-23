"""In-memory repository for company profile data."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from hello_sales_backend.modules.company_profile.use_cases.ports import CompanyProfileRepositoryPort
from hello_sales_backend.modules.company_profile.use_cases.views import (
    CompanyProfileUpsertRequest,
    CompanyProfileView,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductView,
)


def _now() -> datetime:
    return datetime.now(UTC)


class InMemoryCompanyProfileRepository(CompanyProfileRepositoryPort):
    """Keep company profile data in process memory for SQLite-backed test paths."""

    def __init__(self) -> None:
        self._company_profile: CompanyProfileView | None = None
        self._products: dict[str, ProductView] = {}

    async def get_company_profile(self) -> CompanyProfileView | None:
        return self._company_profile.model_copy(deep=True) if self._company_profile else None

    async def upsert_company_profile(self, request: CompanyProfileUpsertRequest) -> CompanyProfileView:
        timestamp = _now()
        profile_id = self._company_profile.profile_id if self._company_profile else uuid4().hex
        created_at = self._company_profile.created_at if self._company_profile else timestamp
        self._company_profile = CompanyProfileView(
            profile_id=profile_id,
            created_at=created_at,
            updated_at=timestamp,
            **request.model_dump(),
        )
        return self._company_profile.model_copy(deep=True)

    async def list_products(self) -> list[ProductView]:
        return [product.model_copy(deep=True) for product in self._products.values()]

    async def get_product(self, product_id: str) -> ProductView | None:
        product = self._products.get(product_id)
        return product.model_copy(deep=True) if product else None

    async def create_product(self, request: ProductCreateRequest) -> ProductView:
        if self._company_profile is None:
            raise RuntimeError("company profile is required before products can be created")
        timestamp = _now()
        product = ProductView(
            product_id=uuid4().hex,
            company_profile_id=self._company_profile.profile_id,
            created_at=timestamp,
            updated_at=timestamp,
            **request.model_dump(),
        )
        self._products[product.product_id] = product
        return product.model_copy(deep=True)

    async def update_product(self, product_id: str, request: ProductUpdateRequest) -> ProductView | None:
        product = self._products.get(product_id)
        if product is None:
            return None
        update_data = request.model_dump(exclude_unset=True)
        updated = product.model_copy(update={**update_data, "updated_at": _now()})
        self._products[product_id] = updated
        return updated.model_copy(deep=True)

    async def delete_product(self, product_id: str) -> bool:
        return self._products.pop(product_id, None) is not None
