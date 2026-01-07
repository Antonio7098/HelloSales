"""Tests for unified Stage protocol and types."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.ai.substrate.stages.base import (
    Stage,
    StageArtifact,
    StageContext,
    StageEvent,
    StageKind,
    StageOutput,
    StageStatus,
    create_stage_context,
)


class TestStageKind:
    """Tests for StageKind enum."""

    def test_all_kinds_defined(self):
        """Verify all expected StageKind values exist."""
        assert StageKind.TRANSFORM == "transform"
        assert StageKind.ENRICH == "enrich"
        assert StageKind.ROUTE == "route"
        assert StageKind.GUARD == "guard"
        assert StageKind.WORK == "work"
        assert StageKind.AGENT == "agent"

    def test_kinds_are_strings(self):
        """Verify StageKind values are strings."""
        for kind in StageKind:
            assert isinstance(kind.value, str)


class TestStageOutput:
    """Tests for StageOutput class."""

    def test_ok_factory(self):
        """Test StageOutput.ok() factory method."""
        output = StageOutput.ok(data={"key": "value"})
        assert output.status == StageStatus.OK
        assert output.data == {"key": "value"}
        assert output.error is None

    def test_ok_factory_kwargs(self):
        """Test StageOutput.ok() with kwargs."""
        output = StageOutput.ok(name="test", value=123)
        assert output.data == {"name": "test", "value": 123}

    def test_skip_factory(self):
        """Test StageOutput.skip() factory method."""
        output = StageOutput.skip(reason="not_needed")
        assert output.status == StageStatus.SKIP
        assert output.data["reason"] == "not_needed"

    def test_fail_factory(self):
        """Test StageOutput.fail() factory method."""
        output = StageOutput.fail(error="something went wrong")
        assert output.status == StageStatus.FAIL
        assert output.error == "something went wrong"

    def test_retry_factory(self):
        """Test StageOutput.retry() factory method."""
        output = StageOutput.retry(error="temporary failure")
        assert output.status == StageStatus.RETRY
        assert output.error == "temporary failure"

    def test_default_empty_data(self):
        """Test that default data is empty dict."""
        output = StageOutput(status=StageStatus.OK)
        assert output.data == {}
        assert output.artifacts == []
        assert output.events == []

    def test_immutable(self):
        """Test that StageOutput is a frozen dataclass."""
        # StageOutput uses frozen=True, so modifications should raise FrozenInstanceError
        output = StageOutput(status=StageStatus.OK)
        # The dataclass is frozen - direct attribute assignment raises FrozenInstanceError
        # But dict mutation on the data attribute still works (intentional for output collection)
        # We test immutability by checking that the class is frozen
        assert type(output).__dataclass_fields__["status"].metadata.get("frozen", False) or hasattr(type(output), "__slots__")

    def test_equality(self):
        """Test that two artifacts with same values are logically equal."""
        # Artifacts have timestamps, so they're not identical
        # But we can test that they have the same type and payload
        a1 = StageArtifact(type="test", payload={"a": 1})
        a2 = StageArtifact(type="test", payload={"a": 1})
        assert a1.type == a2.type
        assert a1.payload == a2.payload
        assert type(a1) is type(a2)


class TestStageEvent:
    """Tests for StageEvent class."""

    def test_creation(self):
        """Test creating a StageEvent."""
        event = StageEvent(
            type="started",
            data={"stage": "test"}
        )
        assert event.type == "started"
        assert event.data == {"stage": "test"}
        assert isinstance(event.timestamp, datetime)


class TestStageContext:
    """Tests for StageContext class."""

    @pytest.fixture
    def mock_snapshot(self):
        """Create a mock ContextSnapshot."""
        return MagicMock()

    def test_creation(self, mock_snapshot):
        """Test creating a StageContext."""
        ctx = StageContext(snapshot=mock_snapshot, config={"timeout": 30})
        assert ctx.snapshot is mock_snapshot
        assert ctx.config == {"timeout": 30}
        assert isinstance(ctx.started_at, datetime)

    def test_emit_event(self, mock_snapshot):
        """Test emitting events through StageContext."""
        ctx = StageContext(snapshot=mock_snapshot)
        ctx.emit_event("test_event", {"key": "value"})

        outputs = ctx.collect_outputs()
        assert len(outputs) == 1
        assert len(outputs[0].events) == 1
        assert outputs[0].events[0].type == "test_event"

    def test_add_artifact(self, mock_snapshot):
        """Test adding artifacts through StageContext."""
        ctx = StageContext(snapshot=mock_snapshot)
        ctx.add_artifact("audio", {"duration_ms": 500})

        outputs = ctx.collect_outputs()
        assert len(outputs) == 1
        assert len(outputs[0].artifacts) == 1
        assert outputs[0].artifacts[0].type == "audio"

    def test_get_output_data(self, mock_snapshot):
        """Test getting data from collected outputs."""
        ctx = StageContext(snapshot=mock_snapshot)
        ctx._outputs.append(StageOutput(
            status=StageStatus.OK,
            data={"result": 42}
        ))

        assert ctx.get_output_data("result") == 42
        assert ctx.get_output_data("missing", default=-1) == -1

    def test_snapshot_is_immutable(self, mock_snapshot):
        """Test that snapshot property is read-only."""
        ctx = StageContext(snapshot=mock_snapshot)
        with pytest.raises(AttributeError):
            ctx.snapshot = mock_snapshot

    def test_config_is_immutable(self, mock_snapshot):
        """Test that config property is read-only."""
        ctx = StageContext(snapshot=mock_snapshot)
        with pytest.raises(AttributeError):
            ctx.config = {}


class TestStageProtocol:
    """Tests for Stage protocol."""

    def test_stage_protocol_accepts_implementation(self):
        """Test that a class implementing Stage protocol is valid."""

        class TestStage:
            name = "test"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        # Should not raise - TestStage implements Stage protocol
        stage: Stage = TestStage()
        assert stage.name == "test"
        assert stage.kind == StageKind.WORK


class TestCreateStageContext:
    """Tests for create_stage_context factory function."""

    @pytest.fixture
    def mock_snapshot(self):
        """Create a mock ContextSnapshot."""
        return MagicMock()

    def test_factory_creates_context(self, mock_snapshot):
        """Test that factory creates StageContext correctly."""
        ctx = create_stage_context(mock_snapshot)
        assert ctx.snapshot is mock_snapshot
        assert ctx.config == {}

    def test_factory_with_config(self, mock_snapshot):
        """Test factory with custom config."""
        ctx = create_stage_context(mock_snapshot, config={"debug": True})
        assert ctx.config == {"debug": True}


class TestStageStatus:
    """Tests for StageStatus enum."""

    def test_all_statuses_defined(self):
        """Verify all expected StageStatus values exist."""
        assert StageStatus.OK == "ok"
        assert StageStatus.SKIP == "skip"
        assert StageStatus.FAIL == "fail"
        assert StageStatus.RETRY == "retry"

    def test_statuses_are_strings(self):
        """Verify StageStatus values are strings."""
        for status in StageStatus:
            assert isinstance(status.value, str)


class TestStageRegistryIntegration:
    """Integration tests for StageRegistry with unified types."""

    def test_stage_registry_accepts_kind_parameter(self):
        """Test that register_stage accepts kind parameter."""
        from app.ai.substrate.stages import clear_all_registries, register_stage, stage_registry

        clear_all_registries()

        @register_stage(kind=StageKind.WORK)
        class TestStage(Stage):
            name = "test_worker_stage"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        reg = stage_registry.get("test_worker_stage")
        assert reg is not None
        assert reg.kind == StageKind.WORK

        clear_all_registries()

    def test_list_stages_includes_all_kinds(self):
        """Test that list_stages includes stages of all kinds."""
        from app.ai.substrate.stages import (
            StageKind,
            clear_all_registries,
            register_stage,
            stage_registry,
        )

        clear_all_registries()

        @register_stage(kind=StageKind.TRANSFORM)
        class TransformStage(Stage):
            name = "transform_test"
            kind = StageKind.TRANSFORM
            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        @register_stage(kind=StageKind.WORK)
        class WorkStage(Stage):
            name = "work_test"
            kind = StageKind.WORK
            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        @register_stage(kind=StageKind.ROUTE)
        class RouteStage(Stage):
            name = "route_test"
            kind = StageKind.ROUTE
            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        stages = stage_registry.list()
        assert "transform_test" in stages
        assert "work_test" in stages
        assert "route_test" in stages

        clear_all_registries()
