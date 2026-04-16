"""Helpers for redacting sensitive log payloads."""

from __future__ import annotations

from collections.abc import Mapping


SENSITIVE_KEYS = {"authorization", "api_key", "token", "password", "secret"}


def redact_mapping(values: Mapping[str, object | None]) -> dict[str, object | None]:
    """Return a shallow copy with sensitive keys redacted."""

    redacted: dict[str, object | None] = {}
    for key, value in values.items():
        if key.lower() in SENSITIVE_KEYS and value is not None:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted
