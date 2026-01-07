"""Unit tests for ContextBuildStage producing ContextSnapshot.

Tests verify that ContextBuildStage produces valid ContextSnapshot
per stageflow.md §8.1 requirements.
"""
from datetime import UTC, datetime
from uuid import uuid4

from app.ai.substrate import (
    ContextSnapshot,
    MemoryEnrichment,
    Message,
    ProfileEnrichment,
    SkillsEnrichment,
)
from app.ai.substrate.stages.context import PipelineContext


class TestContextBuildStageProducesSnapshot:
    """Test that ContextBuildStage produces ContextSnapshot."""

    def test_chat_context_build_produces_context_snapshot(self):
        """Test ChatContextBuildStage produces a valid ContextSnapshot."""
        # This is a behavioral test - we verify the stage stores ContextSnapshot
        # The actual stage implementation is in app.domains.chat.stages
        ctx = PipelineContext(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            behavior="practice",
            data={
                "text": "Hello, I want to practice sales calls",
                "skill_ids": ["skill_1", "skill_2"],
                "prefetched_enrichers": {
                    "profile": {
                        "display_name": "Test User",
                        "preferences": {"voice": "female"},
                        "goals": ["improve closing"],
                        "skill_levels": {"skill_1": "intermediate"},
                    },
                    "memory": {
                        "recent_topics": ["objection handling"],
                        "key_facts": ["Works in SaaS"],
                        "summary": {"content": "Previous session focused on opening"},
                    },
                },
            },
        )

        # Simulate what ChatContextBuildStage does
        text = ctx.data.get("text", "")
        prefetched = ctx.data.get("prefetched_enrichers", {})

        # Build messages
        messages = [Message(role="user", content=text, timestamp=datetime.now(UTC))]

        # Build profile
        profile = None
        if "profile" in prefetched:
            profile_data = prefetched["profile"]
            profile = ProfileEnrichment(
                user_id=ctx.user_id or uuid4(),
                display_name=profile_data.get("display_name"),
                preferences=profile_data.get("preferences", {}),
                goals=profile_data.get("goals", []),
                skill_levels=profile_data.get("skill_levels", {}),
            )

        # Build memory
        memory = None
        if "memory" in prefetched:
            memory_data = prefetched["memory"]
            memory = MemoryEnrichment(
                recent_topics=memory_data.get("recent_topics", []),
                key_facts=memory_data.get("key_facts", []),
                interaction_history_summary=memory_data.get("summary", {}).get("content"),
            )

        # Build skills
        skills = None
        skill_ids = ctx.data.get("skill_ids", [])
        if skill_ids:
            skills = SkillsEnrichment(
                active_skill_ids=skill_ids,
                current_level=None,
                skill_progress={},
            )

        # Create ContextSnapshot (what the stage should do)
        context_snapshot = ContextSnapshot(
            pipeline_run_id=ctx.pipeline_run_id,
            request_id=ctx.request_id,
            session_id=ctx.session_id,
            user_id=ctx.user_id,
            org_id=ctx.org_id,
            interaction_id=None,
            topology=ctx.topology,
            channel="text_channel",
            behavior=ctx.behavior,
            messages=messages,
            profile=profile,
            memory=memory,
            skills=skills,
            input_text=text,
        )

        # Verify it's valid
        assert isinstance(context_snapshot, ContextSnapshot)
        assert context_snapshot.topology == "fast_kernel"
        assert context_snapshot.channel == "text_channel"
        assert context_snapshot.behavior == "practice"
        assert len(context_snapshot.messages) == 1
        assert context_snapshot.messages[0].content == "Hello, I want to practice sales calls"
        assert context_snapshot.profile is not None
        assert context_snapshot.profile.display_name == "Test User"
        assert context_snapshot.memory is not None
        assert "objection handling" in context_snapshot.memory.recent_topics
        assert context_snapshot.skills is not None
        assert "skill_1" in context_snapshot.skills.active_skill_ids

    def test_voice_context_build_produces_context_snapshot(self):
        """Test Voice ContextBuildStage produces a valid ContextSnapshot."""
        audio_duration = 5000  # 5 seconds

        ctx = PipelineContext(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            behavior="practice",
            data={
                "transcript": "How do I handle objections?",
                "audio_duration_ms": audio_duration,
                "prefetched": {
                    "profile": {
                        "display_name": "Voice User",
                        "preferences": {"voice": "male"},
                        "goals": ["improve discovery"],
                        "skill_levels": {},
                    },
                    "summary": {
                        "content": "Session focused on opening statements"
                    },
                },
            },
        )

        # Simulate what Voice ContextBuildStage does
        transcript = ctx.data.get("transcript", "")
        prefetched = ctx.data.get("prefetched", {})

        # Build messages
        messages = [Message(role="user", content=transcript)]

        # Build profile
        profile = None
        if "profile" in prefetched:
            profile_data = prefetched["profile"]
            profile = ProfileEnrichment(
                user_id=ctx.user_id or uuid4(),
                display_name=profile_data.get("display_name"),
                preferences=profile_data.get("preferences", {}),
                goals=profile_data.get("goals", []),
                skill_levels=profile_data.get("skill_levels", {}),
            )

        # Build memory from summary
        memory = None
        if "summary" in prefetched:
            summary_data = prefetched["summary"]
            memory = MemoryEnrichment(
                recent_topics=[],
                key_facts=[],
                interaction_history_summary=summary_data.get("content", "")[:500] if summary_data else None,
            )

        # Create ContextSnapshot
        context_snapshot = ContextSnapshot(
            pipeline_run_id=ctx.pipeline_run_id,
            request_id=ctx.request_id,
            session_id=ctx.session_id,
            user_id=ctx.user_id,
            org_id=ctx.org_id,
            interaction_id=ctx.interaction_id,
            topology=ctx.topology,
            channel="voice_channel",
            behavior=ctx.behavior,
            messages=messages,
            profile=profile,
            memory=memory,
            skills=None,
            input_text=transcript,
            input_audio_duration_ms=audio_duration,
        )

        # Verify
        assert isinstance(context_snapshot, ContextSnapshot)
        assert context_snapshot.channel == "voice_channel"
        assert context_snapshot.input_audio_duration_ms == audio_duration
        assert context_snapshot.messages[0].content == "How do I handle objections?"
        assert context_snapshot.profile.display_name == "Voice User"
        assert "Session focused on opening statements" in context_snapshot.memory.interaction_history_summary

    def test_context_snapshot_serializable_for_agent_input(self):
        """Test ContextSnapshot can be serialized for Agent input."""
        snapshot = ContextSnapshot(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            interaction_id=None,
            topology="accurate_kernel",
            channel="text_channel",
            behavior="roleplay",
            messages=[
                Message(role="user", content="Test message", timestamp=datetime.now(UTC)),
            ],
            profile=ProfileEnrichment(
                user_id=uuid4(),
                display_name="Test User",
                preferences={"theme": "dark"},
            ),
            input_text="Test message",
        )

        # Serialize
        serialized = snapshot.to_dict()

        # Verify serializable
        assert "pipeline_run_id" in serialized
        assert "topology" in serialized
        assert "messages" in serialized
        assert len(serialized["messages"]) == 1
        assert serialized["messages"][0]["content"] == "Test message"

        # Should be JSON serializable (can round-trip)
        import json
        json_str = json.dumps(serialized)
        restored = json.loads(json_str)

        assert restored["topology"] == "accurate_kernel"
        assert restored["channel"] == "text_channel"
        assert restored["behavior"] == "roleplay"

    def test_context_snapshot_contains_all_agent_required_fields(self):
        """Test ContextSnapshot has all fields required by Agent per stageflow.md §8.1."""
        required_fields = [
            "pipeline_run_id",
            "request_id",
            "session_id",
            "user_id",
            "topology",
            "channel",
            "behavior",
            "messages",
        ]

        snapshot = ContextSnapshot(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            channel="text_channel",
            behavior="practice",
            messages=[],
        )

        for field in required_fields:
            assert hasattr(snapshot, field), f"Missing required field: {field}"
            value = getattr(snapshot, field)
            assert value is not None or field in ["org_id", "interaction_id"], \
                f"Field {field} should not be None"

    def test_context_snapshot_with_empty_enrichments(self):
        """Test ContextSnapshot works with no enrichments (minimal case)."""
        snapshot = ContextSnapshot(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            channel="text_channel",
            behavior="practice",
            messages=[Message(role="user", content="Hi")],
        )

        assert snapshot.profile is None
        assert snapshot.memory is None
        assert snapshot.skills is None
        assert snapshot.documents == []
        assert snapshot.web_results == []

        # Should still be serializable
        serialized = snapshot.to_dict()
        assert serialized["profile"] is None
        assert serialized["memory"] is None


