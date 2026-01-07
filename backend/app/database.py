"""Database connection and session management.

This module is now a thin shim over :mod:`app.infrastructure.database`.
All existing imports of :mod:`app.database` continue to work while the
infrastructure layer owns the actual implementation.
"""

from app.infrastructure.database import *  # noqa: F401,F403
