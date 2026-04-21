"""Align runtime schema with durable session store models.

Revision ID: 0003_runtime_session_schema
Revises: 0002_create_agent_run_tables
Create Date: 2026-04-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_runtime_session_schema"
down_revision = "0002_create_agent_run_tables"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return bool(inspector.has_table(table_name))


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def _create_agent_runs_table() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("profile_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_id", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("prompt_owner_kind", sa.String(length=32), nullable=True),
        sa.Column("prompt_owner_id", sa.String(length=128), nullable=True),
        sa.Column("prompt_purpose", sa.String(length=128), nullable=True),
        sa.Column("prompt_checksum", sa.String(length=255), nullable=True),
        sa.Column("latest_turn_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])


def _create_task_run_records_table() -> None:
    op.create_table(
        "task_run_records",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("purpose", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )


def _create_agent_turns_table() -> None:
    op.create_table(
        "agent_turns",
        sa.Column("turn_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prompt_id", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("prompt_owner_kind", sa.String(length=32), nullable=True),
        sa.Column("prompt_owner_id", sa.String(length=128), nullable=True),
        sa.Column("prompt_purpose", sa.String(length=128), nullable=True),
        sa.Column("prompt_checksum", sa.String(length=255), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_turns_run_id", "agent_turns", ["run_id"])


def _create_agent_tool_calls_table() -> None:
    op.create_table(
        "agent_tool_calls",
        sa.Column("tool_call_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("turn_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("arguments_json", sa.Text(), nullable=False),
        sa.Column("result_payload_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_tool_calls_run_id", "agent_tool_calls", ["run_id"])
    op.create_index("ix_agent_tool_calls_turn_id", "agent_tool_calls", ["turn_id"])
    op.create_index("ix_agent_tool_calls_approval_id", "agent_tool_calls", ["approval_id"])


def _create_agent_artifacts_table() -> None:
    op.create_table(
        "agent_artifacts",
        sa.Column("artifact_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("turn_id", sa.String(length=64), nullable=True),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_artifacts_run_id", "agent_artifacts", ["run_id"])
    op.create_index("ix_agent_artifacts_turn_id", "agent_artifacts", ["turn_id"])


def _create_agent_stream_events_table() -> None:
    op.create_table(
        "agent_stream_events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("turn_id", sa.String(length=64), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_stream_events_run_id", "agent_stream_events", ["run_id"])
    op.create_index("ix_agent_stream_events_turn_id", "agent_stream_events", ["turn_id"])


def _create_sessions_table() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("profile_name", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("latest_item_id", sa.String(length=64), nullable=True),
        sa.Column("latest_run_id", sa.String(length=64), nullable=True),
        sa.Column("summary_task_id", sa.String(length=64), nullable=True),
        sa.Column("summary_status", sa.String(length=32), nullable=True),
        sa.Column("last_summarized_item_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def _create_session_items_table() -> None:
    op.create_table(
        "session_items",
        sa.Column("item_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("turn_id", sa.String(length=64), nullable=True),
        sa.Column("tool_call_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_id", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("prompt_owner_kind", sa.String(length=32), nullable=True),
        sa.Column("prompt_owner_id", sa.String(length=128), nullable=True),
        sa.Column("prompt_purpose", sa.String(length=128), nullable=True),
        sa.Column("prompt_checksum", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_session_items_session_id", "session_items", ["session_id"])
    op.create_index("ix_session_items_run_id", "session_items", ["run_id"])
    op.create_index("ix_session_items_turn_id", "session_items", ["turn_id"])
    op.create_index("ix_session_items_tool_call_id", "session_items", ["tool_call_id"])


def _create_session_summaries_table() -> None:
    op.create_table(
        "session_summaries",
        sa.Column("summary_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("coverage_start_sequence", sa.Integer(), nullable=False),
        sa.Column("coverage_end_sequence", sa.Integer(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("provider_name", sa.String(length=128), nullable=True),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("prompt_id", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_owner_kind", sa.String(length=32), nullable=False),
        sa.Column("prompt_owner_id", sa.String(length=128), nullable=False),
        sa.Column("prompt_purpose", sa.String(length=128), nullable=False),
        sa.Column("prompt_checksum", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_category", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("session_id", name="uq_session_summaries_session_id"),
    )
    op.create_index("ix_session_summaries_session_id", "session_summaries", ["session_id"], unique=True)


def upgrade() -> None:
    if not _has_table("task_run_records"):
        _create_task_run_records_table()

    if not _has_table("agent_runs"):
        _create_agent_runs_table()
    else:
        columns = _column_names("agent_runs")
        if "session_id" not in columns:
            op.add_column("agent_runs", sa.Column("session_id", sa.String(length=64), nullable=True))
        if "prompt_id" not in columns:
            op.add_column("agent_runs", sa.Column("prompt_id", sa.String(length=255), nullable=True))
        if "prompt_version" not in columns:
            op.add_column("agent_runs", sa.Column("prompt_version", sa.String(length=64), nullable=True))
        if "prompt_owner_kind" not in columns:
            op.add_column("agent_runs", sa.Column("prompt_owner_kind", sa.String(length=32), nullable=True))
        if "prompt_owner_id" not in columns:
            op.add_column("agent_runs", sa.Column("prompt_owner_id", sa.String(length=128), nullable=True))
        if "prompt_purpose" not in columns:
            op.add_column("agent_runs", sa.Column("prompt_purpose", sa.String(length=128), nullable=True))
        if "prompt_checksum" not in columns:
            op.add_column("agent_runs", sa.Column("prompt_checksum", sa.String(length=255), nullable=True))
        op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"], if_not_exists=True)

    if not _has_table("agent_turns"):
        _create_agent_turns_table()
    else:
        columns = _column_names("agent_turns")
        if "prompt_id" not in columns:
            op.add_column("agent_turns", sa.Column("prompt_id", sa.String(length=255), nullable=True))
        if "prompt_version" not in columns:
            op.add_column("agent_turns", sa.Column("prompt_version", sa.String(length=64), nullable=True))
        if "prompt_owner_kind" not in columns:
            op.add_column("agent_turns", sa.Column("prompt_owner_kind", sa.String(length=32), nullable=True))
        if "prompt_owner_id" not in columns:
            op.add_column("agent_turns", sa.Column("prompt_owner_id", sa.String(length=128), nullable=True))
        if "prompt_purpose" not in columns:
            op.add_column("agent_turns", sa.Column("prompt_purpose", sa.String(length=128), nullable=True))
        if "prompt_checksum" not in columns:
            op.add_column("agent_turns", sa.Column("prompt_checksum", sa.String(length=255), nullable=True))

    if not _has_table("agent_tool_calls"):
        _create_agent_tool_calls_table()

    if not _has_table("agent_artifacts"):
        _create_agent_artifacts_table()

    if not _has_table("agent_stream_events"):
        _create_agent_stream_events_table()
    else:
        columns = _column_names("agent_stream_events")
        if "request_id" not in columns:
            op.add_column("agent_stream_events", sa.Column("request_id", sa.String(length=64), nullable=True))
        if "trace_id" not in columns:
            op.add_column("agent_stream_events", sa.Column("trace_id", sa.String(length=64), nullable=True))
        if "actor_id" not in columns:
            op.add_column("agent_stream_events", sa.Column("actor_id", sa.String(length=64), nullable=True))

    if not _has_table("sessions"):
        _create_sessions_table()

    if not _has_table("session_items"):
        _create_session_items_table()

    if not _has_table("session_summaries"):
        _create_session_summaries_table()


def downgrade() -> None:
    if _has_table("task_run_records"):
        op.drop_table("task_run_records")

    if _has_table("session_summaries"):
        op.drop_index("ix_session_summaries_session_id", table_name="session_summaries", if_exists=True)
        op.drop_table("session_summaries")

    if _has_table("session_items"):
        op.drop_index("ix_session_items_tool_call_id", table_name="session_items", if_exists=True)
        op.drop_index("ix_session_items_turn_id", table_name="session_items", if_exists=True)
        op.drop_index("ix_session_items_run_id", table_name="session_items", if_exists=True)
        op.drop_index("ix_session_items_session_id", table_name="session_items", if_exists=True)
        op.drop_table("session_items")

    if _has_table("sessions"):
        op.drop_table("sessions")

    if _has_table("agent_stream_events"):
        columns = _column_names("agent_stream_events")
        if "actor_id" in columns:
            op.drop_column("agent_stream_events", "actor_id")
        if "trace_id" in columns:
            op.drop_column("agent_stream_events", "trace_id")
        if "request_id" in columns:
            op.drop_column("agent_stream_events", "request_id")

    if _has_table("agent_turns"):
        columns = _column_names("agent_turns")
        if "prompt_checksum" in columns:
            op.drop_column("agent_turns", "prompt_checksum")
        if "prompt_purpose" in columns:
            op.drop_column("agent_turns", "prompt_purpose")
        if "prompt_owner_id" in columns:
            op.drop_column("agent_turns", "prompt_owner_id")
        if "prompt_owner_kind" in columns:
            op.drop_column("agent_turns", "prompt_owner_kind")
        if "prompt_version" in columns:
            op.drop_column("agent_turns", "prompt_version")
        if "prompt_id" in columns:
            op.drop_column("agent_turns", "prompt_id")

    if _has_table("agent_runs"):
        op.drop_index("ix_agent_runs_session_id", table_name="agent_runs", if_exists=True)
        columns = _column_names("agent_runs")
        if "prompt_checksum" in columns:
            op.drop_column("agent_runs", "prompt_checksum")
        if "prompt_purpose" in columns:
            op.drop_column("agent_runs", "prompt_purpose")
        if "prompt_owner_id" in columns:
            op.drop_column("agent_runs", "prompt_owner_id")
        if "prompt_owner_kind" in columns:
            op.drop_column("agent_runs", "prompt_owner_kind")
        if "prompt_version" in columns:
            op.drop_column("agent_runs", "prompt_version")
        if "prompt_id" in columns:
            op.drop_column("agent_runs", "prompt_id")
        if "session_id" in columns:
            op.drop_column("agent_runs", "session_id")
