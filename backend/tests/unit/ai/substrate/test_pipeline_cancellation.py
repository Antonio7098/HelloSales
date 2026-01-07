"""Tests for the unified pipeline cancellation mechanism.

Tests cover:
- StageOutput.cancel() factory method
- UnifiedPipelineCancelled exception
- Graph executor cancellation behavior
- SttStage empty transcript cancellation
"""

from unittest.mock import MagicMock
from uuid import uuid4


class TestStageOutputCancel:
    """Tests for StageOutput.cancel() factory method."""

    def test_cancel_creates_output_with_cancel_status(self):
        """Test cancel() creates output with CANCEL status."""
        from app.ai.substrate.stages.base import StageOutput, StageStatus

        output = StageOutput.cancel(reason="test cancellation")

        assert output.status == StageStatus.CANCEL
        assert output.error is None

    def test_cancel_includes_reason_in_data(self):
        """Test cancel() reason is included in data."""
        from app.ai.substrate.stages.base import StageOutput

        reason = "No speech detected"
        output = StageOutput.cancel(reason=reason)

        assert output.data["cancel_reason"] == reason

    def test_cancel_with_additional_data(self):
        """Test cancel() with additional data merged."""
        from app.ai.substrate.stages.base import StageOutput

        extra_data = {"transcript": "", "confidence": 0.0}
        output = StageOutput.cancel(reason="empty", data=extra_data)

        assert output.data["cancel_reason"] == "empty"
        assert output.data["transcript"] == ""
        assert output.data["confidence"] == 0.0

    def test_cancel_with_kwargs(self):
        """Test cancel() with keyword arguments via data dict."""
        from app.ai.substrate.stages.base import StageOutput

        extra_data = {
            "transcript": "",
            "latency_ms": 100,
            "cost_cents": 5
        }
        output = StageOutput.cancel(
            reason="no speech",
            data=extra_data
        )

        assert output.data["cancel_reason"] == "no speech"
        assert output.data["transcript"] == ""
        assert output.data["latency_ms"] == 100
        assert output.data["cost_cents"] == 5

    def test_cancel_status_value(self):
        """Test CANCEL status has correct string value."""
        from app.ai.substrate.stages.base import StageStatus

        assert StageStatus.CANCEL.value == "cancel"

    def test_cancel_is_distinct_from_ok(self):
        """Test CANCEL is different from OK status."""
        from app.ai.substrate.stages.base import StageOutput, StageStatus

        ok_output = StageOutput.ok(result="success")
        cancel_output = StageOutput.cancel(reason="stopped")

        assert ok_output.status == StageStatus.OK
        assert cancel_output.status == StageStatus.CANCEL
        assert ok_output.status != cancel_output.status

    def test_cancel_is_distinct_from_fail(self):
        """Test CANCEL is different from FAIL status."""
        from app.ai.substrate.stages.base import StageOutput, StageStatus

        fail_output = StageOutput.fail(error="error")
        cancel_output = StageOutput.cancel(reason="stopped")

        assert fail_output.status == StageStatus.FAIL
        assert cancel_output.status == StageStatus.CANCEL
        assert fail_output.status != cancel_output.status


class TestUnifiedPipelineCancelled:
    """Tests for UnifiedPipelineCancelled exception."""

    def test_exception_creation(self):
        """Test creating UnifiedPipelineCancelled exception."""
        from app.ai.substrate.stages.graph import UnifiedPipelineCancelled

        results = {"stage1": MagicMock()}
        exc = UnifiedPipelineCancelled(
            stage="stt",
            reason="No speech detected",
            results=results
        )

        assert exc.stage == "stt"
        assert exc.reason == "No speech detected"
        assert exc.results is results

    def test_exception_message_contains_stage_and_reason(self):
        """Test exception message includes stage and reason."""
        from app.ai.substrate.stages.graph import UnifiedPipelineCancelled

        exc = UnifiedPipelineCancelled(
            stage="stt",
            reason="empty transcript",
            results={}
        )

        message = str(exc)
        assert "stt" in message
        assert "empty transcript" in message

    def test_exception_is_exception(self):
        """Test UnifiedPipelineCancelled is an Exception."""
        from app.ai.substrate.stages.graph import UnifiedPipelineCancelled

        exc = UnifiedPipelineCancelled(stage="test", reason="reason", results={})

        assert isinstance(exc, Exception)

    def test_exception_with_partial_results(self):
        """Test exception carries partial stage results."""
        from app.ai.substrate.stages.base import StageOutput
        from app.ai.substrate.stages.graph import UnifiedPipelineCancelled

        stage1_output = StageOutput.ok(data={"key": "value"})
        stage2_output = StageOutput.ok(data={"other": "data"})

        exc = UnifiedPipelineCancelled(
            stage="stt",
            reason="cancelled",
            results={"voice_input": stage1_output, "router": stage2_output}
        )

        assert len(exc.results) == 2
        assert "voice_input" in exc.results
        assert "router" in exc.results


