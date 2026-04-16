"""Structured application error models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

from hello_sales_backend.platform.observability.redaction import redact_mapping


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        normalized = {str(key): _normalize_value(item) for key, item in value.items()}
        return redact_mapping(normalized)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, BaseException):
        return {
            "type": value.__class__.__name__,
            "message": str(value),
        }
    return str(value)


def normalize_details(details: Mapping[str, object] | None = None) -> dict[str, object]:
    """Normalize and redact arbitrary detail payloads."""

    if not details:
        return {}
    return {str(key): _normalize_value(value) for key, value in details.items()}


def build_cause(exc: BaseException | None) -> dict[str, object] | None:
    """Return a normalized cause payload."""

    if exc is None:
        return None
    return {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }


def build_causal_chain(exc: BaseException | None) -> list[dict[str, object]]:
    """Return the exception cause chain from nearest to farthest."""

    chain: list[dict[str, object]] = []
    cursor = exc
    while cursor is not None:
        chain.append({"type": cursor.__class__.__name__, "message": str(cursor)})
        cursor = cursor.__cause__
    return chain


@dataclass(slots=True)
class AppError(Exception):
    """Structured application error."""

    message: str
    code: str
    category: str
    status_code: int = 500
    severity: str = "error"
    retryable: bool = False
    details: dict[str, object] = field(default_factory=dict)
    operation: str | None = None
    component: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    cause: dict[str, object] | None = None
    causes: list[dict[str, object]] = field(default_factory=list)
    timestamp: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        super().__init__(self.message)
        self.details = normalize_details(self.details)

    def with_context(
        self,
        *,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> AppError:
        """Return a copy with request context attached."""

        return AppError(
            message=self.message,
            code=self.code,
            category=self.category,
            status_code=self.status_code,
            severity=self.severity,
            retryable=self.retryable,
            details=self.details,
            operation=self.operation,
            component=self.component,
            correlation_id=correlation_id or self.correlation_id,
            trace_id=trace_id or self.trace_id,
            cause=self.cause,
            causes=list(self.causes),
            timestamp=self.timestamp,
        )

    def to_dict(self) -> dict[str, object | None]:
        """Return the canonical error payload."""

        return {
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "severity": self.severity,
            "retryable": self.retryable,
            "operation": self.operation,
            "component": self.component,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "cause": self.cause,
            "causes": self.causes,
            "timestamp": self.timestamp,
        }


def app_error(
    message: str,
    *,
    code: str,
    category: str,
    status_code: int = 500,
    severity: str = "error",
    retryable: bool = False,
    details: Mapping[str, object] | None = None,
    operation: str | None = None,
    component: str | None = None,
    exc: BaseException | None = None,
) -> AppError:
    """Create a structured application error with normalized cause data."""

    return AppError(
        message=message,
        code=code,
        category=category,
        status_code=status_code,
        severity=severity,
        retryable=retryable,
        details=normalize_details(details),
        operation=operation,
        component=component,
        cause=build_cause(exc),
        causes=build_causal_chain(exc.__cause__) if exc is not None and exc.__cause__ is not None else [],
    )


def orchestration_error(
    message: str,
    *,
    code: str,
    status_code: int = 500,
    details: Mapping[str, object] | None = None,
    exc: BaseException | None = None,
) -> AppError:
    """Create an orchestration-specific application error."""

    return app_error(
        message,
        code=code,
        category="workflow",
        status_code=status_code,
        details=details,
        operation="workflow.runtime",
        component="workflow",
        exc=exc,
    )


def internal_error(
    message: str,
    *,
    code: str = "internal.unhandled_exception",
    details: Mapping[str, object] | None = None,
    operation: str | None = None,
    component: str | None = None,
    exc: BaseException | None = None,
) -> AppError:
    """Create a structured error for unexpected internal failures."""

    return app_error(
        message,
        code=code,
        category="internal",
        status_code=500,
        severity="critical",
        details=details,
        operation=operation,
        component=component,
        exc=exc,
    )
