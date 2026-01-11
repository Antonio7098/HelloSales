"""Repository implementations."""

from app.infrastructure.repositories.base import BaseRepository, OrgScopedRepository
from app.infrastructure.repositories.client_repository import ClientRepositoryImpl
from app.infrastructure.repositories.company_profile_repository import (
    CompanyProfileRepositoryImpl,
)
from app.infrastructure.repositories.interaction_repository import (
    InteractionRepositoryImpl,
)
from app.infrastructure.repositories.organization_repository import (
    OrganizationMembershipRepositoryImpl,
    OrganizationRepositoryImpl,
)
from app.infrastructure.repositories.product_repository import ProductRepositoryImpl
from app.infrastructure.repositories.sales_email_repository import (
    SalesEmailRepositoryImpl,
)
from app.infrastructure.repositories.sales_script_repository import (
    SalesScriptRepositoryImpl,
)
from app.infrastructure.repositories.session_repository import SessionRepositoryImpl
from app.infrastructure.repositories.user_repository import UserRepositoryImpl

__all__ = [
    "BaseRepository",
    "OrgScopedRepository",
    "ClientRepositoryImpl",
    "CompanyProfileRepositoryImpl",
    "InteractionRepositoryImpl",
    "OrganizationMembershipRepositoryImpl",
    "OrganizationRepositoryImpl",
    "ProductRepositoryImpl",
    "SalesEmailRepositoryImpl",
    "SalesScriptRepositoryImpl",
    "SessionRepositoryImpl",
    "UserRepositoryImpl",
]
