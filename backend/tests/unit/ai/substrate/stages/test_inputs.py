"""Tests for StageInputs and StagePorts immutable data flow types.

These tests verify:
- StagePorts immutability and factory functions
- StageInputs immutability and access patterns
- Proper data flow from snapshots and prior outputs
"""
from __future__ import annotations

import asyncio
import dataclasses
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.ai.substrate.agent.context_snapshot import ContextSnapshot, Message
from app.ai.substrate.stages.base import StageOutput, StageStatus
from app.ai.substrate.stages.inputs import StageInputs, create_stage_inputs
from app.ai.substrate.stages.ports import (
    StagePorts,
    create_stage_ports,
    create_stage_ports_from_data_dict,
)


class TestStagePortsImmutability:
    """Tests for StagePorts immutability."""

    def test_stage_ports_is_frozen(self):
        """Verify StagePorts is frozen and cannot be modified."""
        ports = StagePorts(db=None)
        with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):  # frozen dataclass
            ports.db = "new_value"

    def test_stage_ports_factory_creates_frozen(self):
        """Verify factory creates frozen instances."""
        ports = create_stage_ports(db=None)
        with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):
            ports.db = "new_value"

    def test_stage_ports_default_values(self):
        """Verify default values are correct."""
        ports = StagePorts()
        assert ports.db is None
        assert ports.db_lock is None
        assert ports.call_logger_db is None
        assert ports.send_status is None
        assert ports.send_token is None
        assert ports.send_audio_chunk is None
        assert ports.llm_chunk_queue is None
        assert ports.chat_service is None
        assert ports.recording is None
        assert ports.audio_data is None
        assert ports.audio_format is None

    def test_stage_ports_with_all_values(self):
        """Verify StagePorts can be created with all values."""
        async def dummy_status(stage, state, data):
            pass

        async def dummy_token(token):
            pass

        async def dummy_chunk(chunk, fmt, size, final):
            pass

        lock = asyncio.Lock()
        ports = StagePorts(
            db="mock_db",
            db_lock=lock,
            call_logger_db="mock_logger_db",
            send_status=dummy_status,
            send_token=dummy_token,
            send_audio_chunk=dummy_chunk,
            llm_chunk_queue="mock_queue",
            chat_service="mock_chat_service",
            recording={"session_id": "test"},
            audio_data=b"audio_bytes",
            audio_format="mp3",
        )

        assert ports.db == "mock_db"
        assert ports.db_lock is lock
        assert ports.send_status is dummy_status
        assert ports.send_token is dummy_token
        assert ports.audio_data == b"audio_bytes"

    def test_create_stage_ports_helper(self):
        """Verify factory helper creates correct ports."""
        lock = asyncio.Lock()
        ports = create_stage_ports(
            db="db_session",
            db_lock=lock,
            audio_data=b"test_audio",
        )

        assert ports.db == "db_session"
        assert ports.db_lock is lock
        assert ports.audio_data == b"test_audio"

    def test_create_stage_ports_from_data_dict(self):
        """Verify migration helper extracts data from legacy dict."""
        legacy_data = {
            "db": "old_db",
            "send_status": "old_status_cb",
            "send_token": "old_token_cb",
            "audio_data": b"old_audio",
        }

        ports = create_stage_ports_from_data_dict(legacy_data)

        assert ports.db == "old_db"
        assert ports.send_status == "old_status_cb"
        assert ports.send_token == "old_token_cb"
        assert ports.audio_data == b"old_audio"
        # Fields not in dict should be None
        assert ports.db_lock is None
        assert ports.chat_service is None


