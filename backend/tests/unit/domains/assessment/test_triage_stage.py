"""Tests for the new TriageStage that uses TriageService for LLM-based classification."""
import uuid
from unittest.mock import AsyncMock

import pytest

from app.ai.substrate.stages.context import PipelineContext
from app.ai.substrate.stages.chat.triage import TriageStage


class TestTriageStage:
    """Test the TriageStage implementation."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def triage_stage(self, mock_db):
        """Create a TriageStage instance."""
        return TriageStage(db=mock_db)

    @pytest.fixture
    def pipeline_context(self):
        """Create a PipelineContext for testing."""
        return PipelineContext(
            pipeline_run_id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            interaction_id=uuid.uuid4(),
            topology="voice_fast",
            configuration={"stages": []},
            behavior="practice",
            mode="practice",
            quality_mode="fast",
            service="voice"
        )

    @pytest.mark.asyncio
    async def test_triage_stage_basic_functionality(self, triage_stage, pipeline_context):
        """Test basic TriageStage functionality."""
        # Add empty transcript to trigger predictable behavior
        pipeline_context.data["transcript"] = ""
        pipeline_context.data["context"] = None
        pipeline_context.data["send_status"] = AsyncMock()

        # Run triage stage
        result = await triage_stage.run(pipeline_context)

        # Verify result structure
        assert result.name == "triage"
        assert result.status == "completed"
        assert "skip_assessment" in result.data
        assert "triage_decision" in result.data

        # Empty transcript should skip assessment
        assert result.data["skip_assessment"] is True
        assert result.data["triage_decision"] == "skip_assessment"
        assert result.data["reason"] == "empty_transcript"

    @pytest.mark.asyncio
    async def test_triage_stage_with_transcript(self, triage_stage, pipeline_context):
        """Test TriageStage with actual transcript (uses real LLM)."""
        # Add transcript data
        pipeline_context.data["transcript"] = "Hello, I want to practice my presentation skills"
        pipeline_context.data["context"] = None
        pipeline_context.data["send_status"] = AsyncMock()

        # Run triage stage
        result = await triage_stage.run(pipeline_context)

        # Verify result structure
        assert result.name == "triage"
        assert result.status == "completed"
        assert "skip_assessment" in result.data
        assert "triage_decision" in result.data

        # Should have triage response data
        assert "triage_response" in result.data
        triage_response = result.data["triage_response"]
        assert "decision" in triage_response
        assert "reason" in triage_response
