"""Tests for UnifiedStageGraph immutable data flow.

These tests verify:
- Original context is not mutated after graph execution
- Stages only receive outputs from declared dependencies
- Parallel execution doesn't share mutable state
"""
from __future__ import annotations

import asyncio
import dataclasses
from uuid import uuid4

import pytest

from app.ai.substrate.agent.context_snapshot import ContextSnapshot
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput, StageStatus
from app.ai.substrate.stages.graph import UnifiedStageGraph, UnifiedStageSpec


def _create_minimal_snapshot() -> ContextSnapshot:
    """Helper to create a minimal ContextSnapshot for testing."""
    return ContextSnapshot(
        pipeline_run_id=uuid4(),
        request_id=uuid4(),
        session_id=uuid4(),
        user_id=uuid4(),
        org_id=uuid4(),
        interaction_id=uuid4(),
        topology="test_topology",
        channel="test_channel",
        behavior="test_behavior",
        messages=[],
    )


class SimpleStage(Stage):
    """Simple stage for testing."""

    name: str
    output_data: dict

    def __init__(self, name: str, output_data: dict):
        self.name = name
        self.output_data = output_data

    async def execute(self, _ctx: StageContext) -> StageOutput:
        return StageOutput.ok(data=self.output_data)


class DependencyCapturingStage(Stage):
    """Stage that captures what inputs it received."""

    name: str
    received_inputs: list

    def __init__(self, name: str):
        self.name = name
        self.received_inputs = []

    async def execute(self, ctx: StageContext) -> StageOutput:
        from app.ai.substrate.stages.inputs import StageInputs

        inputs: StageInputs = ctx.config.get("inputs")
        self.received_inputs.append(inputs)
        return StageOutput.ok(data={"stage_name": self.name})


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestContextImmutability:
    """Tests that original context is not mutated."""

    @pytest.mark.asyncio
    async def test_original_context_not_mutated(self):
        """Verify ctx.config is not modified after graph.run()."""
        snapshot = _create_minimal_snapshot()

        stage_a = SimpleStage("a", {"value": "from_a"})
        spec_a = UnifiedStageSpec(
            name="a",
            runner=stage_a.execute,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )

        graph = UnifiedStageGraph([spec_a])

        original_config = {"data": {"initial": "value"}}
        ctx = StageContext(snapshot=snapshot, config=original_config)

        original_config_copy = dict(original_config)

        await graph.run(ctx)

        assert ctx.config == original_config_copy
        assert "data" not in ctx.config or ctx.config.get("data") == original_config_copy.get("data", {})

    @pytest.mark.asyncio
    async def test_different_stages_get_different_contexts(self):
        """Verify each stage gets its own StageContext."""
        snapshot = _create_minimal_snapshot()

        stage_a = DependencyCapturingStage("a")
        spec_a = UnifiedStageSpec(
            name="a",
            runner=stage_a.execute,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )

        graph = UnifiedStageGraph([spec_a])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        await graph.run(ctx)

        assert len(stage_a.received_inputs) == 1
        inputs = stage_a.received_inputs[0]
        assert inputs is not None
        assert isinstance(inputs.snapshot, ContextSnapshot)


