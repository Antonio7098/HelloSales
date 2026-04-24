"""Request auth middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def _parse_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip() or None


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Resolve the current auth context once per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        auth_service = request.app.state.container.modules.auth.service
        auth_result = await auth_service.authenticate_request(
            session_token=request.cookies.get(auth_service.session_cookie_name),
            bearer_token=_parse_bearer_token(request.headers.get("authorization")),
        )
        request.state.auth_context = auth_result.context
        response = await call_next(request)
        if auth_result.session_token:
            auth_service.set_session_cookie(response, auth_result.session_token)
        elif auth_result.clear_session:
            auth_service.clear_session_cookie(response)
        return response
