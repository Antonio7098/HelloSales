"""Tests for the new code-defined Pipeline system."""

import pytest

from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput
from app.ai.substrate.stages.pipeline import Pipeline
from app.ai.substrate.stages.pipeline_registry import pipeline_registry


class DummyStage(Stage):
    """A simple stage for testing."""

    name = "dummy"
    kind = StageKind.TRANSFORM

    def __init__(self, *, value: str = "default"):
        self.value = value

    async def execute(self, _ctx: StageContext) -> StageOutput:
        return StageOutput.ok(data={"value": self.value})


class TestPipelineCreation:
    """Tests for Pipeline instantiation."""

    def test_pipeline_empty_by_default(self):
        """Pipeline can be created empty."""
        pipeline = Pipeline()
        assert pipeline is not None
        assert len(pipeline.stages) == 0

    def test_pipeline_with_stage_via_with_stage(self):
        """Pipeline can be built using with_stage()."""
        pipeline = Pipeline().with_stage(
            "test", DummyStage, StageKind.TRANSFORM
        )
        assert "test" in pipeline.stages


class TestPipelineRegistry:
    """Tests for PipelineRegistry."""

    def test_registry_has_expected_pipelines(self):
        """Registry has all expected pipelines."""
        expected = ["chat_fast", "chat_accurate", "voice_fast", "voice_accurate"]
        for name in expected:
            assert name in pipeline_registry

    def test_registry_can_retrieve_pipeline(self):
        """Registry can retrieve a pipeline by name."""
        pipeline = pipeline_registry.get("chat_fast")
        assert pipeline is not None
        assert isinstance(pipeline, Pipeline)

    def test_registry_get_missing_raises(self):
        """Getting a missing pipeline raises KeyError."""
        with pytest.raises(KeyError):
            pipeline_registry.get("nonexistent")

    def test_registry_list_returns_names(self):
        """Registry list() returns all registered names."""
        names = pipeline_registry.list()
        assert "chat_fast" in names
        assert "chat_accurate" in names
        assert "voice_fast" in names
        assert "voice_accurate" in names


class TestPipelineBuild:
    """Tests for Pipeline.build()."""

    def test_build_empty_pipeline_raises(self):
        """Empty pipeline cannot be built (UnifiedStageGraph requires at least one stage)."""
        pipeline = Pipeline()
        with pytest.raises(ValueError, match="UnifiedStageGraph requires at least one UnifiedStageSpec"):
            pipeline.build()

    def test_build_pipeline_with_stages(self):
        """Pipeline with stages can be built."""
        pipeline = Pipeline().with_stage(
            "dummy", DummyStage, StageKind.TRANSFORM
        )
        graph = pipeline.build()
        assert len(graph.stage_specs) == 1
        assert graph.stage_specs[0].name == "dummy"


class TestPipelineComposition:
    """Tests for Pipeline.compose()."""

    def test_compose_merges_stages(self):
        """compose() merges stages from two pipelines."""
        p1 = Pipeline().with_stage("a", DummyStage, StageKind.TRANSFORM)
        p2 = Pipeline().with_stage("b", DummyStage, StageKind.TRANSFORM)
        merged = p1.compose(p2)
        assert "a" in merged.stages
        assert "b" in merged.stages

    def test_compose_overrides_duplicate(self):
        """compose() overrides stages with same name."""
        p1 = Pipeline().with_stage("x", DummyStage, StageKind.TRANSFORM)
        p2 = Pipeline().with_stage("x", DummyStage, StageKind.ENRICH)
        merged = p1.compose(p2)
        # The runner should be from the second pipeline
        assert merged.stages["x"].kind == StageKind.ENRICH


class TestConcretePipelines:
    """Tests for concrete pipeline implementations."""

    def test_chat_fast_pipeline_has_stages(self):
        """ChatFastPipeline has the expected number of stages."""
        pipeline = pipeline_registry.get("chat_fast")
        assert len(pipeline.stages) > 0

    def test_chat_accurate_pipeline_has_stages(self):
        """ChatAccuratePipeline has the expected number of stages."""
        pipeline = pipeline_registry.get("chat_accurate")
        assert len(pipeline.stages) > 0

    def test_voice_fast_pipeline_has_stages(self):
        """VoiceFastPipeline has the expected number of stages."""
        pipeline = pipeline_registry.get("voice_fast")
        assert len(pipeline.stages) > 0

    def test_voice_accurate_pipeline_has_stages(self):
        """VoiceAccuratePipeline has the expected number of stages."""
        pipeline = pipeline_registry.get("voice_accurate")
        assert len(pipeline.stages) > 0

    def test_all_pipelines_can_build(self):
        """All pipelines can be built into graphs."""
        for name in pipeline_registry.list():
            pipeline = pipeline_registry.get(name)
            graph = pipeline.build()
            assert graph is not None
            assert len(graph.stage_specs) == len(pipeline.stages)