class TestStageInputsImmutability:
    """Tests for StageInputs immutability."""

    def _create_minimal_snapshot(self) -> ContextSnapshot:
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

    def test_stage_inputs_is_frozen(self):
        """Verify StageInputs is frozen and cannot be modified."""
        snapshot = self._create_minimal_snapshot()
        inputs = StageInputs(snapshot=snapshot)

        with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):  # frozen dataclass
            inputs.snapshot = "new_snapshot"

    def test_stage_inputs_factory_creates_frozen(self):
        """Verify factory creates frozen instances."""
        snapshot = self._create_minimal_snapshot()
        inputs = create_stage_inputs(snapshot=snapshot)

        with pytest.raises((TypeError, dataclasses.FrozenInstanceError)):
            inputs.snapshot = "new_snapshot"

    def test_stage_inputs_default_values(self):
        """Verify default values are correct."""
        snapshot = self._create_minimal_snapshot()
        inputs = StageInputs(snapshot=snapshot)

        assert inputs.snapshot is snapshot
        assert inputs.prior_outputs == {}
        assert isinstance(inputs.ports, StagePorts)
        assert inputs.ports.db is None

    def test_stage_inputs_with_prior_outputs(self):
        """Verify StageInputs can store prior outputs."""
        snapshot = self._create_minimal_snapshot()

        stt_output = StageOutput(
            status=StageStatus.OK,
            data={"transcript": "hello world", "confidence": 0.95},
        )
        llm_output = StageOutput(
            status=StageStatus.OK,
            data={"response": "hi there"},
        )

        prior_outputs = {
            "stt_stage": stt_output,
            "llm_stage": llm_output,
        }

        inputs = StageInputs(
            snapshot=snapshot,
            prior_outputs=prior_outputs,
        )

        assert len(inputs.prior_outputs) == 2
        assert inputs.prior_outputs["stt_stage"] is stt_output
        assert inputs.prior_outputs["llm_stage"] is llm_output


class TestStageInputsGetMethods:
    """Tests for StageInputs get() and get_from() methods."""

    def _create_minimal_snapshot(self) -> ContextSnapshot:
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

    def test_get_from_specific_stage(self):
        """Verify get_from() returns value from specific stage."""
        snapshot = self._create_minimal_snapshot()

        stt_output = StageOutput(
            status=StageStatus.OK,
            data={"transcript": "hello world", "confidence": 0.95},
        )
        llm_output = StageOutput(
            status=StageStatus.OK,
            data={"response": "hi there"},
        )

        prior_outputs = {
            "stt_stage": stt_output,
            "llm_stage": llm_output,
        }

        inputs = StageInputs(
            snapshot=snapshot,
            prior_outputs=prior_outputs,
        )

        transcript = inputs.get_from("stt_stage", "transcript")
        assert transcript == "hello world"

        response = inputs.get_from("llm_stage", "response")
        assert response == "hi there"

    def test_get_from_missing_stage(self):
        """Verify get_from() returns default for missing stage."""
        snapshot = self._create_minimal_snapshot()
        inputs = StageInputs(snapshot=snapshot)

        result = inputs.get_from("nonexistent_stage", "key")
        assert result is None

        result = inputs.get_from("nonexistent_stage", "key", default="default")
        assert result == "default"

    def test_get_from_missing_key(self):
        """Verify get_from() returns default for missing key."""
        snapshot = self._create_minimal_snapshot()

        stt_output = StageOutput(
            status=StageStatus.OK,
            data={"transcript": "hello world"},
        )

        inputs = StageInputs(
            snapshot=snapshot,
            prior_outputs={"stt_stage": stt_output},
        )

        result = inputs.get_from("stt_stage", "nonexistent_key")
        assert result is None

        result = inputs.get_from("stt_stage", "nonexistent_key", default="default")
        assert result == "default"

    def test_get_searches_all_outputs(self):
        """Verify get() searches through all prior outputs."""
        snapshot = self._create_minimal_snapshot()

        stt_output = StageOutput(
            status=StageStatus.OK,
            data={"transcript": "hello world"},
        )
        # Note: "transcript" appears in second stage too
        llm_output = StageOutput(
            status=StageStatus.OK,
            data={"transcript": "should not find this", "response": "hi"},
        )

        prior_outputs = {
            "stt_stage": stt_output,
            "llm_stage": llm_output,
        }

        inputs = StageInputs(
            snapshot=snapshot,
            prior_outputs=prior_outputs,
        )

        # Should find from first stage (stt_stage)
        result = inputs.get("transcript")
        assert result == "hello world"

        # Should find response from second stage
        result = inputs.get("response")
        assert result == "hi"

    def test_get_returns_default(self):
        """Verify get() returns default when key not found."""
        snapshot = self._create_minimal_snapshot()
        inputs = StageInputs(snapshot=snapshot)

        result = inputs.get("nonexistent_key")
        assert result is None

        result = inputs.get("nonexistent_key", default="default_value")
        assert result == "default_value"

    def test_has_output(self):
        """Verify has_output() correctly checks for stage output."""
        snapshot = self._create_minimal_snapshot()

        stt_output = StageOutput(status=StageStatus.OK, data={})
        prior_outputs = {"stt_stage": stt_output}

        inputs = StageInputs(snapshot=snapshot, prior_outputs=prior_outputs)

        assert inputs.has_output("stt_stage") is True
        assert inputs.has_output("llm_stage") is False
        assert inputs.has_output("nonexistent") is False

    def test_get_output(self):
        """Verify get_output() returns complete StageOutput."""
        snapshot = self._create_minimal_snapshot()

        stt_output = StageOutput(
            status=StageStatus.OK,
            data={"transcript": "hello"},
        )
        prior_outputs = {"stt_stage": stt_output}

        inputs = StageInputs(snapshot=snapshot, prior_outputs=prior_outputs)

        result = inputs.get_output("stt_stage")
        assert result is stt_output

        result = inputs.get_output("nonexistent")
        assert result is None


