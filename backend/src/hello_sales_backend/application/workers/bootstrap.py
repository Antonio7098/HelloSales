"""Application worker registry assembly."""

from __future__ import annotations

from hello_sales_backend.application.workers.definitions.structured_brief import (
    build_structured_brief_definition,
)
from hello_sales_backend.application.workers.registry import WorkerRegistry


def build_worker_registry() -> WorkerRegistry:
    """Build the application worker registry."""

    return WorkerRegistry([build_structured_brief_definition()])
