"""WorkOS auth provider adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import jwt
from jwt import PyJWKClient
from workos import WorkOSClient
from workos.session import (
    AuthenticateWithSessionCookieErrorResponse,
    AuthenticateWithSessionCookieFailureReason,
    AuthenticateWithSessionCookieSuccessResponse,
    RefreshWithSessionCookieErrorResponse,
    RefreshWithSessionCookieSuccessResponse,
)

from hello_sales_backend.platform.auth.contracts import AuthProviderPort, AuthResult
from hello_sales_backend.shared.auth import AuthContext
from hello_sales_backend.shared.errors import app_error


@dataclass(slots=True)
class _WorkOSClaims:
    """Decoded WorkOS JWT claims used for provider-neutral auth mapping."""

    session_id: str
    user_id: str
    organization_id: str | None
    role: str | None
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    raw: dict[str, object]


class WorkOSAuthProvider(AuthProviderPort):
    """WorkOS-backed hosted auth and API authentication adapter."""

    provider_name = "workos"
    _JWT_ALGORITHMS = ["RS256"]

    def __init__(
        self,
        *,
        api_key: str,
        client_id: str,
        cookie_password: str,
        redirect_uri: str,
        logout_return_to: str,
        base_url: str | None = None,
        request_timeout: int = 10,
    ) -> None:
        self._cookie_password = cookie_password
        self._redirect_uri = redirect_uri
        self._logout_return_to = logout_return_to
        self._client = WorkOSClient(
            api_key=api_key,
            client_id=client_id,
            base_url=base_url,
            request_timeout=request_timeout,
        )
        self._jwks = PyJWKClient(f"{self._client.base_url}sso/jwks/{self._client.client_id}")

    def is_configured(self) -> bool:
        return True

    def get_authorization_url(self, *, state: str | None = None) -> str:
        return self._client.user_management.get_authorization_url(
            provider="authkit",
            redirect_uri=self._redirect_uri,
            state=state,
        )

    async def exchange_code(self, *, code: str) -> AuthResult:
        try:
            payload = self._client.request_raw(
                method="post",
                path="user_management/authenticate",
                body={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self._client.client_id,
                    "client_secret": self._client._api_key,
                    "session": {
                        "seal_session": True,
                        "cookie_password": self._cookie_password,
                    },
                },
            )
        except Exception as exc:
            raise app_error(
                "WorkOS code exchange failed",
                code="provider.auth.code_exchange_failed",
                category="provider",
                status_code=502,
                details={"provider": self.provider_name},
                operation="auth.exchange_code",
                component="auth",
                exc=exc,
            ) from exc
        sealed_session = str(payload.get("sealed_session") or "")
        if not sealed_session:
            raise app_error(
                "WorkOS code exchange did not return a sealed session",
                code="provider.auth.code_exchange_invalid",
                category="provider",
                status_code=502,
                details={"provider": self.provider_name},
                operation="auth.exchange_code",
                component="auth",
            )
        context = self._map_from_access_token(
            access_token=str(payload["access_token"]),
            user=payload.get("user"),
            source="session_cookie",
        )
        return AuthResult(context=context, session_token=sealed_session, source="session_cookie")

    async def authenticate(
        self,
        *,
        session_token: str | None,
        bearer_token: str | None = None,
    ) -> AuthResult:
        if bearer_token:
            return AuthResult(
                context=self._map_from_access_token(
                    access_token=bearer_token,
                    user=None,
                    source="bearer_token",
                ),
                source="bearer_token",
            )
        session = self._client.user_management.load_sealed_session(
            session_data=session_token or "",
            cookie_password=self._cookie_password,
        )
        authenticated = session.authenticate()
        if isinstance(authenticated, AuthenticateWithSessionCookieSuccessResponse):
            return AuthResult(
                context=self._map_from_session_response(authenticated, source="session_cookie"),
                source="session_cookie",
            )
        if (
            isinstance(authenticated, AuthenticateWithSessionCookieErrorResponse)
            and authenticated.reason
            == AuthenticateWithSessionCookieFailureReason.NO_SESSION_COOKIE_PROVIDED
        ):
            return AuthResult(source="session_cookie")

        refreshed = session.refresh()
        if isinstance(refreshed, RefreshWithSessionCookieSuccessResponse):
            return AuthResult(
                context=self._map_from_refresh_response(refreshed, source="session_cookie"),
                session_token=refreshed.sealed_session,
                source="session_cookie",
            )
        if isinstance(refreshed, RefreshWithSessionCookieErrorResponse):
            if refreshed.reason == AuthenticateWithSessionCookieFailureReason.INVALID_SESSION_COOKIE:
                return AuthResult(clear_session=True, source="session_cookie")
            raise app_error(
                "WorkOS session refresh failed",
                code="provider.auth.session_refresh_failed",
                category="provider",
                status_code=502,
                retryable=True,
                details={
                    "provider": self.provider_name,
                    "reason": str(refreshed.reason),
                },
                operation="auth.authenticate",
                component="auth",
            )
        return AuthResult(clear_session=True, source="session_cookie")

    async def get_logout_url(self, *, session_token: str | None) -> str | None:
        if not session_token:
            return self._logout_return_to
        try:
            session = self._client.user_management.load_sealed_session(
                session_data=session_token,
                cookie_password=self._cookie_password,
            )
            return session.get_logout_url(return_to=self._logout_return_to)
        except Exception as exc:
            raise app_error(
                "Failed to build WorkOS logout URL",
                code="provider.auth.logout_failed",
                category="provider",
                status_code=502,
                details={"provider": self.provider_name},
                operation="auth.logout",
                component="auth",
                exc=exc,
            ) from exc

    async def aclose(self) -> None:
        return None

    def _map_from_access_token(
        self,
        *,
        access_token: str,
        user: dict[str, Any] | None,
        source: str,
    ) -> AuthContext:
        claims = self._decode_access_token(access_token)
        user_payload = user or {}
        email = user_payload.get("email")
        impersonator = user_payload.get("impersonator")
        return AuthContext(
            provider_name=self.provider_name,
            actor_id=claims.user_id,
            user_id=claims.user_id,
            session_id=claims.session_id,
            org_id=claims.organization_id,
            email=str(email) if isinstance(email, str) else None,
            roles=claims.roles,
            permissions=claims.permissions,
            impersonator_email=(
                str(impersonator["email"])
                if isinstance(impersonator, dict) and isinstance(impersonator.get("email"), str)
                else None
            ),
            raw_claims={**claims.raw, "source": source},
        )

    def _map_from_session_response(
        self,
        response: AuthenticateWithSessionCookieSuccessResponse,
        *,
        source: str,
    ) -> AuthContext:
        user_payload = response.user or {}
        user_id = str(user_payload.get("id") or "")
        if not user_id:
            raise app_error(
                "WorkOS session authentication did not include a user id",
                code="provider.auth.invalid_session",
                category="provider",
                status_code=502,
                details={"provider": self.provider_name},
                operation="auth.map_session",
                component="auth",
            )
        roles = tuple(
            str(item)
            for item in (
                response.roles
                if response.roles is not None
                else ([response.role] if response.role else [])
            )
        )
        permissions = tuple(str(item) for item in (response.permissions or []))
        email = user_payload.get("email")
        impersonator = response.impersonator or {}
        return AuthContext(
            provider_name=self.provider_name,
            actor_id=user_id,
            user_id=user_id,
            session_id=response.session_id,
            org_id=response.organization_id,
            email=str(email) if isinstance(email, str) else None,
            roles=roles,
            permissions=permissions,
            impersonator_email=(
                str(impersonator.get("email"))
                if isinstance(impersonator.get("email"), str)
                else None
            ),
            raw_claims={"source": source},
        )

    def _map_from_refresh_response(
        self,
        response: RefreshWithSessionCookieSuccessResponse,
        *,
        source: str,
    ) -> AuthContext:
        return self._map_from_session_response(
            AuthenticateWithSessionCookieSuccessResponse(
                authenticated=True,
                session_id=response.session_id,
                organization_id=response.organization_id,
                role=response.role,
                roles=response.roles,
                permissions=response.permissions,
                user=response.user,
                impersonator=response.impersonator,
                entitlements=response.entitlements,
                feature_flags=response.feature_flags,
            ),
            source=source,
        )

    def _decode_access_token(self, access_token: str) -> _WorkOSClaims:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(access_token)
            decoded = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=self._JWT_ALGORITHMS,
                options={"verify_aud": False},
                leeway=self._client._jwt_leeway,
            )
        except Exception as exc:
            raise app_error(
                "WorkOS bearer token validation failed",
                code="provider.auth.invalid_bearer_token",
                category="provider",
                status_code=401,
                severity="warning",
                details={"provider": self.provider_name},
                operation="auth.authenticate_bearer",
                component="auth",
                exc=exc,
            ) from exc
        roles: tuple[str, ...]
        if isinstance(decoded.get("roles"), list):
            roles = tuple(str(item) for item in decoded["roles"])
        elif decoded.get("role") is not None:
            roles = (str(decoded["role"]),)
        else:
            roles = ()
        permissions = tuple(str(item) for item in decoded.get("permissions", []) or [])
        user_id = str(decoded.get("sub") or "")
        session_id = str(decoded.get("sid") or "")
        if not user_id or not session_id:
            raise app_error(
                "WorkOS access token is missing required claims",
                code="provider.auth.invalid_bearer_token",
                category="provider",
                status_code=401,
                severity="warning",
                details={"provider": self.provider_name},
                operation="auth.authenticate_bearer",
                component="auth",
            )
        return _WorkOSClaims(
            session_id=session_id,
            user_id=user_id,
            organization_id=None if decoded.get("org_id") is None else str(decoded["org_id"]),
            role=None if decoded.get("role") is None else str(decoded["role"]),
            roles=roles,
            permissions=permissions,
            raw={str(key): value for key, value in decoded.items()},
        )
