from __future__ import annotations

from httpx import AsyncClient

from hello_sales_backend.platform.auth.contracts import AuthResult
from hello_sales_backend.shared.auth import (
    ANALYTICS_READ_PERMISSION,
    APP_ACCESS_PERMISSION,
    COMPANY_PROFILE_READ_PERMISSION,
    COMPANY_PROFILE_WRITE_PERMISSION,
    ENTITY_OPERATIONS_WRITE_PERMISSION,
    JOBS_READ_PERMISSION,
    JOBS_RUN_PERMISSION,
    SESSIONS_READ_ANY_PERMISSION,
    SESSIONS_READ_PERMISSION,
    SESSIONS_WRITE_ANY_PERMISSION,
    SESSIONS_WRITE_PERMISSION,
    SYSTEM_READ_PERMISSION,
    WEB_SEARCH_USE_PERMISSION,
    WORKERS_CANCEL_PERMISSION,
    WORKERS_READ_PERMISSION,
    WORKERS_RUN_PERMISSION,
    AuthContext,
)


class FakeAuthProvider:
    provider_name = "test-auth"

    def __init__(self, session_result: AuthResult | None = None) -> None:
        self._session_result = session_result

    def is_configured(self) -> bool:
        return True

    def get_authorization_url(self, *, state: str | None = None) -> str:
        suffix = f"?state={state}" if state else ""
        return f"https://auth.example.test/login{suffix}"

    async def exchange_code(self, *, code: str) -> AuthResult:
        if code == "good-code" and self._session_result is not None:
            return AuthResult(
                context=self._session_result.context,
                session_token="test-session",
                source="session_cookie",
            )
        return AuthResult()

    async def authenticate(
        self,
        *,
        session_token: str | None,
        bearer_token: str | None = None,
    ) -> AuthResult:
        token = bearer_token or session_token
        if token == "test-session" and self._session_result is not None:
            return self._session_result
        if token:
            return AuthResult(clear_session=True, source="session_cookie")
        return AuthResult(source="session_cookie")

    async def get_logout_url(self, *, session_token: str | None) -> str | None:
        return "https://auth.example.test/logout"

    async def aclose(self) -> None:
        return None


def build_test_auth_context(
    *,
    permissions: tuple[str, ...] | None = None,
    roles: tuple[str, ...] = ("admin",),
) -> AuthContext:
    resolved_permissions = permissions if permissions is not None else (
        APP_ACCESS_PERMISSION,
        SESSIONS_READ_PERMISSION,
        SESSIONS_WRITE_PERMISSION,
        SESSIONS_READ_ANY_PERMISSION,
        SESSIONS_WRITE_ANY_PERMISSION,
        COMPANY_PROFILE_READ_PERMISSION,
        COMPANY_PROFILE_WRITE_PERMISSION,
        JOBS_READ_PERMISSION,
        JOBS_RUN_PERMISSION,
        WORKERS_READ_PERMISSION,
        WORKERS_RUN_PERMISSION,
        WORKERS_CANCEL_PERMISSION,
        SYSTEM_READ_PERMISSION,
        ANALYTICS_READ_PERMISSION,
        WEB_SEARCH_USE_PERMISSION,
        ENTITY_OPERATIONS_WRITE_PERMISSION,
    )
    return AuthContext(
        provider_name="test-auth",
        actor_id="user_test_123",
        user_id="user_test_123",
        session_id="session_test_123",
        org_id="org_test_123",
        email="seller@example.test",
        roles=roles,
        permissions=resolved_permissions,
    )


def build_test_auth_provider(
    *,
    permissions: tuple[str, ...] | None = None,
    roles: tuple[str, ...] = ("admin",),
) -> FakeAuthProvider:
    return FakeAuthProvider(
        AuthResult(
            context=build_test_auth_context(permissions=permissions, roles=roles),
            session_token="test-session",
            source="session_cookie",
        )
    )


def attach_test_session_cookie(client: AsyncClient) -> None:
    client.cookies.set("hello_sales_session", "test-session")
