"""Provider-neutral auth contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from hello_sales_backend.shared.auth import AuthContext


@dataclass(slots=True, frozen=True)
class AuthResult:
    """Resolved authentication result for one request or callback."""

    context: AuthContext | None = None
    session_token: str | None = None
    clear_session: bool = False
    source: str | None = None


class AuthProviderPort(Protocol):
    """Provider contract for app-owned auth flows."""

    provider_name: str

    def is_configured(self) -> bool: ...

    def get_authorization_url(self, *, state: str | None = None) -> str: ...

    async def exchange_code(self, *, code: str) -> AuthResult: ...

    async def authenticate(
        self,
        *,
        session_token: str | None,
        bearer_token: str | None = None,
    ) -> AuthResult: ...

    async def get_logout_url(self, *, session_token: str | None) -> str | None: ...

    async def aclose(self) -> None: ...

