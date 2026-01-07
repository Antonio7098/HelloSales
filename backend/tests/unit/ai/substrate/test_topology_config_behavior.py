"""Tests for Topology / Configuration / Behavior architecture.

This test suite validates the implementation of the Topology / Configuration /
Behavior architecture that separates:
- Topology: Pipeline structure (stages and order) defined in topologies
  (e.g., "chat_fast", "voice_accurate").
- Configuration: Static stage parameters defined per-topology.
- Behavior: Runtime logic selection via ``ctx.behavior`` (e.g., "practice", "roleplay").
"""
import uuid

from app.ai.substrate.agent.context_snapshot import ContextSnapshot
from app.ai.substrate.stages import stage_registry
from app.ai.substrate.stages.base import StageContext, StageKind
from app.ai.substrate.stages.pipeline_registry import pipeline_registry


class TestTopologyConfigBehavior:
    """Test the Topology/Configuration/Behavior architecture implementation."""

    def test_stage_context_carries_topology_and_behavior(self):
        """Test that StageContext carries topology and behavior."""
        pipeline_run_id = uuid.uuid4()
        request_id = uuid.uuid4()
        session_id = uuid.uuid4()
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        interaction_id = uuid.uuid4()

        snapshot = ContextSnapshot(
            pipeline_run_id=pipeline_run_id,
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            interaction_id=interaction_id,
            topology="chat_fast",
            channel="chat",
            behavior="practice",
        )

        ctx = StageContext(
            snapshot=snapshot,
            config={},
        )

        assert ctx.snapshot.topology == "chat_fast"
        assert ctx.snapshot.behavior == "practice"
        assert ctx.snapshot.channel == "chat"

    def test_registry_has_all_pipelines(self):
        """Test that registry has all expected pipelines."""
        expected = ["chat_fast", "chat_accurate", "voice_fast", "voice_accurate"]
        for name in expected:
            assert name in pipeline_registry, f"Pipeline '{name}' not found in registry"

    def test_pipeline_can_be_retrieved_and_built(self):
        """Test that pipelines can be retrieved and built."""
        pipeline = pipeline_registry.get("chat_fast")
        assert pipeline is not None
        graph = pipeline.build()
        assert graph is not None

    def test_stage_kind_classification(self):
        """Test that stages are correctly classified by kind."""

        # Verify stages have correct kinds
        for name, reg in stage_registry._registry.items():
            assert reg.kind in StageKind
            assert reg.name == name

    def test_voice_pipeline_has_voice_stages(self):
        """Test that voice pipelines have voice-specific stages."""
        pipeline = pipeline_registry.get("voice_fast")
        stage_names = set(pipeline.stages.keys())

        # Voice pipeline should have voice-specific stages
        assert "voice_input" in stage_names
        assert "stt" in stage_names
        assert "tts_incremental" in stage_names

    def test_chat_pipeline_does_not_have_voice_stages(self):
        """Test that chat pipelines don't have voice-specific stages."""
        pipeline = pipeline_registry.get("chat_fast")
        stage_names = set(pipeline.stages.keys())

        # Chat pipeline should NOT have voice-specific stages
        assert "voice_input" not in stage_names
        assert "stt" not in stage_names
        assert "tts_incremental" not in stage_names
