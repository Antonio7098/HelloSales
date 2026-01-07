"""StagePorts - Injected capabilities for stages (callbacks, services, db).

This module defines StagePorts, an immutable dataclass that provides typed access
to services and callbacks that stages need. This replaces the untyped mutable
dict access pattern (ctx.config["data"]["send_status"], etc.).

Example:
    ports = StagePorts(
        db=db_session,
        send_status=lambda status, state, data: asyncio.sleep(0),
        send_token=lambda token: asyncio.sleep(0),
        send_audio_chunk=lambda chunk, fmt, size, final: asyncio.sleep(0),
    )
"""
from __future__ import annotations

from asyncio import Lock
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class StagePorts:
    """Injected capabilities for stages (callbacks, services, db).

    This is an immutable (frozen) dataclass that provides typed access to
    capabilities that stages need. All fields are read-only after creation.

    Attributes:
        db: Database session for persistence operations.
        db_lock: Optional lock for preventing concurrent DB access.
        call_logger_db: Database session for provider call logging.
        send_status: Callback for sending status updates (stage, state, data).
        send_token: Callback for sending streamed LLM tokens.
        send_audio_chunk: Callback for sending TTS audio chunks.
        llm_chunk_queue: Queue for LLM chunks in streaming pipeline.
        partial_text_queue: Queue for partial text from LLM for incremental TTS.
        chat_service: Chat service for building context and running LLM.
        recording: Recording metadata (session_id, user_id, format, voice).
        audio_data: Raw audio bytes for STT processing.
        audio_format: Audio format info for STT provider.
    """

    db: AsyncSession | None = None
    db_lock: Lock | None = None
    call_logger_db: AsyncSession | None = None

    send_status: Callable[[str, str, dict[str, Any] | None], Awaitable[None]] | None = None
    send_token: Callable[[str], Awaitable[None]] | None = None
    send_audio_chunk: Callable[[bytes, str, int, bool], Awaitable[None]] | None = None
    send_transcript: Callable[[Any, str, float, int], Awaitable[None]] | None = None  # msg_id, transcript, confidence, duration_ms

    llm_chunk_queue: Any = None
    partial_text_queue: Any = None  # asyncio.Queue for streaming partial text to TTS
    chat_service: Any = None

    recording: Any = None
    audio_data: bytes | None = None
    audio_format: str | None = None


def create_stage_ports(
    *,
    db: AsyncSession | None = None,
    db_lock: Lock | None = None,
    call_logger_db: AsyncSession | None = None,
    send_status: Callable[[str, str, dict[str, Any] | None], Awaitable[None]] | None = None,
    send_token: Callable[[str], Awaitable[None]] | None = None,
    send_audio_chunk: Callable[[bytes, str, int, bool], Awaitable[None]] | None = None,
    send_transcript: Callable[[str, str, float, int], Awaitable[None]] | None = None,
    llm_chunk_queue: Any = None,
    partial_text_queue: Any = None,
    chat_service: Any = None,
    recording: Any = None,
    audio_data: bytes | None = None,
    audio_format: str | None = None,
) -> StagePorts:
    """Factory function to create StagePorts with all fields.

    This is the recommended way to create StagePorts instances.

    Args:
        db: Database session for persistence operations.
        db_lock: Optional lock for preventing concurrent DB access.
        call_logger_db: Database session for provider call logging.
        send_status: Callback for status updates.
        send_token: Callback for streaming tokens.
        send_audio_chunk: Callback for streaming audio chunks.
        send_transcript: Callback for sending STT transcript to client.
        llm_chunk_queue: Queue for LLM chunks in streaming pipeline.
        partial_text_queue: Queue for streaming partial text from LLM to TTS.
        chat_service: Chat service for building context and running LLM.
        recording: Recording metadata.
        audio_data: Raw audio bytes.
        audio_format: Audio format string.

    Returns:
        StagePorts instance with all fields set.
    """
    return StagePorts(
        db=db,
        db_lock=db_lock,
        call_logger_db=call_logger_db,
        send_status=send_status,
        send_token=send_token,
        send_audio_chunk=send_audio_chunk,
        send_transcript=send_transcript,
        llm_chunk_queue=llm_chunk_queue,
        partial_text_queue=partial_text_queue,
        chat_service=chat_service,
        recording=recording,
        audio_data=audio_data,
        audio_format=audio_format,
    )


def create_stage_ports_from_data_dict(data: dict[str, Any]) -> StagePorts:
    """Create StagePorts from the legacy data dict pattern.

    This is a migration helper that extracts values from the old mutable
    data dict and creates a proper StagePorts instance.

    Args:
        data: The legacy ctx.data dict containing all stage data.

    Returns:
        StagePorts instance populated from the data dict.
    """
    return StagePorts(
        db=data.get("db"),
        db_lock=data.get("db_lock"),
        call_logger_db=data.get("call_logger_db"),
        send_status=data.get("send_status"),
        send_token=data.get("send_token"),
        send_audio_chunk=data.get("send_audio_chunk"),
        send_transcript=data.get("send_transcript"),
        llm_chunk_queue=data.get("llm_chunk_queue"),
        chat_service=data.get("chat_service"),
        recording=data.get("recording"),
        audio_data=data.get("audio_data"),
        audio_format=data.get("audio_format"),
    )


__all__ = [
    "StagePorts",
    "create_stage_ports",
    "create_stage_ports_from_data_dict",
]
