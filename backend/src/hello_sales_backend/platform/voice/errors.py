"""Voice error helpers."""

from __future__ import annotations

from collections.abc import Mapping

from hello_sales_backend.shared.errors import AppError, app_error


def voice_error(
    message: str,
    *,
    code: str,
    category: str = "provider",
    status_code: int = 502,
    retryable: bool = False,
    details: Mapping[str, object] | None = None,
    operation: str | None = None,
    exc: BaseException | None = None,
) -> AppError:
    """Create a structured voice runtime error."""

    return app_error(
        message,
        code=code,
        category=category,
        status_code=status_code,
        retryable=retryable,
        details=details,
        operation=operation,
        component="voice",
        exc=exc,
    )


def provider_disabled(kind: str, provider: str) -> AppError:
    """Return a stable disabled-provider error."""

    return voice_error(
        f"Voice {kind} provider is not configured",
        code=f"voice.{kind}.provider_disabled",
        category="dependency",
        status_code=503,
        details={"provider": provider},
        operation=f"voice.{kind}",
    )
