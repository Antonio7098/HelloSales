"""Development-only auth provider."""

from __future__ import annotations

from hello_sales_backend.platform.auth.contracts import AuthProviderPort, AuthResult
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

_DEV_SESSION_TOKEN = "dev-session"
_DEV_AUTH_CONTEXT = AuthContext(
    provider_name="dev",
    actor_id="dev_user",
    user_id="dev_user",
    session_id="dev-session-id",
    org_id="dev-org",
    email="dev@hello-sales.local",
    roles=("developer",),
    permissions=(
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
    ),
)


class DevAuthProvider(AuthProviderPort):
    """Provider that injects a fixed development identity."""

    provider_name = "dev"

    def is_configured(self) -> bool:
        return True

    def get_authorization_url(self, *, state: str | None = None) -> str:
        return state or "/"

    async def exchange_code(self, *, code: str) -> AuthResult:
        return AuthResult(
            context=_DEV_AUTH_CONTEXT,
            session_token=_DEV_SESSION_TOKEN,
            source="dev",
        )

    async def authenticate(
        self,
        *,
        session_token: str | None,
        bearer_token: str | None = None,
    ) -> AuthResult:
        return AuthResult(
            context=_DEV_AUTH_CONTEXT,
            session_token=session_token or bearer_token or _DEV_SESSION_TOKEN,
            source="dev",
        )

    async def get_logout_url(self, *, session_token: str | None) -> str | None:
        return None

    async def aclose(self) -> None:
        return None
