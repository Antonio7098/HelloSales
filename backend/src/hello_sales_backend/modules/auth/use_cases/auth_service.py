"""Auth application service."""

from __future__ import annotations

from fastapi import Response

from hello_sales_backend.modules.auth.use_cases.views import CurrentSessionView, LogoutView
from hello_sales_backend.platform.auth.contracts import AuthProviderPort, AuthResult
from hello_sales_backend.shared.auth import AuthContext
from hello_sales_backend.shared.errors import app_error


class AuthService:
    """Expose app-owned auth use cases through a stable facade."""

    def __init__(
        self,
        *,
        provider: AuthProviderPort,
        session_cookie_name: str,
        session_cookie_secure: bool,
        session_cookie_domain: str | None,
    ) -> None:
        self._provider = provider
        self._session_cookie_name = session_cookie_name
        self._session_cookie_secure = session_cookie_secure
        self._session_cookie_domain = session_cookie_domain

    @property
    def session_cookie_name(self) -> str:
        """Return the configured app session cookie name."""

        return self._session_cookie_name

    def get_login_url(self, *, return_path: str | None = None) -> str:
        """Return the hosted auth redirect URL."""

        return self._provider.get_authorization_url(state=self.normalize_return_path(return_path))

    async def authenticate_request(
        self,
        *,
        session_token: str | None,
        bearer_token: str | None = None,
    ) -> AuthResult:
        """Resolve the current request auth context through the configured provider."""

        return await self._provider.authenticate(
            session_token=session_token,
            bearer_token=bearer_token,
        )

    async def exchange_code(self, *, code: str) -> AuthResult:
        """Exchange a callback code into an authenticated app session."""

        return await self._provider.exchange_code(code=code)

    async def logout(self, *, session_token: str | None) -> LogoutView:
        """Build the logout redirect and clear the local session."""

        return LogoutView(redirect_url=await self._provider.get_logout_url(session_token=session_token))

    @staticmethod
    def normalize_return_path(return_path: str | None) -> str:
        """Restrict callback state to safe in-app relative paths."""

        if not return_path:
            return "/"
        candidate = return_path.strip()
        if not candidate:
            return "/"
        if not candidate.startswith("/") or candidate.startswith("//"):
            raise app_error(
                "Return path must be an in-app relative path",
                code="auth.invalid_return_path",
                category="validation",
                status_code=400,
                severity="warning",
                details={"return_path": return_path},
                operation="auth.normalize_return_path",
                component="auth",
            )
        return candidate

    def set_session_cookie(self, response: Response, session_token: str) -> None:
        """Attach the app-owned session cookie to the response."""

        response.set_cookie(
            key=self._session_cookie_name,
            value=session_token,
            httponly=True,
            secure=self._session_cookie_secure,
            samesite="lax",
            path="/",
            domain=self._session_cookie_domain,
        )

    def clear_session_cookie(self, response: Response) -> None:
        """Remove the app-owned session cookie from the response."""

        response.delete_cookie(
            key=self._session_cookie_name,
            path="/",
            domain=self._session_cookie_domain,
        )

    @staticmethod
    def require_authenticated(context: AuthContext | None) -> AuthContext:
        """Raise a structured 401 when the current request is anonymous."""

        if context is not None:
            return context
        raise app_error(
            "Authentication is required for this endpoint",
            code="auth.unauthenticated",
            category="validation",
            status_code=401,
            severity="warning",
            operation="auth.require_authenticated",
            component="auth",
        )

    @staticmethod
    def current_session_view(context: AuthContext) -> CurrentSessionView:
        """Project an auth context into the public session view."""

        return CurrentSessionView(
            provider_name=context.provider_name,
            actor_id=context.actor_id,
            user_id=context.user_id,
            session_id=context.session_id,
            org_id=context.org_id,
            email=context.email,
            roles=list(context.roles),
            permissions=list(context.permissions),
            impersonator_email=context.impersonator_email,
        )

