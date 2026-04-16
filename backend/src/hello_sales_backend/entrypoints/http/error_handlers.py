"""HTTP error handler registration."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hello_sales_backend.entrypoints.http.schemas import error_response
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.shared.errors import AppError, internal_error


def _request_context(request: Request) -> tuple[str | None, str | None]:
    state = getattr(request, "state", None)
    if state is None:
        return None, None
    return getattr(state, "request_id", None), getattr(state, "trace_id", None)


def register_error_handlers(app: FastAPI) -> None:
    """Register application-level error handlers."""

    logger = get_logger("hello_sales_backend.http.errors")

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id, trace_id = _request_context(request)
        enriched = exc.with_context(correlation_id=request_id, trace_id=trace_id)
        await request.app.state.container.observability.emit(
            OperationalEvent(
                event_type="request.failed",
                severity=enriched.severity,
                component=enriched.component or "http",
                operation=enriched.operation or "http.request",
                correlation_id=enriched.correlation_id,
                trace_id=enriched.trace_id,
                code=enriched.code,
                payload=enriched.to_dict(),
            )
        )
        logger.warning(
            "request_failed",
            path=request.url.path,
            method=request.method,
            **enriched.to_dict(),
        )
        return JSONResponse(
            status_code=enriched.status_code,
            content=error_response(
                message=enriched.message,
                code=enriched.code,
                category=enriched.category,
                details=enriched.details,
                severity=enriched.severity,
                retryable=enriched.retryable,
                operation=enriched.operation,
                component=enriched.component,
                correlation_id=enriched.correlation_id,
                trace_id=enriched.trace_id,
                cause=enriched.cause,
                causes=enriched.causes,
                timestamp=enriched.timestamp,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id, trace_id = _request_context(request)
        structured_error = internal_error(
            "Unhandled application exception",
            details={
                "path": request.url.path,
                "method": request.method,
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            },
            operation="http.request",
            component="http",
            exc=exc,
        ).with_context(correlation_id=request_id, trace_id=trace_id)
        await request.app.state.container.observability.emit(
            OperationalEvent(
                event_type="request.failed_unexpected",
                severity=structured_error.severity,
                component=structured_error.component or "http",
                operation=structured_error.operation or "http.request",
                correlation_id=structured_error.correlation_id,
                trace_id=structured_error.trace_id,
                code=structured_error.code,
                payload=structured_error.to_dict(),
            )
        )
        logger.exception(
            "request_failed_unexpected",
            path=request.url.path,
            method=request.method,
            **structured_error.to_dict(),
        )
        return JSONResponse(
            status_code=structured_error.status_code,
            content=error_response(
                message=structured_error.message,
                code=structured_error.code,
                category=structured_error.category,
                details=structured_error.details,
                severity=structured_error.severity,
                retryable=structured_error.retryable,
                operation=structured_error.operation,
                component=structured_error.component,
                correlation_id=structured_error.correlation_id,
                trace_id=structured_error.trace_id,
                cause=structured_error.cause,
                causes=structured_error.causes,
                timestamp=structured_error.timestamp,
            ).model_dump(mode="json"),
        )
