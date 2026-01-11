"""WorkOS JWT token verification."""

from functools import lru_cache
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from app.config import Settings, get_settings
from app.domain.errors import TokenExpiredError, TokenInvalidError
from app.infrastructure.telemetry.logging import get_logger

logger = get_logger(__name__)


class WorkOSAuth:
    """WorkOS authentication handler for JWT verification."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client_id = settings.workos_client_id
        self.issuer = settings.workos_issuer
        self.audience = settings.workos_audience or settings.workos_client_id
        self.algorithm = settings.jwt_algorithm

        # JWKS client for fetching public keys
        self._jwks_client: PyJWKClient | None = None

    @property
    def jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client."""
        if self._jwks_client is None:
            jwks_uri = f"{self.issuer}/.well-known/jwks.json"
            self._jwks_client = PyJWKClient(jwks_uri)
        return self._jwks_client

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Verify a WorkOS JWT token.

        Args:
            token: The JWT token string

        Returns:
            Decoded token claims

        Raises:
            TokenExpiredError: If token is expired
            TokenInvalidError: If token is invalid
        """
        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify the token
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            logger.debug(
                "Token verified successfully",
                extra={"sub": claims.get("sub"), "org_id": claims.get("org_id")},
            )

            return claims

        except jwt.ExpiredSignatureError as e:
            logger.warning("Token expired", extra={"error": str(e)})
            raise TokenExpiredError(
                message="Token has expired",
                details={"error": str(e)},
            ) from e

        except jwt.InvalidAudienceError as e:
            logger.warning("Invalid token audience", extra={"error": str(e)})
            raise TokenInvalidError(
                message="Invalid token audience",
                details={"error": str(e)},
            ) from e

        except jwt.InvalidIssuerError as e:
            logger.warning("Invalid token issuer", extra={"error": str(e)})
            raise TokenInvalidError(
                message="Invalid token issuer",
                details={"error": str(e)},
            ) from e

        except jwt.InvalidSignatureError as e:
            logger.warning("Invalid token signature", extra={"error": str(e)})
            raise TokenInvalidError(
                message="Invalid token signature",
                details={"error": str(e)},
            ) from e

        except jwt.DecodeError as e:
            logger.warning("Token decode error", extra={"error": str(e)})
            raise TokenInvalidError(
                message="Invalid token format",
                details={"error": str(e)},
            ) from e

        except Exception as e:
            logger.error("Unexpected token verification error", extra={"error": str(e)})
            raise TokenInvalidError(
                message="Token verification failed",
                details={"error": str(e)},
            ) from e

    async def get_user_info(self, token: str) -> dict[str, Any]:
        """Fetch user info from WorkOS userinfo endpoint.

        Args:
            token: Access token

        Returns:
            User info from WorkOS
        """
        userinfo_url = f"{self.issuer}/sso/userinfo"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()


@lru_cache
def get_workos_auth() -> WorkOSAuth:
    """Get cached WorkOS auth instance."""
    return WorkOSAuth(get_settings())