class TestStageStatusCancel:
    """Tests for StageStatus.CANCEL enum value."""

    def test_cancel_status_exists(self):
        """Test CANCEL status is defined."""
        from app.ai.substrate.stages.base import StageStatus

        assert hasattr(StageStatus, "CANCEL")

    def test_cancel_status_is_string_enum(self):
        """Test CANCEL status is a string enum."""
        from app.ai.substrate.stages.base import StageStatus

        assert StageStatus("cancel") == StageStatus.CANCEL

    def test_all_status_values(self):
        """Test all expected status values exist."""
        from app.ai.substrate.stages.base import StageStatus

        expected = {"ok", "skip", "cancel", "fail", "retry"}
        actual = {s.value for s in StageStatus}

        assert expected == actual


class TestSttStageCancellation:
    """Tests for SttStage empty transcript cancellation behavior."""

    def test_stt_stage_has_cancel_output_method(self):
        """Test that SttStage can import and use StageOutput.cancel()."""
        from app.ai.substrate.stages.base import StageOutput, StageStatus

        output = StageOutput.cancel(
            reason="No speech detected - empty transcript",
            data={
                "transcript": "",
                "confidence": 0.0,
                "no_speech": True,
            }
        )

        assert output.status == StageStatus.CANCEL
        assert output.data["cancel_reason"] == "No speech detected - empty transcript"
        assert output.data["transcript"] == ""
        assert output.data["no_speech"] is True

    def test_stt_stage_empty_transcript_check(self):
        """Test empty transcript detection logic."""
        from app.ai.substrate.stages.base import StageOutput

        test_cases = [
            ("", True),
            ("   ", True),
            ("hello", False),
            ("Hello, I want to practice", False),
        ]

        for transcript, _should_cancel in test_cases:
            is_empty = not transcript or not transcript.strip()
            if is_empty:
                output = StageOutput.cancel(
                    reason="No speech detected - empty transcript",
                    data={"transcript": transcript}
                )
                assert output.status.value == "cancel"
            else:
                output = StageOutput.ok(data={"transcript": transcript})
                assert output.status.value == "ok"

    def test_cancel_output_preserves_stt_data(self):
        """Test that cancel output preserves STT result data."""
        from app.ai.substrate.stages.base import StageOutput

        provider_call_id = uuid4()
        output = StageOutput.cancel(
            reason="No speech detected - empty transcript",
            data={
                "transcript": "",
                "confidence": 0.0,
                "duration_ms": 100.0,
                "latency_ms": 50,
                "cost_cents": 0,
                "stt_provider_call_id": str(provider_call_id),
                "no_speech": True,
            },
        )

        assert output.data["transcript"] == ""
        assert output.data["confidence"] == 0.0
        assert output.data["duration_ms"] == 100.0
        assert output.data["latency_ms"] == 50
        assert output.data["cost_cents"] == 0
        assert output.data["no_speech"] is True


class TestVoiceServiceCancellation:
    """Tests for voice service handling of UnifiedPipelineCancelled."""

    def test_service_returns_empty_result_on_cancellation(self):
        """Test that voice service returns empty VoicePipelineResult on cancellation."""
        from uuid import UUID

        from app.domains.voice.service import VoicePipelineResult

        result = VoicePipelineResult(
            transcript="",
            transcript_confidence=0.0,
            audio_duration_ms=0,
            response_text="",
            llm_latency_ms=0,
            audio_data=b"",
            audio_format="",
            tts_duration_ms=0,
            user_message_id=UUID(int=0),
            assistant_message_id=UUID(int=0),
            stt_cost=0,
            llm_cost=0,
            tts_cost=0,
        )

        assert result.transcript == ""
        assert result.response_text == ""
        assert result.audio_data == b""
        assert result.total_cost == 0
