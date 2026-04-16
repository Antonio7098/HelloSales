"""Shared protocol helpers."""

from typing import Protocol


class SupportsHealthcheck(Protocol):
    """Protocol for readiness checks."""

    async def readiness(self) -> object: ...
