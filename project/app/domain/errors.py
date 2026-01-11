"""Typed error hierarchy for HelloSales.

All application errors inherit from AppError and provide:
- code: Machine-readable error code
- message: Human-readable description
- details: Additional context as dict
- retryable: Whether the operation can be retried
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AppError(Exception):
    """Base application error with full context."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __post_init__(self) -> None:
        super().__init__(str(self))

    def to_dict(self) -> dict[str, Any]:
        """Serialize error for API responses and logging."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat(),
        }


# --- Not Found Errors ---


@dataclass
class NotFoundError(AppError):
    """Resource not found."""

    code: str = "NOT_FOUND"
    retryable: bool = False


@dataclass
class UserNotFoundError(NotFoundError):
    """User not found."""

    code: str = "USER_NOT_FOUND"


@dataclass
class OrganizationNotFoundError(NotFoundError):
    """Organization not found."""

    code: str = "ORGANIZATION_NOT_FOUND"


@dataclass
class SessionNotFoundError(NotFoundError):
    """Session not found."""

    code: str = "SESSION_NOT_FOUND"


@dataclass
class InteractionNotFoundError(NotFoundError):
    """Interaction not found."""

    code: str = "INTERACTION_NOT_FOUND"


@dataclass
class ProductNotFoundError(NotFoundError):
    """Product not found."""

    code: str = "PRODUCT_NOT_FOUND"


@dataclass
class ClientNotFoundError(NotFoundError):
    """Client not found."""

    code: str = "CLIENT_NOT_FOUND"


@dataclass
class ScriptNotFoundError(NotFoundError):
    """Sales script not found."""

    code: str = "SCRIPT_NOT_FOUND"


@dataclass
class EmailNotFoundError(NotFoundError):
    """Sales email not found."""

    code: str = "EMAIL_NOT_FOUND"


# --- Validation Errors ---


@dataclass
class ValidationError(AppError):
    """Input validation failed."""

    code: str = "VALIDATION_ERROR"
    retryable: bool = False


@dataclass
class InvalidStateError(ValidationError):
    """Invalid state transition."""

    code: str = "INVALID_STATE"


@dataclass
class GuardBlockedError(ValidationError):
    """Input/output blocked by guardrails."""

    code: str = "GUARD_BLOCKED"
    category: str = ""
    blocked_content: str = ""


@dataclass
class DuplicateError(ValidationError):
    """Duplicate resource."""

    code: str = "DUPLICATE_ERROR"


# --- Auth Errors ---


@dataclass
class AuthError(AppError):
    """Authentication/authorization failed."""

    code: str = "AUTH_ERROR"
    retryable: bool = False


@dataclass
class TokenExpiredError(AuthError):
    """JWT token has expired."""

    code: str = "TOKEN_EXPIRED"
    retryable: bool = True  # Can retry with fresh token


@dataclass
class TokenInvalidError(AuthError):
    """JWT token is invalid."""

    code: str = "TOKEN_INVALID"


@dataclass
class InsufficientPermissionsError(AuthError):
    """User lacks required permissions."""

    code: str = "INSUFFICIENT_PERMISSIONS"


@dataclass
class OrganizationAccessDeniedError(AuthError):
    """User does not have access to this organization."""

    code: str = "ORG_ACCESS_DENIED"


# --- Provider Errors ---


@dataclass
class ProviderError(AppError):
    """External provider failed."""

    code: str = "PROVIDER_ERROR"
    provider: str = ""
    operation: str = ""


@dataclass
class ProviderTimeoutError(ProviderError):
    """Provider call timed out."""

    code: str = "PROVIDER_TIMEOUT"
    retryable: bool = True


@dataclass
class ProviderRateLimitError(ProviderError):
    """Provider rate limit exceeded."""

    code: str = "PROVIDER_RATE_LIMITED"
    retryable: bool = True
    retry_after_seconds: int = 60


@dataclass
class ProviderUnavailableError(ProviderError):
    """Provider is unavailable."""

    code: str = "PROVIDER_UNAVAILABLE"
    retryable: bool = True


@dataclass
class ProviderInvalidRequestError(ProviderError):
    """Invalid request to provider."""

    code: str = "PROVIDER_INVALID_REQUEST"
    retryable: bool = False


# --- Pipeline Errors ---


@dataclass
class PipelineError(AppError):
    """Pipeline execution failed."""

    code: str = "PIPELINE_ERROR"
    stage: str = ""
    pipeline_run_id: str = ""


@dataclass
class StageFailedError(PipelineError):
    """A stage in the pipeline failed."""

    code: str = "STAGE_FAILED"


@dataclass
class PipelineCancelledError(PipelineError):
    """Pipeline was cancelled (not necessarily an error)."""

    code: str = "PIPELINE_CANCELLED"
    retryable: bool = False
    cancel_reason: str = ""


@dataclass
class PipelineTimeoutError(PipelineError):
    """Pipeline execution timed out."""

    code: str = "PIPELINE_TIMEOUT"
    retryable: bool = True


# --- Database Errors ---


@dataclass
class DatabaseError(AppError):
    """Database operation failed."""

    code: str = "DATABASE_ERROR"
    operation: str = ""


@dataclass
class ConnectionError(DatabaseError):
    """Database connection failed."""

    code: str = "DB_CONNECTION_ERROR"
    retryable: bool = True


@dataclass
class TransactionError(DatabaseError):
    """Database transaction failed."""

    code: str = "DB_TRANSACTION_ERROR"
    retryable: bool = True
