"""Domain entities - pure Python dataclasses representing business objects."""

from app.domain.entities.client import Client
from app.domain.entities.company_profile import CompanyProfile
from app.domain.entities.interaction import Interaction
from app.domain.entities.organization import Organization, OrganizationMembership
from app.domain.entities.product import Product
from app.domain.entities.sales_email import SalesEmail
from app.domain.entities.sales_script import SalesScript
from app.domain.entities.session import Session, SessionSummary, SummaryState
from app.domain.entities.user import User

__all__ = [
    "User",
    "Organization",
    "OrganizationMembership",
    "CompanyProfile",
    "Session",
    "SessionSummary",
    "SummaryState",
    "Interaction",
    "Product",
    "Client",
    "SalesScript",
    "SalesEmail",
]
