"""Salesbook domain exceptions. /Oliviercontribution."""

from __future__ import annotations

from hello_sales_backend.shared.errors import AppError


class SalesbookError(AppError):
    """Base for salesbook domain errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 404,
        severity: str = "warning",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            category="domain",
            status_code=status_code,
            severity=severity,
            details=details or {},
            operation="salesbook.request",
            component="salesbook",
        )


class UnknownProfileError(SalesbookError):
    """Raised when a salesbook operation references a non-existent company_profile."""

    def __init__(self, profile_id: str) -> None:
        super().__init__(
            message=f"profile not found: {profile_id}",
            code="salesbook.profile.not_found",
            details={"profile_id": profile_id},
        )


class UnknownDealError(SalesbookError):
    """Raised when a pipeline operation targets a deal that does not exist."""

    def __init__(self, deal_id: str) -> None:
        super().__init__(
            message=f"deal not found: {deal_id}",
            code="salesbook.deal.not_found",
            details={"deal_id": deal_id},
        )


class UnknownMembershipError(SalesbookError):
    """Raised when a team-membership operation targets a row that does not exist."""

    def __init__(self, membership_id: str) -> None:
        super().__init__(
            message=f"membership not found: {membership_id}",
            code="salesbook.membership.not_found",
            details={"membership_id": membership_id},
        )


class UnknownCommentError(SalesbookError):
    """Raised when a moderation operation targets a comment that does not exist."""

    def __init__(self, comment_id: str) -> None:
        super().__init__(
            message=f"comment not found: {comment_id}",
            code="salesbook.comment.not_found",
            details={"comment_id": comment_id},
        )


class UnknownQuestionKeyError(SalesbookError):
    """Raised when a submitted onboarding response uses a question_key not in the registry."""

    def __init__(self, question_key: str) -> None:
        super().__init__(
            message=f"question_key not found in registry: {question_key}",
            code="salesbook.question_key.not_found",
            status_code=400,
            details={"question_key": question_key},
        )


class InvalidPhaseError(SalesbookError):
    """Raised when a phase value is outside {1, 2, 3}."""

    def __init__(self, phase: int) -> None:
        super().__init__(
            message=f"invalid phase value: {phase}",
            code="salesbook.phase.invalid",
            status_code=400,
            details={"phase": phase},
        )


__all__ = [
    "SalesbookError",
    "UnknownProfileError",
    "UnknownDealError",
    "UnknownMembershipError",
    "UnknownCommentError",
    "UnknownQuestionKeyError",
    "InvalidPhaseError",
]
