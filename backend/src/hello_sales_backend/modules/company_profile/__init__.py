"""Company profile data module public API."""

from hello_sales_backend.modules.company_profile.bootstrap import (
    CompanyProfileModule,
    build_company_profile_module,
)
from hello_sales_backend.modules.company_profile.use_cases.company_profile_service import (
    CompanyProfileService,
)
from hello_sales_backend.modules.company_profile.use_cases.views import (
    CompanyContextView,
    CompanyProfileUpsertRequest,
    CompanyProfileView,
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductView,
)

__all__ = [
    "CompanyProfileModule",
    "CompanyProfileService",
    "CompanyContextView",
    "CompanyProfileUpsertRequest",
    "CompanyProfileView",
    "ProductCreateRequest",
    "ProductUpdateRequest",
    "ProductView",
    "build_company_profile_module",
]
