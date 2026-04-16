"""Shared HTTP response envelopes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiEnvelope(BaseModel):
    """Standard success response."""

    ok: bool = True
    data: Any


class ApiErrorEnvelope(BaseModel):
    """Standard error response."""

    ok: bool = False
    error: dict[str, object | None]


def ok_response(payload: Any) -> ApiEnvelope:
    """Wrap a payload in the standard success envelope."""

    return ApiEnvelope(data=payload)


def error_response(
    *,
    message: str,
    code: str,
    category: str,
    details: dict[str, object] | None = None,
    severity: str,
    retryable: bool,
    operation: str | None = None,
    component: str | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    cause: dict[str, object] | None = None,
    causes: list[dict[str, object]] | None = None,
    timestamp: str | None = None,
) -> ApiErrorEnvelope:
    """Wrap an error payload in the standard error envelope."""

    return ApiErrorEnvelope(
        error={
            "message": message,
            "code": code,
            "category": category,
            "details": details,
            "severity": severity,
            "retryable": retryable,
            "operation": operation,
            "component": component,
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "cause": cause,
            "causes": causes or [],
            "timestamp": timestamp,
        }
    )