class TestSnapshotAccess:
    """Tests for accessing data from ContextSnapshot."""

    def _create_snapshot_with_data(self) -> ContextSnapshot:
        """Helper to create a ContextSnapshot with test data."""
        messages = [
            Message(role="user", content="hello", timestamp=datetime.utcnow()),
            Message(role="assistant", content="hi there", timestamp=datetime.utcnow()),
        ]
        return ContextSnapshot(
            pipeline_run_id=UUID("12345678-1234-5678-1234-567812345678"),
            request_id=UUID("22345678-1234-5678-1234-567812345678"),
            session_id=UUID("32345678-1234-5678-1234-567812345678"),
            user_id=UUID("42345678-1234-5678-1234-567812345678"),
            org_id=UUID("52345678-1234-5678-1234-567812345678"),
            interaction_id=UUID("62345678-1234-5678-1234-567812345678"),
            topology="voice_topology",
            channel="voice_channel",
            behavior="interview",
            messages=messages,
            input_text="test input",
        )

    def test_snapshot_available_in_inputs(self):
        """Verify original snapshot is accessible from StageInputs."""
        snapshot = self._create_snapshot_with_data()
        inputs = StageInputs(snapshot=snapshot)

        assert inputs.snapshot is snapshot

    def test_snapshot_identity_fields(self):
        """Verify snapshot identity fields are accessible."""
        snapshot = self._create_snapshot_with_data()
        inputs = StageInputs(snapshot=snapshot)

        assert inputs.snapshot.user_id == UUID("42345678-1234-5678-1234-567812345678")
        assert inputs.snapshot.session_id == UUID("32345678-1234-5678-1234-567812345678")
        assert inputs.snapshot.topology == "voice_topology"
        assert inputs.snapshot.channel == "voice_channel"

    def test_snapshot_messages_accessible(self):
        """Verify message history is accessible."""
        snapshot = self._create_snapshot_with_data()
        inputs = StageInputs(snapshot=snapshot)

        assert len(inputs.snapshot.messages) == 2
        assert inputs.snapshot.messages[0].role == "user"
        assert inputs.snapshot.messages[0].content == "hello"

    def test_snapshot_input_text_accessible(self):
        """Verify input_text is accessible."""
        snapshot = self._create_snapshot_with_data()
        inputs = StageInputs(snapshot=snapshot)

        assert inputs.snapshot.input_text == "test input"


class TestCreateStageInputsFactory:
    """Tests for create_stage_inputs factory function."""

    def _create_minimal_snapshot(self) -> ContextSnapshot:
        """Helper to create a minimal ContextSnapshot for testing."""
        return ContextSnapshot(
            pipeline_run_id=uuid4(),
            request_id=uuid4(),
            session_id=uuid4(),
            user_id=uuid4(),
            org_id=uuid4(),
            interaction_id=uuid4(),
            topology="test",
            channel="test",
            behavior="test",
            messages=[],
        )

    def test_factory_with_prior_outputs(self):
        """Verify factory correctly passes prior_outputs."""
        snapshot = self._create_minimal_snapshot()
        output = StageOutput(status=StageStatus.OK, data={"key": "value"})

        inputs = create_stage_inputs(
            snapshot=snapshot,
            prior_outputs={"stage1": output},
        )

        assert inputs.prior_outputs["stage1"] is output

    def test_factory_with_ports(self):
        """Verify factory correctly passes ports."""
        snapshot = self._create_minimal_snapshot()
        ports = StagePorts(db="test_db")

        inputs = create_stage_inputs(
            snapshot=snapshot,
            ports=ports,
        )

        assert inputs.ports.db == "test_db"

    def test_factory_defaults(self):
        """Verify factory uses correct defaults."""
        snapshot = self._create_minimal_snapshot()

        inputs = create_stage_inputs(snapshot=snapshot)

        assert inputs.prior_outputs == {}
        assert isinstance(inputs.ports, StagePorts)
        assert inputs.ports.db is None
