"""Auth endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from hello_sales_backend.entrypoints.http.dependencies import (
    get_auth_service,
    get_container,
    require_authenticated_context,
)
from hello_sales_backend.entrypoints.http.schemas import ApiEnvelope, ok_response
from hello_sales_backend.modules.auth import AuthService
from hello_sales_backend.platform.composition.app_container import AppContainer
from hello_sales_backend.shared.auth import AuthContext
from hello_sales_backend.shared.errors import app_error

router = APIRouter()
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ContainerDep = Annotated[AppContainer, Depends(get_container)]
AuthContextDep = Annotated[AuthContext, Depends(require_authenticated_context)]


@router.get("/login")
async def login(
    service: AuthServiceDep,
    return_path: str | None = Query(default=None),
) -> RedirectResponse:
    return RedirectResponse(service.get_login_url(return_path=return_path), status_code=302)


@router.get("/callback")
async def callback(
    request: Request,
    service: AuthServiceDep,
    container: ContainerDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> RedirectResponse:
    if not code:
        raise app_error(
            "Auth callback code is required",
            code="auth.callback.code_missing",
            category="validation",
            status_code=400,
            severity="warning",
            operation="auth.callback",
            component="auth",
        )
    auth_result = await service.exchange_code(code=code)
    if auth_result.context is None or auth_result.session_token is None:
        raise app_error(
            "Auth callback did not establish a session",
            code="auth.callback.session_missing",
            category="provider",
            status_code=502,
            operation="auth.callback",
            component="auth",
        )
    return_path = service.normalize_return_path(state)
    redirect_url = f"{container.settings.frontend_app_url.rstrip('/')}{return_path}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    service.set_session_cookie(response, auth_result.session_token)
    request.state.auth_context = auth_result.context
    return response


@router.get("/session", response_model=ApiEnvelope)
async def current_session(
    auth_context: AuthContextDep,
    service: AuthServiceDep,
) -> ApiEnvelope:
    return ok_response(service.current_session_view(auth_context))


@router.post("/logout", response_model=ApiEnvelope)
async def logout(
    request: Request,
    response: Response,
    service: AuthServiceDep,
) -> ApiEnvelope:
    result = await service.logout(
        session_token=request.cookies.get(service.session_cookie_name),
    )
    service.clear_session_cookie(response)
    return ok_response(result)
