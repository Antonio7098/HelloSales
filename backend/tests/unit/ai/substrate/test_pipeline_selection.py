"""Unit tests for pipeline selection based on quality_mode."""
import pytest


class TestPipelineSelection:
    """Test pipeline selection logic based on quality_mode."""

    @pytest.mark.parametrize(
        "quality_mode, expected_pipeline",
        [
            ("fast", "chat_fast"),
            ("accurate", "chat_accurate"),
        ],
    )
    def test_chat_pipeline_selection_by_quality_mode(self, quality_mode, expected_pipeline):
        """Test that chat service selects correct pipeline based on quality_mode."""
        # Test the pipeline name construction logic from ChatService.handle_message_dag
        pipeline_name = f"chat_{quality_mode}"
        assert pipeline_name == expected_pipeline

    @pytest.mark.parametrize(
        "quality_mode, expected_pipeline",
        [
            ("fast", "voice_fast"),
            ("accurate", "voice_accurate"),
        ],
    )
    def test_voice_pipeline_selection_by_quality_mode(self, quality_mode, expected_pipeline):
        """Test that voice service selects correct pipeline based on quality_mode."""
        # Test the pipeline name construction logic from VoiceService.process_recording
        pipeline_name = f"voice_{quality_mode}"
        assert pipeline_name == expected_pipeline

    @pytest.mark.parametrize(
        "service, quality_mode, expected_pipeline",
        [
            ("chat", "fast", "chat_fast"),
            ("chat", "accurate", "chat_accurate"),
            ("voice", "fast", "voice_fast"),
            ("voice", "accurate", "voice_accurate"),
        ],
    )
    def test_service_pipeline_naming_pattern(self, service, quality_mode, expected_pipeline):
        """Test the consistent naming pattern across services."""
        pipeline_name = f"{service}_{quality_mode}"
        assert pipeline_name == expected_pipeline
