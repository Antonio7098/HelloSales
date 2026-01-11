"""Request context middleware for correlation IDs."""

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.telemetry.logging import clear_request_context, set_request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that sets up request context for logging and tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid4())

        # Set context for logging
        set_request_context(request_id=request_id)

        # Add request ID to request state for later use
        request.state.request_id = request_id

        try:
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response
        finally:
            # Clear context after request
            clear_request_context()
