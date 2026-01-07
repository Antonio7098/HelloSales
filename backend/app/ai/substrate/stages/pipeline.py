"""Code-defined pipeline base class for stageflow 2.0.

Pipelines are Python classes that define their stage composition declaratively.
Replaces kernels.json, channels.json, and pipelines.json.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.ai.substrate.stages.base import StageContext, StageKind, StageOutput
from app.ai.substrate.stages.graph import UnifiedStageGraph, UnifiedStageSpec

if TYPE_CHECKING:
    from app.ai.substrate.stages.base import Stage

# Dependencies that stages may require - extracted from ctx.config["data"]
STAGE_DEPENDENCIES = {
    # Providers
    "llm_provider",
    "stt_provider",
    "tts_provider",
    # Services
    "chat_service",
    "db",
    # Logging & utilities
    "call_logger",
    "retry_fn",
}


def _get_init_params(stage_cls: type[Stage]) -> set[str]:
    """Get the parameter names that stage's __init__ accepts."""
    try:
        sig = inspect.signature(stage_cls.__init__)
        return set(sig.parameters.keys()) - {"self"}
    except (ValueError, TypeError):
        # Fallback for classes without a proper __init__
        return set()


def make_runner(
    stage_cls: type[Stage],
    init_kwargs: dict[str, Any] | None = None,
) -> Callable[[StageContext], Awaitable[StageOutput]]:
    """Create a runner function from a Stage class.

    This creates a callable that instantiates the stage and calls its execute method,
    handling the binding of 'self' automatically. Dependencies are extracted from
    the stage context's data dict.

    Args:
        stage_cls: The Stage class to instantiate
        init_kwargs: Optional static kwargs to pass to constructor (e.g., for testing)
    """
    # Get the parameters this stage's __init__ accepts
    accepted_params = _get_init_params(stage_cls)

    async def runner(ctx: StageContext) -> StageOutput:
        # Extract dependencies from context data
        ctx_data = ctx.config.get("data", {})

        # Build kwargs from context data - only pass what __init__ accepts
        kwargs: dict[str, Any] = {}

        # Add static kwargs if provided
        if init_kwargs:
            for k, v in init_kwargs.items():
                if k in accepted_params:
                    kwargs[k] = v

        # Add dependencies from context data - only if __init__ accepts them
        for dep in STAGE_DEPENDENCIES:
            if dep in ctx_data and dep in accepted_params:
                kwargs[dep] = ctx_data[dep]

        # Create stage instance with dependencies
        stage = stage_cls(**kwargs)
        return await stage.execute(ctx)

    return runner


@dataclass
class Pipeline:
    """Base class for code-defined pipelines.

    Usage:
        class VoiceFastPipeline(Pipeline):
            stages = {
                "voice_input": UnifiedStageSpec(
                    name="voice_input",
                    runner=make_runner(VoiceInputStage),
                    kind=StageKind.TRANSFORM,
                ),
                "stt": UnifiedStageSpec(
                    name="stt",
                    runner=make_runner(SttStage),
                    kind=StageKind.TRANSFORM,
                    dependencies=("voice_input",),
                ),
                # ... more stages
            }

        graph = VoiceFastPipeline().build()
    """
    stages: dict[str, UnifiedStageSpec] = field(default_factory=dict)

    def compose(self, other: Pipeline) -> Pipeline:
        """Merge stages and dependencies from another pipeline.

        Later stages override earlier ones if same name.
        """
        new_stages = {**self.stages, **other.stages}
        return Pipeline(stages=new_stages)

    def build(self) -> UnifiedStageGraph:
        """Generate executable DAG for the orchestrator."""
        return UnifiedStageGraph(list(self.stages.values()))

    def with_stage(
        self,
        name: str,
        stage_cls: type[Stage],
        kind: StageKind,
        dependencies: tuple[str, ...] | None = None,
        conditional: bool = False,
        init_kwargs: dict[str, Any] | None = None,
    ) -> Pipeline:
        """Add a stage to this pipeline (fluent builder)."""
        spec = UnifiedStageSpec(
            name=name,
            runner=make_runner(stage_cls, init_kwargs),
            kind=kind,
            dependencies=dependencies or (),
            conditional=conditional,
        )
        self.stages[name] = spec
        return self


__all__ = ["Pipeline", "make_runner"]
