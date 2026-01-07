"""Tests for the stage registry system."""


from app.ai.substrate.stages import (
    get_stage,
    list_stages,
    register_stage,
    stage_registry,
)
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput


class TestStageRegistry:
    """Test stage registry functionality."""

    def setup_method(self):
        """Clear registry before each test."""
        stage_registry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        stage_registry.clear()

    def test_register_stage(self):
        """Test registering a stage."""

        @register_stage()
        class TestStage(Stage):
            name = "test_stage"
            kind = StageKind.TRANSFORM

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        # Verify stage is registered
        assert "test_stage" in stage_registry._registry
        reg = stage_registry._registry["test_stage"]
        assert reg.name == "test_stage"
        assert reg.kind == StageKind.TRANSFORM

    def test_get_stage(self):
        """Test retrieving a stage by name."""

        @register_stage()
        class MyStage(Stage):
            name = "my_stage"
            kind = StageKind.ENRICH

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        # Verify stage can be retrieved
        stage_cls = get_stage("my_stage")
        assert stage_cls is not None
        assert stage_cls.__name__ == "MyStage"

    def test_list_stages(self):
        """Test listing all registered stages."""

        @register_stage(kind=StageKind.TRANSFORM)
        class Stage1(Stage):
            name = "stage1"
            kind = StageKind.TRANSFORM

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        @register_stage(kind=StageKind.ENRICH)
        class Stage2(Stage):
            name = "stage2"
            kind = StageKind.ENRICH

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        stages = list_stages()
        assert len(stages) >= 2
        assert "stage1" in stages
        assert "stage2" in stages

    def test_register_with_kind(self):
        """Test registering a stage with explicit kind."""

        @register_stage(kind=StageKind.GUARD)
        class GuardStage(Stage):
            name = "guard_stage"
            kind = StageKind.GUARD

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        reg = stage_registry._registry.get("guard_stage")
        assert reg is not None
        assert reg.kind == StageKind.GUARD

    def test_clear_registry(self):
        """Test clearing the registry."""

        @register_stage()
        class TempStage(Stage):
            name = "temp_stage"
            kind = StageKind.TRANSFORM

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        assert "temp_stage" in stage_registry._registry

        stage_registry.clear()

        assert "temp_stage" not in stage_registry._registry
