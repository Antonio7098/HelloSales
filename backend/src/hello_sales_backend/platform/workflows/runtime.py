"""Stageflow runtime wrapper."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.shared.errors import orchestration_error


@dataclass(slots=True)
class WorkflowRuntime:
    """Resolved orchestration runtime capabilities."""

    installed: bool
    required: bool
    engine_name: str
    runtime_objects: dict[str, Any]


def build_workflow_runtime(settings: Settings) -> WorkflowRuntime:
    """Build the Stageflow runtime wrapper."""

    try:
        stageflow_module = importlib.import_module("stageflow")
        stageflow_api_module = importlib.import_module("stageflow.api")
    except ModuleNotFoundError as exc:
        if settings.stageflow_required:
            raise orchestration_error(
                "Stageflow runtime is required but not installed",
                code="workflow.runtime.missing_dependency",
                details={"engine": "stageflow", "required": True},
                exc=exc,
            ) from exc
        return WorkflowRuntime(
            installed=False,
            required=False,
            engine_name="stageflow",
            runtime_objects={},
        )

    return WorkflowRuntime(
        installed=True,
        required=settings.stageflow_required,
        engine_name="stageflow",
        runtime_objects={
            "module": stageflow_module,
            "api": stageflow_api_module,
        },
    )