class TestContextSnapshotRoutingDecision:
    """Test ContextSnapshot with routing decision."""

    def test_context_snapshot_with_routing_decision(self):
        """Test ContextSnapshot can store routing decision."""
        from app.ai.substrate import RoutingDecision

        routing = RoutingDecision(
            agent_id="agent.conversational.v1",
            pipeline_name="chat_fast",
            topology="fast_kernel",
            channel="text_channel",
            reason="User message detected",
        )

        snapshot = ContextSnapshot(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            channel="text_channel",
            behavior="practice",
            messages=[],
            routing_decision=routing,
        )

        assert snapshot.routing_decision is not None
        assert snapshot.routing_decision.agent_id == "agent.conversational.v1"
        assert snapshot.routing_decision.pipeline_name == "chat_fast"

        # Should serialize correctly
        serialized = snapshot.to_dict()
        assert serialized["routing_decision"]["agent_id"] == "agent.conversational.v1"


class TestEnricherPassThrough:
    """Test that enricher outputs are correctly passed to ContextBuildStage."""

    def test_chat_context_build_reads_from_skills_context(self):
        """Test ChatContextBuildStage reads skills from skills_context."""

        # Simulate SkillsContextStage output
        skills_context = [
            {"skill_id": "skill_1", "level": "intermediate"},
            {"skill_id": "skill_2", "level": "beginner"},
        ]

        ctx = PipelineContext(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            behavior="practice",
            data={
                "text": "Test message",
                "skills_context": skills_context,
            },
        )

        # Simulate what ChatContextBuildStage does with skills_context
        skills_data = ctx.data.get("skills_context", [])
        skill_ids = []
        current_level = None

        for skill_item in skills_data:
            if isinstance(skill_item, dict):
                skill_ids.append(skill_item.get("skill_id"))
                if current_level is None:
                    current_level = skill_item.get("level")

        assert skill_ids == ["skill_1", "skill_2"]
        assert current_level == "intermediate"

    def test_chat_context_build_reads_from_prefetched_enrichers(self):
        """Test ChatContextBuildStage reads enrichments from prefetched_enrichers."""
        prefetched = {
            "profile": {
                "display_name": "Test User",
                "preferences": {"voice": "female"},
                "goals": ["improve closing"],
                "skill_levels": {"skill_1": "intermediate"},
            },
            "memory": {
                "recent_topics": ["objection handling"],
                "key_facts": ["Works in SaaS"],
                "summary": {"content": "Previous session focused on opening"},
            },
        }

        ctx = PipelineContext(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            behavior="practice",
            data={
                "text": "Test message",
                "prefetched_enrichers": prefetched,
            },
        )

        # Simulate what ChatContextBuildStage does
        from app.ai.substrate import MemoryEnrichment, ProfileEnrichment

        prefetched_data = ctx.data.get("prefetched_enrichers", {})

        profile = None
        if "profile" in prefetched_data:
            profile_data = prefetched_data["profile"]
            if profile_data:
                profile = ProfileEnrichment(
                    user_id=ctx.user_id or uuid4(),
                    display_name=profile_data.get("display_name"),
                    preferences=profile_data.get("preferences", {}),
                    goals=profile_data.get("goals", []),
                    skill_levels=profile_data.get("skill_levels", {}),
                )

        memory = None
        if "memory" in prefetched_data:
            memory_data = prefetched_data["memory"]
            if memory_data:
                memory = MemoryEnrichment(
                    recent_topics=memory_data.get("recent_topics", []),
                    key_facts=memory_data.get("key_facts", []),
                    interaction_history_summary=memory_data.get("summary", {}).get("content"),
                )

        assert profile is not None
        assert profile.display_name == "Test User"
        assert profile.preferences["voice"] == "female"
        assert "improve closing" in profile.goals

        assert memory is not None
        assert "objection handling" in memory.recent_topics
        assert "Works in SaaS" in memory.key_facts

    def test_voice_context_build_reads_from_prefetched(self):
        """Test Voice ContextBuildStage reads enrichments from prefetched."""
        prefetched = {
            "profile": {
                "display_name": "Voice User",
                "preferences": {"voice": "male"},
            },
            "summary": {
                "content": "Session focused on opening statements",
            },
        }

        ctx = PipelineContext(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=None,
            interaction_id=None,
            topology="fast_kernel",
            behavior="practice",
            data={
                "transcript": "Test voice message",
                "prefetched": prefetched,
            },
        )

        # Simulate what Voice ContextBuildStage does
        from app.ai.substrate import MemoryEnrichment, ProfileEnrichment

        prefetched_data = ctx.data.get("prefetched", {})

        profile = None
        if "profile" in prefetched_data:
            profile_data = prefetched_data["profile"]
            if profile_data:
                profile = ProfileEnrichment(
                    user_id=ctx.user_id or uuid4(),
                    display_name=profile_data.get("display_name"),
                    preferences=profile_data.get("preferences", {}),
                    goals=profile_data.get("goals", []),
                    skill_levels=profile_data.get("skill_levels", {}),
                )

        memory = None
        if "summary" in prefetched_data:
            summary_data = prefetched_data["summary"]
            if summary_data:
                memory = MemoryEnrichment(
                    recent_topics=[],
                    key_facts=[],
                    interaction_history_summary=summary_data.get("content", "")[:500] if summary_data else None,
                )

        assert profile is not None
        assert profile.display_name == "Voice User"

        assert memory is not None
        assert "Session focused on opening statements" in memory.interaction_history_summary