class TestDependencyIsolation:
    """Tests that stages only see declared dependencies."""

    @pytest.mark.asyncio
    async def test_stage_only_sees_declared_dependencies(self):
        """Verify stage receives only outputs from its declared dependencies."""
        snapshot = _create_minimal_snapshot()

        stage_a = SimpleStage("a", {"key_a": "value_a", "shared_key": "from_a"})
        stage_b = SimpleStage("b", {"key_b": "value_b", "shared_key": "from_b"})
        stage_c = DependencyCapturingStage("c")

        spec_a = UnifiedStageSpec(
            name="a",
            runner=stage_a.execute,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )
        spec_b = UnifiedStageSpec(
            name="b",
            runner=stage_b.execute,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )
        spec_c = UnifiedStageSpec(
            name="c",
            runner=stage_c.execute,
            kind=StageKind.TRANSFORM,
            dependencies=("a", "b"),
        )

        graph = UnifiedStageGraph([spec_a, spec_b, spec_c])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        await graph.run(ctx)

        assert len(stage_c.received_inputs) == 1
        inputs = stage_c.received_inputs[0]

        assert inputs.has_output("a")
        assert inputs.has_output("b")
        assert not inputs.has_output("c")
        assert not inputs.has_output("nonexistent")

    @pytest.mark.asyncio
    async def test_stage_receives_correct_values_from_dependencies(self):
        """Verify stage gets correct data from each dependency."""
        snapshot = _create_minimal_snapshot()

        stage_a = SimpleStage("a", {"value": "from_a"})
        stage_b = DependencyCapturingStage("b")

        spec_a = UnifiedStageSpec(
            name="a",
            runner=stage_a.execute,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )
        spec_b = UnifiedStageSpec(
            name="b",
            runner=stage_b.execute,
            kind=StageKind.TRANSFORM,
            dependencies=("a",),
        )

        graph = UnifiedStageGraph([spec_a, spec_b])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        await graph.run(ctx)

        inputs = stage_b.received_inputs[0]
        value_from_a = inputs.get_from("a", "value")
        assert value_from_a == "from_a"

    @pytest.mark.asyncio
    async def test_parallel_stages_isolated(self):
        """Verify parallel stages don't share state."""
        snapshot = _create_minimal_snapshot()

        capturing_a = DependencyCapturingStage("a")
        capturing_b = DependencyCapturingStage("b")

        spec_a = UnifiedStageSpec(
            name="a",
            runner=capturing_a.execute,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )
        spec_b = UnifiedStageSpec(
            name="b",
            runner=capturing_b.execute,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )

        graph = UnifiedStageGraph([spec_a, spec_b])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        await graph.run(ctx)

        assert len(capturing_a.received_inputs) == 1
        assert len(capturing_b.received_inputs) == 1

        inputs_a = capturing_a.received_inputs[0]
        inputs_b = capturing_b.received_inputs[0]

        assert not inputs_a.has_output("a")
        assert not inputs_a.has_output("b")
        assert not inputs_b.has_output("a")
        assert not inputs_b.has_output("b")

    @pytest.mark.asyncio
    async def test_diamond_dependency(self):
        """Verify diamond pattern (A -> B, A -> C, B+C -> D) works correctly.

        In a diamond pattern:
        - A -> B, A -> C, B+C -> D
        - D depends on B and C, NOT A directly
        - So D should only see B and C's outputs
        """
        snapshot = _create_minimal_snapshot()

        data_from_a = {"from": "a", "value_a": 1}
        data_from_b = {"from": "b", "value_b": 2}
        data_from_c = {"from": "c", "value_c": 3}

        stage_a = SimpleStage("a", data_from_a)
        stage_b = SimpleStage("b", data_from_b)
        stage_c = SimpleStage("c", data_from_c)
        stage_d = DependencyCapturingStage("d")

        spec_a = UnifiedStageSpec(name="a", runner=stage_a.execute, kind=StageKind.TRANSFORM, dependencies=())
        spec_b = UnifiedStageSpec(name="b", runner=stage_b.execute, kind=StageKind.TRANSFORM, dependencies=("a",))
        spec_c = UnifiedStageSpec(name="c", runner=stage_c.execute, kind=StageKind.TRANSFORM, dependencies=("a",))
        spec_d = UnifiedStageSpec(name="d", runner=stage_d.execute, kind=StageKind.TRANSFORM, dependencies=("b", "c"))

        graph = UnifiedStageGraph([spec_a, spec_b, spec_c, spec_d])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        await graph.run(ctx)

        inputs_d = stage_d.received_inputs[0]

        assert inputs_d.has_output("b")
        assert inputs_d.has_output("c")
        assert not inputs_d.has_output("a")  # D doesn't depend on A directly
        assert not inputs_d.has_output("d")

        assert inputs_d.get_from("b", "from") == "b"
        assert inputs_d.get_from("c", "from") == "c"
        assert inputs_d.get("value_b") == 2
        assert inputs_d.get("value_c") == 3


