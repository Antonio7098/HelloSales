"""Stageflow runtime wrapper."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from hello_sales_backend.platform.config.settings import Settings
from hello_sales_backend.platform.workflows.pipeline import (
    WorkflowPipeline,
    WorkflowPipelineFactory,
    WorkflowStageKind,
    WorkflowStageOutput,
    WorkflowStageSpec,
)
from hello_sales_backend.shared.errors import orchestration_error


@dataclass(slots=True)
class StageflowPipelineAdapter:
    """Adapt a Stageflow pipeline to the platform pipeline contract."""

    pipeline: Any

    async def run(self) -> dict[str, WorkflowStageOutput]:
        results = await self.pipeline.run()
        return {
            name: WorkflowStageOutput(data=dict(stage_output.data))
            for name, stage_output in results.items()
        }


@dataclass(slots=True)
class StageflowPipelineFactory:
    """Wrap Stageflow pipeline construction behind a platform-owned interface."""

    api: Any

    def create_pipeline(self, *, name: str, stages: list[WorkflowStageSpec]) -> WorkflowPipeline:
        pipeline = self.api.Pipeline.from_stages(
            *[
                self.api.stage(
                    stage.name,
                    stage.handler,
                    self._map_stage_kind(stage.kind),
                    dependencies=stage.dependencies,
                )
                for stage in stages
            ],
            name=name,
        )
        return StageflowPipelineAdapter(pipeline=pipeline)

    def _map_stage_kind(self, kind: WorkflowStageKind) -> Any:
        if kind is WorkflowStageKind.GUARD:
            return self.api.StageKind.GUARD
        if kind is WorkflowStageKind.WORK:
            return self.api.StageKind.WORK
        return self.api.StageKind.TRANSFORM


@dataclass(slots=True)
class WorkflowRuntime:
    """Resolved orchestration runtime capabilities."""

    installed: bool
    required: bool
    engine_name: str
    pipeline_factory: WorkflowPipelineFactory | None = None


def build_workflow_runtime(settings: Settings) -> WorkflowRuntime:
    """Build the Stageflow runtime wrapper."""

    try:
        importlib.import_module("stageflow")
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
            pipeline_factory=None,
        )

    return WorkflowRuntime(
        installed=True,
        required=settings.stageflow_required,
        engine_name="stageflow",
        pipeline_factory=StageflowPipelineFactory(api=stageflow_api_module),
    )
