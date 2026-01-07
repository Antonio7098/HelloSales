import logging
import time
from typing import Any

import jwt
from jwt import PyJWKClient

from app.config import get_settings

logger = logging.getLogger("auth")

_workos_jwks_client: PyJWKClient | None = None
_workos_jwks_last_refresh: float = 0
WORKOS_JWKS_CACHE_TTL = 3600


class WorkOSJWTError(Exception):
    """Custom exception for WorkOS JWT verification errors."""


def _get_workos_jwks_url() -> str:
    settings = get_settings()
    client_id = (settings.workos_client_id or "").strip()
    if not client_id:
        raise WorkOSJWTError("WorkOS client_id is not configured")
    return f"https://api.workos.com/sso/jwks/{client_id}"


def _get_jwks_client() -> PyJWKClient:
    global _workos_jwks_client, _workos_jwks_last_refresh

    current_time = time.time()

    if (
        _workos_jwks_client is None
        or (current_time - _workos_jwks_last_refresh) > WORKOS_JWKS_CACHE_TTL
    ):
        jwks_url = _get_workos_jwks_url()

        _workos_jwks_client = PyJWKClient(jwks_url, cache_keys=True)
        _workos_jwks_last_refresh = current_time

        logger.debug(
            "WorkOS JWKS client initialized",
            extra={"service": "auth", "jwks_url": jwks_url},
        )

    return _workos_jwks_client


def _normalize_issuer(value: str) -> str:
    return value.rstrip("/")


async def verify_workos_jwt(token: str) -> dict[str, Any]:
    """Verify a WorkOS AuthKit access token and return claims."""
    settings = get_settings()

    if not settings.workos_client_id:
        raise WorkOSJWTError("WorkOS is not configured")

    try:
        jwks_client = _get_jwks_client()

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
        except jwt.exceptions.PyJWKClientError as exc:
            logger.error(
                "Failed to get WorkOS signing key",
                extra={"service": "auth", "error": str(exc)},
            )
            raise WorkOSJWTError(f"Failed to get signing key: {exc}")

        issuer = settings.workos_issuer or ""
        options: dict[str, bool] = {
            "verify_aud": bool((settings.workos_audience or "").strip()),
            "verify_iss": False,
        }

        decode_kwargs: dict[str, Any] = {
            "key": signing_key.key,
            "algorithms": ["RS256"],
            "options": options,
        }

        if options["verify_aud"]:
            decode_kwargs["audience"] = settings.workos_audience

        claims = jwt.decode(token, **decode_kwargs)

        if issuer:
            token_issuer = claims.get("iss")
            if not isinstance(token_issuer, str) or not token_issuer:
                raise WorkOSJWTError("Token missing 'iss' claim")
            if _normalize_issuer(token_issuer) != _normalize_issuer(issuer):
                raise WorkOSJWTError("Invalid token issuer")

        if "sub" not in claims:
            raise WorkOSJWTError("Token missing 'sub' claim")

        return claims

    except jwt.ExpiredSignatureError:
        logger.warning("WorkOS JWT expired", extra={"service": "auth"})
        raise WorkOSJWTError("Token has expired")

    except jwt.InvalidTokenError as exc:
        logger.warning(
            "Invalid WorkOS JWT",
            extra={"service": "auth", "error": str(exc)},
        )
        raise WorkOSJWTError(f"Invalid token: {exc}")

    except WorkOSJWTError:
        raise

    except Exception as exc:
        logger.error(
            "WorkOS JWT verification failed",
            extra={"service": "auth", "error": str(exc)},
            exc_info=True,
        )
        raise WorkOSJWTError(f"Verification failed: {exc}")
