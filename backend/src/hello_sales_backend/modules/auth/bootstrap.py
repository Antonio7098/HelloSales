"""Auth module bootstrap."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.modules.auth.use_cases.auth_service import AuthService
from hello_sales_backend.platform.auth.contracts import AuthProviderPort


@dataclass(slots=True)
class AuthModule:
    """Resolved auth module bundle."""

    service: AuthService


def build_auth_module(
    *,
    provider: AuthProviderPort,
    session_cookie_name: str,
    session_cookie_secure: bool,
    session_cookie_domain: str | None,
) -> AuthModule:
    """Build the auth module."""

    return AuthModule(
        service=AuthService(
            provider=provider,
            session_cookie_name=session_cookie_name,
            session_cookie_secure=session_cookie_secure,
            session_cookie_domain=session_cookie_domain,
        )
    )

