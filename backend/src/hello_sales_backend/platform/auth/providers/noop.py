"""No-op auth provider used when no auth adapter is configured."""

from __future__ import annotations

from hello_sales_backend.platform.auth.contracts import AuthProviderPort, AuthResult


class NoopAuthProvider(AuthProviderPort):
    """Provider that leaves requests anonymous."""

    provider_name = "noop"

    def is_configured(self) -> bool:
        return False

    def get_authorization_url(self, *, state: str | None = None) -> str:
        return ""

    async def exchange_code(self, *, code: str) -> AuthResult:
        return AuthResult()

    async def authenticate(
        self,
        *,
        session_token: str | None,
        bearer_token: str | None = None,
    ) -> AuthResult:
        return AuthResult(source="noop")

    async def get_logout_url(self, *, session_token: str | None) -> str | None:
        return None

    async def aclose(self) -> None:
        return None

