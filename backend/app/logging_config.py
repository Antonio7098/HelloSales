"""Structured JSON logging configuration.

This module is now a thin shim over :mod:`app.infrastructure.logging`.
All existing imports of :mod:`app.logging_config` continue to work
while the infrastructure layer owns the actual implementation.
"""

from app.infrastructure.logging import *  # noqa: F401,F403
