"""Application worker registry."""

from __future__ import annotations

from dataclasses import dataclass

from hello_sales_backend.application.workers.contracts import WorkerDefinition
from hello_sales_backend.shared.errors import app_error


@dataclass(slots=True)
class WorkerRegistry:
    """Index concrete worker definitions by name."""

    definitions: list[WorkerDefinition]

    def require(self, worker_name: str) -> WorkerDefinition:
        for definition in self.definitions:
            if definition.worker_name == worker_name:
                return definition
        raise app_error(
            "Worker definition was not found",
            code="worker.definition.not_found",
            category="validation",
            status_code=404,
            details={"worker_name": worker_name},
            operation="worker.registry.require",
            component="worker",
        )

    def list_profiles(self) -> list[tuple[str, str]]:
        return [(item.worker_name, item.display_name) for item in self.definitions]