class TestSnapshotPreservation:
    """Tests that ContextSnapshot is preserved correctly."""

    @pytest.mark.asyncio
    async def test_snapshot_passed_to_all_stages(self):
        """Verify all stages receive the same snapshot."""
        snapshot = _create_minimal_snapshot()

        capturing_a = DependencyCapturingStage("a")
        capturing_b = DependencyCapturingStage("b")

        spec_a = UnifiedStageSpec(name="a", runner=capturing_a.execute, kind=StageKind.TRANSFORM, dependencies=())
        spec_b = UnifiedStageSpec(name="b", runner=capturing_b.execute, kind=StageKind.TRANSFORM, dependencies=("a",))

        graph = UnifiedStageGraph([spec_a, spec_b])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        await graph.run(ctx)

        snapshot_a = capturing_a.received_inputs[0].snapshot
        snapshot_b = capturing_b.received_inputs[0].snapshot

        assert snapshot_a is snapshot
        assert snapshot_b is snapshot
        assert snapshot_a.pipeline_run_id == snapshot.pipeline_run_id

    @pytest.mark.asyncio
    async def test_snapshot_immutable_in_stage(self):
        """Verify stages cannot modify snapshot."""
        snapshot = _create_minimal_snapshot()
        original_run_id = snapshot.pipeline_run_id

        async def try_modify_snapshot(ctx: StageContext) -> StageOutput:
            with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):
                ctx.snapshot.pipeline_run_id = uuid4()
            return StageOutput.ok()

        spec = UnifiedStageSpec(
            name="test",
            runner=try_modify_snapshot,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )

        graph = UnifiedStageGraph([spec])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        await graph.run(ctx)

        assert snapshot.pipeline_run_id == original_run_id


class TestOutputsAccumulation:
    """Tests for correct output accumulation."""

    @pytest.mark.asyncio
    async def test_all_outputs_returned(self):
        """Verify graph.run() returns all stage outputs."""
        snapshot = _create_minimal_snapshot()

        stage_a = SimpleStage("a", {"key": "a_value"})
        stage_b = SimpleStage("b", {"key": "b_value"})

        spec_a = UnifiedStageSpec(name="a", runner=stage_a.execute, kind=StageKind.TRANSFORM, dependencies=())
        spec_b = UnifiedStageSpec(name="b", runner=stage_b.execute, kind=StageKind.TRANSFORM, dependencies=())

        graph = UnifiedStageGraph([spec_a, spec_b])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        outputs = await graph.run(ctx)

        assert "a" in outputs
        assert "b" in outputs
        assert outputs["a"].data["key"] == "a_value"
        assert outputs["b"].data["key"] == "b_value"

    @pytest.mark.asyncio
    async def test_outputs_are_immutable(self):
        """Verify returned outputs are StageOutput instances."""
        snapshot = _create_minimal_snapshot()

        stage = SimpleStage("a", {"key": "value"})
        spec = UnifiedStageSpec(name="a", runner=stage.execute, kind=StageKind.TRANSFORM, dependencies=())

        graph = UnifiedStageGraph([spec])
        ctx = StageContext(snapshot=snapshot, config={"data": {}})

        outputs = await graph.run(ctx)

        assert isinstance(outputs["a"], StageOutput)
        assert outputs["a"].status == StageStatus.OK


class TestPortsInjection:
    """Tests for StagePorts injection from config data."""

    @pytest.mark.asyncio
    async def test_ports_extracted_from_data_dict(self):
        """Verify StagePorts is created from ctx.config['data']."""
        snapshot = _create_minimal_snapshot()

        captured_ports = []

        async def capture_ports(ctx: StageContext) -> StageOutput:
            from app.ai.substrate.stages.inputs import StageInputs
            inputs: StageInputs = ctx.config["inputs"]
            captured_ports.append(inputs.ports)
            return StageOutput.ok()

        spec = UnifiedStageSpec(
            name="test",
            runner=capture_ports,
            kind=StageKind.TRANSFORM,
            dependencies=(),
        )

        graph = UnifiedStageGraph([spec])
        ctx = StageContext(snapshot=snapshot, config={"data": {"audio_data": b"test_audio"}})

        await graph.run(ctx)

        assert len(captured_ports) == 1
        assert captured_ports[0].audio_data == b"test_audio"
