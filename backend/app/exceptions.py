"""Custom exceptions for the application.

This module defines application-specific exceptions with structured
error codes and metadata for consistent error handling across the API.

Exception Hierarchy:
- AppError (base)
  ├── NotFoundError
  │   ├── SessionNotFoundError
  │   ├── SessionStateNotFoundError
  │   └── ...
  ├── ValidationError
  │   ├── InvalidSessionStateError
  │   └── ...
  ├── ConfigurationError
  └── ...

Usage:
    try:
        state = await session_state_service.get(session_id)
    except SessionStateNotFoundError:
        # Handle missing state
        pass
    except InvalidSessionStateError as e:
        # Handle invalid value
        log.error(f"Invalid {e.field}: {e.value}, valid={e.valid_values}")
        raise

Attributes:
    code: Machine-readable error code (e.g., "SESSION_NOT_FOUND")
    message: Human-readable error message
    details: Additional context for debugging
    retryable: Whether the operation can be retried
"""

from __future__ import annotations

from dataclasses import field
from datetime import datetime
from typing import Any
from uuid import UUID


class AppError(Exception):
    """Base exception for application errors.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        details: Additional context for debugging
        retryable: Whether the operation can be retried
        timestamp: When the error occurred
    """

    code: str = "APP_ERROR"
    message: str = "An unexpected error occurred"
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        """Initialize error with optional message and details."""
        self.message = message or self.message
        self.details = details or {}
        self.retryable = retryable
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "retryable": self.retryable,
                "timestamp": self.timestamp.isoformat(),
            }
        }

    def __str__(self) -> str:
        """String representation with code."""
        return f"[{self.code}] {self.message}"


class NotFoundError(AppError):
    """Base exception for resource not found errors."""

    code = "NOT_FOUND"
    message = "Resource not found"

    def __init__(
        self,
        resource: str,
        identifier: str | UUID,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize not found error."""
        self.resource = resource
        self.identifier = identifier
        full_details = {"resource": resource, "identifier": str(identifier)}
        if details:
            full_details.update(details)
        super().__init__(
            message=f"{resource} not found: {identifier}",
            details=full_details,
        )


class SessionNotFoundError(NotFoundError):
    """Raised when a session is not found."""

    code = "SESSION_NOT_FOUND"
    message = "Session not found"

    def __init__(self, session_id: UUID) -> None:
        """Initialize session not found error."""
        super().__init__(
            resource="Session",
            identifier=session_id,
        )


class SessionStateNotFoundError(NotFoundError):
    """Raised when session state is not found.

    This typically indicates the session state row was deleted or
    never created for the session.
    """

    code = "SESSION_STATE_NOT_FOUND"
    message = "Session state not found"

    def __init__(self, session_id: UUID) -> None:
        """Initialize session state not found error."""
        super().__init__(
            resource="SessionState",
            identifier=session_id,
            details={
                "hint": "Session state should be created when session is opened"
            },
        )


class ValidationError(AppError):
    """Base exception for validation errors."""

    code = "VALIDATION_ERROR"
    message = "Validation failed"
    retryable = False


class InvalidSessionStateError(ValidationError):
    """Raised when session state has invalid values.

    Attributes:
        field: The field that has invalid value (e.g., "topology", "behavior")
        value: The invalid value that was provided
        valid_values: List of valid values for the field
    """

    code = "INVALID_SESSION_STATE"
    message = "Invalid session state value"

    def __init__(
        self,
        field: str,
        value: Any,
        valid_values: list[Any],
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize invalid session state error."""
        self.field = field
        self.value = value
        self.valid_values = valid_values
        full_details = {
            "field": field,
            "value": value,
            "valid_values": valid_values,
        }
        if details:
            full_details.update(details)
        super().__init__(
            message=f"Invalid session state: {field}={value!r}. "
            f"Valid values: {valid_values}",
            details=full_details,
        )


class SessionStateConflictError(AppError):
    """Raised when session state update conflicts with concurrent modification.

    This can happen when two requests try to update the same session state
    simultaneously. The client should refresh and retry.
    """

    code = "SESSION_STATE_CONFLICT"
    message = "Session state was modified by another request"
    retryable = True

    def __init__(
        self,
        session_id: UUID,
        expected_version: datetime,
        actual_version: datetime,
    ) -> None:
        """Initialize conflict error."""
        self.session_id = session_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            message=f"Session state {session_id} was modified by another request. "
            f"Expected: {expected_version}, Actual: {actual_version}",
            details={
                "session_id": str(session_id),
                "expected_version": expected_version.isoformat(),
                "actual_version": actual_version.isoformat(),
            },
        )


class ConfigurationError(AppError):
    """Base exception for configuration errors."""

    code = "CONFIGURATION_ERROR"
    message = "Invalid configuration"


class TopologyNotSupportedError(ConfigurationError):
    """Raised when a topology is not supported by the system.

    This can happen when a pipeline requests an unsupported kernel/channel
    combination.
    """

    code = "TOPOLOGY_NOT_SUPPORTED"
    message = "Topology not supported"

    def __init__(
        self,
        topology: str,
        supported_topologies: list[str],
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize topology not supported error."""
        self.topology = topology
        self.supported_topologies = supported_topologies
        full_details = {
            "topology": topology,
            "supported_topologies": supported_topologies,
        }
        if details:
            full_details.update(details)
        super().__init__(
            message=f"Topology '{topology}' is not supported. "
            f"Supported: {supported_topologies}",
            details=full_details,
        )


class BehaviorNotAllowedError(ConfigurationError):
    """Raised when a behavior is not allowed for the session.

    This can happen when a user tries to set a behavior that requires
    specific entitlements or subscription level.
    """

    code = "BEHAVIOR_NOT_ALLOWED"
    message = "Behavior not allowed"

    def __init__(
        self,
        behavior: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize behavior not allowed error."""
        self.behavior = behavior
        self.reason = reason
        full_details = {
            "behavior": behavior,
            "reason": reason,
        }
        if details:
            full_details.update(details)
        super().__init__(
            message=f"Behavior '{behavior}' is not allowed: {reason}",
            details=full_details,
        )


__all__ = [
    "AppError",
    "NotFoundError",
    "SessionNotFoundError",
    "SessionStateNotFoundError",
    "ValidationError",
    "InvalidSessionStateError",
    "SessionStateConflictError",
    "ConfigurationError",
    "TopologyNotSupportedError",
    "BehaviorNotAllowedError",
]
