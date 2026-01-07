"""Unit tests for ContextSnapshot class.

Tests verify that ContextSnapshot:
- Is immutable (frozen)
- Is serializable to JSON
- Can be deserialized from JSON
- Contains all required fields as per stageflow.md §8.1
"""
import dataclasses
from datetime import datetime
from uuid import uuid4

import pytest

from app.ai.substrate import (
    ContextSnapshot,
    DocumentEnrichment,
    MemoryEnrichment,
    Message,
    ProfileEnrichment,
    RoutingDecision,
    SkillsEnrichment,
)


class TestContextSnapshot:
    """Test ContextSnapshot creation and behavior."""

    def test_create_minimal_context_snapshot(self):
        """Test creating ContextSnapshot with minimal required fields."""
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
        )

        assert snapshot.pipeline_run_id is not None
        assert snapshot.topology == "fast_kernel"
        assert snapshot.channel == "text_channel"
        assert snapshot.behavior == "practice"
        assert snapshot.messages == []
        assert snapshot.documents == []

    def test_context_snapshot_is_immutable(self):
        """Test that ContextSnapshot is frozen (immutable)."""
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
        )

        with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):
            snapshot.behavior = "roleplay"  # type: ignore[attr-defined]

    def test_context_snapshot_with_messages(self):
        """Test ContextSnapshot with message history."""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello, help me practice."),
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
            messages=messages,
        )

        assert len(snapshot.messages) == 2
        assert snapshot.messages[0].role == "system"
        assert snapshot.messages[0].content == "You are a helpful assistant."
        assert snapshot.messages[1].role == "user"

    def test_context_snapshot_with_routing_decision(self):
        """Test ContextSnapshot with routing decision."""
        routing = RoutingDecision(
            agent_id="agent.conversational.v1",
            pipeline_name="chat_fast",
            topology="fast_kernel",
            channel="text_channel",
            reason="User requested fast response",
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
            routing_decision=routing,
        )

        assert snapshot.routing_decision is not None
        assert snapshot.routing_decision.agent_id == "agent.conversational.v1"
        assert snapshot.routing_decision.pipeline_name == "chat_fast"

    def test_context_snapshot_with_profile_enrichment(self):
        """Test ContextSnapshot with profile enrichment."""
        profile = ProfileEnrichment(
            user_id=uuid4(),
            display_name="Test User",
            preferences={"voice": "female", "speed": "normal"},
            goals=["improve closing"],
            skill_levels={"prospecting": "intermediate"},
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
            profile=profile,
        )

        assert snapshot.profile is not None
        assert snapshot.profile.display_name == "Test User"
        assert snapshot.profile.preferences["voice"] == "female"
        assert "improve closing" in snapshot.profile.goals

    def test_context_snapshot_with_memory_enrichment(self):
        """Test ContextSnapshot with memory enrichment."""
        memory = MemoryEnrichment(
            recent_topics=["sales techniques", "objection handling"],
            key_facts=["Customer works in SaaS", "Annual revenue: $10M"],
            interaction_history_summary="User has had 5 practice sessions",
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
            memory=memory,
        )

        assert snapshot.memory is not None
        assert "sales techniques" in snapshot.memory.recent_topics
        assert "Customer works in SaaS" in snapshot.memory.key_facts

    def test_context_snapshot_with_skills_enrichment(self):
        """Test ContextSnapshot with skills enrichment."""
        skills = SkillsEnrichment(
            active_skill_ids=["skill_1", "skill_2"],
            current_level="intermediate",
            skill_progress={"skill_1": 75, "skill_2": 50},
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
            skills=skills,
        )

        assert snapshot.skills is not None
        assert "skill_1" in snapshot.skills.active_skill_ids
        assert snapshot.skills.current_level == "intermediate"

    def test_context_snapshot_with_documents(self):
        """Test ContextSnapshot with document enrichment."""
        doc = DocumentEnrichment(
            document_id="doc_123",
            document_type="sales_script",
            blocks=[
                {"id": "blk_1", "type": "paragraph", "value": "Opening hook..."},
                {"id": "blk_2", "type": "paragraph", "value": "Value proposition..."},
            ],
            metadata={"version": 1},
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
            documents=[doc],
        )

        assert len(snapshot.documents) == 1
        assert snapshot.documents[0].document_id == "doc_123"
        assert len(snapshot.documents[0].blocks) == 2

    def test_context_snapshot_serialization(self):
        """Test ContextSnapshot can be serialized to JSON-serializable dict."""
        original = ContextSnapshot(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            interaction_id=None,
            topology="fast_kernel",
            channel="text_channel",
            behavior="practice",
            messages=[
                Message(role="user", content="Test message", timestamp=datetime(2025, 1, 1, 12, 0, 0))
            ],
            input_text="Hello world",
        )

        # Serialize
        serialized = original.to_dict()

        # Verify serialization
        assert serialized["topology"] == "fast_kernel"
        assert serialized["behavior"] == "practice"
        assert len(serialized["messages"]) == 1
        assert serialized["messages"][0]["content"] == "Test message"
        assert serialized["input_text"] == "Hello world"
        # UUIDs should be converted to strings
        assert isinstance(serialized["user_id"], str)

    def test_context_snapshot_deserialization(self):
        """Test ContextSnapshot can be deserialized from dict."""
        data = {
            "pipeline_run_id": str(uuid4()),
            "request_id": str(uuid4()),
            "session_id": str(uuid4()),
            "user_id": str(uuid4()),
            "org_id": None,
            "interaction_id": None,
            "topology": "accurate_kernel",
            "channel": "voice_channel",
            "behavior": "roleplay",
            "messages": [
                {"role": "user", "content": "Test", "timestamp": "2025-01-01T12:00:00", "metadata": {}}
            ],
            "documents": [],
            "web_results": [],
            "assessment_state": {},
            "input_audio_duration_ms": None,
            "created_at": "2025-01-01T12:00:00",
            "metadata": {},
        }

        snapshot = ContextSnapshot.from_dict(data)

        assert snapshot.topology == "accurate_kernel"
        assert snapshot.channel == "voice_channel"
        assert snapshot.behavior == "roleplay"
        assert len(snapshot.messages) == 1
        assert snapshot.messages[0].content == "Test"
        # UUIDs should be converted back to UUID objects
        assert isinstance(snapshot.user_id, uuid4().__class__)

    def test_context_snapshot_roundtrip(self):
        """Test ContextSnapshot serialization roundtrip preserves data."""
        original = ContextSnapshot(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            interaction_id=uuid4(),
            topology="fast_kernel",
            channel="text_channel",
            behavior="practice",
            messages=[
                Message(role="user", content="Test 1", timestamp=datetime(2025, 1, 1)),
                Message(role="assistant", content="Response 1"),
            ],
            profile=ProfileEnrichment(
                user_id=uuid4(),
                display_name="Test User",
                preferences={"theme": "dark"},
            ),
            memory=MemoryEnrichment(
                recent_topics=["topic1", "topic2"],
                key_facts=["fact1"],
            ),
            skills=SkillsEnrichment(
                active_skill_ids=["skill_1"],
                current_level="beginner",
            ),
            documents=[
                DocumentEnrichment(
                    document_id="doc_1",
                    document_type="script",
                    blocks=[{"id": "blk_1", "type": "heading", "value": "Title"}],
                )
            ],
            input_text="User input text",
            exercise_id="exercise_123",
            assessment_state={"score": 85, "passed": True},
        )

        # Roundtrip
        serialized = original.to_dict()
        deserialized = ContextSnapshot.from_dict(serialized)

        # Verify all fields match
        assert deserialized.topology == original.topology
        assert deserialized.channel == original.channel
        assert deserialized.behavior == original.behavior
        assert len(deserialized.messages) == len(original.messages)
        assert deserialized.messages[0].content == original.messages[0].content
        assert deserialized.profile is not None
        assert deserialized.profile.display_name == original.profile.display_name
        assert deserialized.memory is not None
        assert deserialized.memory.recent_topics == original.memory.recent_topics
        assert deserialized.skills is not None
        assert deserialized.skills.current_level == original.skills.current_level
        assert len(deserialized.documents) == len(original.documents)
        assert deserialized.input_text == original.input_text
        assert deserialized.exercise_id == original.exercise_id
        assert deserialized.assessment_state["score"] == original.assessment_state["score"]


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Test creating a Message."""
        msg = Message(role="user", content="Hello", timestamp=datetime.utcnow())

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """Test Message with metadata."""
        msg = Message(
            role="assistant",
            content="Here is your answer.",
            metadata={"confidence": 0.95, "tokens": 150},
        )

        assert msg.metadata["confidence"] == 0.95
        assert msg.metadata["tokens"] == 150


class TestRoutingDecision:
    """Test RoutingDecision dataclass."""

    def test_routing_decision_creation(self):
        """Test creating a RoutingDecision."""
        decision = RoutingDecision(
            agent_id="agent.conversational.v1",
            pipeline_name="chat_fast",
            topology="fast_kernel",
            channel="text_channel",
            reason="User message detected",
        )

        assert decision.agent_id == "agent.conversational.v1"
        assert decision.pipeline_name == "chat_fast"
        assert decision.topology == "fast_kernel"
        assert decision.channel == "text_channel"
        assert decision.reason == "User message detected"


# Required for frozen dataclass test
