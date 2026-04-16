"""Request context middleware."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime


def _route_label(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) and path else "__unmatched__"


def _request_outcome(*, status_code: int, error_type: str | None) -> str:
    if error_type is not None or status_code >= 500:
        return "failure"
    if status_code >= 400:
        return "client_error"
    return "success"


class RequestContextMiddleware:
    """Attach request correlation identifiers to each HTTP request."""

    def __init__(self, app: ASGIApp, observability: ObservabilityRuntime) -> None:
        self._app = app
        self._observability = observability
        self._logger = get_logger("hello_sales_backend.http")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = MutableHeaders(scope=scope)
        request_id = headers.get("x-request-id") or uuid4().hex
        trace_id = headers.get("x-trace-id") or uuid4().hex
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id
        scope["state"]["trace_id"] = trace_id
        scope["state"]["correlation_id"] = request_id
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=request_id,
        )
        started_at = perf_counter()
        status_code = 500
        error_type: str | None = None
        self._observability.on_http_request_started()
        self._logger.info(
            "http.request.started",
            method=scope["method"],
            path=scope["path"],
            correlation_id=request_id,
        )

        with self._observability.start_http_span(
            method=scope["method"],
            path=scope["path"],
            request_id=request_id,
            trace_id=trace_id,
        ) as span:

            async def send_with_headers(message: Message) -> None:
                nonlocal status_code
                if message["type"] == "http.response.start":
                    response_headers = MutableHeaders(scope=message)
                    response_headers["x-request-id"] = request_id
                    response_headers["x-trace-id"] = trace_id
                    response_headers["x-correlation-id"] = request_id
                    status_code = int(message["status"])
                await send(message)

            try:
                await self._app(scope, receive, send_with_headers)
            except Exception as exc:
                error_type = exc.__class__.__name__
                self._logger.exception(
                    "http.request.failed",
                    method=scope["method"],
                    path=scope["path"],
                    duration_ms=round((perf_counter() - started_at) * 1000, 2),
                    correlation_id=request_id,
                    exception_type=error_type,
                    exception_message=str(exc),
                )
                raise
            finally:
                route = _route_label(scope)
                duration_seconds = perf_counter() - started_at
                self._observability.on_http_request_finished(
                    method=scope["method"],
                    route=route,
                    status_code=status_code,
                    outcome=_request_outcome(status_code=status_code, error_type=error_type),
                    duration_seconds=duration_seconds,
                )
                self._observability.finish_http_span(
                    span,
                    route=route,
                    status_code=status_code,
                    error_type=error_type,
                )
                self._logger.info(
                    "http.request.completed",
                    method=scope["method"],
                    path=scope["path"],
                    status_code=status_code,
                    duration_ms=round(duration_seconds * 1000, 2),
                    correlation_id=request_id,
                )
                structlog.contextvars.clear_contextvars()
