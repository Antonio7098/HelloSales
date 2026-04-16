"""Request context middleware."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hello_sales_backend.platform.observability.logging import get_logger


class RequestContextMiddleware:
    """Attach request correlation identifiers to each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app
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
        self._logger.info(
            "http.request.started",
            method=scope["method"],
            path=scope["path"],
            correlation_id=request_id,
        )

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
            self._logger.exception(
                "http.request.failed",
                method=scope["method"],
                path=scope["path"],
                duration_ms=round((perf_counter() - started_at) * 1000, 2),
                correlation_id=request_id,
                exception_type=exc.__class__.__name__,
                exception_message=str(exc),
            )
            raise
        finally:
            self._logger.info(
                "http.request.completed",
                method=scope["method"],
                path=scope["path"],
                status_code=status_code,
                duration_ms=round((perf_counter() - started_at) * 1000, 2),
                correlation_id=request_id,
            )
            structlog.contextvars.clear_contextvars()
