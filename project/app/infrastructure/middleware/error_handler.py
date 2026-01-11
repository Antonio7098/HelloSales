"""Global error handler middleware."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AppError,
    AuthError,
    NotFoundError,
    ProviderError,
    ValidationError,
)
from app.infrastructure.telemetry.logging import get_logger

logger = get_logger(__name__)


def error_handler_middleware(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Handle all application errors."""
        # Determine HTTP status code based on error type
        status_code = _get_status_code(exc)

        # Log the error
        log_level = "warning" if status_code < 500 else "error"
        getattr(logger, log_level)(
            f"Application error: {exc.message}",
            extra={
                "error_code": exc.code,
                "error_details": exc.details,
                "retryable": exc.retryable,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "retryable": exc.retryable,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(
            f"Unhandled exception: {str(exc)}",
            extra={"path": request.url.path, "error_type": type(exc).__name__},
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                    "retryable": False,
                }
            },
        )


def _get_status_code(error: AppError) -> int:
    """Map error type to HTTP status code."""
    if isinstance(error, NotFoundError):
        return 404
    if isinstance(error, ValidationError):
        return 400
    if isinstance(error, AuthError):
        return 401
    if isinstance(error, ProviderError):
        return 502
    return 500
