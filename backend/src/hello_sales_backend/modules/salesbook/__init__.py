"""Salesbook module public API. /Oliviercontribution."""

from hello_sales_backend.modules.salesbook.bootstrap import (
    SalesbookModule,
    build_salesbook_module,
)
from hello_sales_backend.modules.salesbook.use_cases.salesbook_service import (
    SalesbookService,
)
from hello_sales_backend.modules.salesbook.use_cases.views import (
    ClientContactUpsertRequest,
    ClientContactView,
    EngagementLogCreateRequest,
    EngagementLogView,
    OnboardingBatchSubmit,
    OnboardingProgressView,
    OnboardingResponseSubmit,
    OnboardingResponseView,
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
    PipelineDealView,
    SalesbookExhaustiveOnboardingEntry,
    SalesbookExhaustiveProductEntry,
    SalesbookExhaustiveView,
    TeamMembershipCreateRequest,
    TeamMembershipView,
)

__all__ = [
    "SalesbookModule",
    "SalesbookService",
    "build_salesbook_module",
    "ClientContactUpsertRequest",
    "ClientContactView",
    "EngagementLogCreateRequest",
    "EngagementLogView",
    "OnboardingBatchSubmit",
    "OnboardingProgressView",
    "OnboardingResponseSubmit",
    "OnboardingResponseView",
    "PipelineDealCreateRequest",
    "PipelineDealUpdateRequest",
    "PipelineDealView",
    "SalesbookExhaustiveOnboardingEntry",
    "SalesbookExhaustiveProductEntry",
    "SalesbookExhaustiveView",
    "TeamMembershipCreateRequest",
    "TeamMembershipView",
]
