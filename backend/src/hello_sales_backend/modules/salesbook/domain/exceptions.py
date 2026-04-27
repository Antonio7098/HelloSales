"""Salesbook domain exceptions. /Oliviercontribution."""

from __future__ import annotations


class SalesbookError(Exception):
    """Base for salesbook domain errors."""


class UnknownProfileError(SalesbookError):
    """Raised when a salesbook operation references a non-existent company_profile."""


class UnknownDealError(SalesbookError):
    """Raised when a pipeline operation targets a deal that does not exist."""


class UnknownMembershipError(SalesbookError):
    """Raised when a team-membership operation targets a row that does not exist."""


class UnknownQuestionKeyError(SalesbookError):
    """Raised when a submitted onboarding response uses a question_key not in the registry."""


class InvalidPhaseError(SalesbookError):
    """Raised when a phase value is outside {1, 2, 3}."""


__all__ = [
    "SalesbookError",
    "UnknownProfileError",
    "UnknownDealError",
    "UnknownMembershipError",
    "UnknownQuestionKeyError",
    "InvalidPhaseError",
]
