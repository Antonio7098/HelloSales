"""Clock adapter for system status."""

from __future__ import annotations

from datetime import UTC, datetime


class UtcClock:
    """Provide UTC timestamps."""

    def now_iso(self) -> str:
        return datetime.now(UTC).isoformat()
