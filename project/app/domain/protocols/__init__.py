"""Domain protocols - abstract interfaces for infrastructure implementations."""

from app.domain.protocols.providers import LLMProvider
from app.domain.protocols.repositories import (
    ClientRepository,
    CompanyProfileRepository,
    InteractionRepository,
    OrganizationRepository,
    ProductRepository,
    SalesEmailRepository,
    SalesScriptRepository,
    SessionRepository,
    SummaryRepository,
    UserRepository,
)

__all__ = [
    # Repositories
    "UserRepository",
    "OrganizationRepository",
    "CompanyProfileRepository",
    "SessionRepository",
    "SummaryRepository",
    "InteractionRepository",
    "ProductRepository",
    "ClientRepository",
    "SalesScriptRepository",
    "SalesEmailRepository",
    # Providers
    "LLMProvider",
]
