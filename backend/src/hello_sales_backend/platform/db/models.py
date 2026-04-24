"""Operational persistence models."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hello_sales_backend.platform.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TaskRunRecord(Base):
    """Persist background task execution state."""

    __tablename__ = "task_run_records"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def set_error_details(self, payload: dict[str, object] | None) -> None:
        """Persist structured error details as JSON text."""

        self.error_details = json.dumps(payload, sort_keys=True) if payload else None


class AgentRunRecord(Base):
    """Persist generic-agent run state."""

    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permissions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prompt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_owner_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prompt_owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_purpose: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latest_turn_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def set_error_details(self, payload: dict[str, object] | None) -> None:
        self.error_details = json.dumps(payload, sort_keys=True) if payload else None


class AgentTurnRecord(Base):
    """Persist one agent turn."""

    __tablename__ = "agent_turns"

    turn_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_owner_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prompt_owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_purpose: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def set_error_details(self, payload: dict[str, object] | None) -> None:
        self.error_details = json.dumps(payload, sort_keys=True) if payload else None


class AgentToolCallRecord(Base):
    """Persist one agent tool call."""

    __tablename__ = "agent_tool_calls"

    tool_call_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    turn_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def set_arguments(self, payload: dict[str, object]) -> None:
        self.arguments_json = json.dumps(payload, sort_keys=True)

    def set_result_payload(self, payload: dict[str, object] | None) -> None:
        self.result_payload_json = json.dumps(payload, sort_keys=True) if payload else None

    def set_error_details(self, payload: dict[str, object] | None) -> None:
        self.error_details = json.dumps(payload, sort_keys=True) if payload else None


class AgentArtifactRecord(Base):
    """Persist one structured agent artifact."""

    __tablename__ = "agent_artifacts"

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    turn_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    def set_payload(self, payload: dict[str, object]) -> None:
        self.payload_json = json.dumps(payload, sort_keys=True)


class AgentStreamEventRecord(Base):
    """Persist ordered generic-agent stream events."""

    __tablename__ = "agent_stream_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    turn_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    def set_payload(self, payload: dict[str, object]) -> None:
        self.payload_json = json.dumps(payload, sort_keys=True)


class SessionRecord(Base):
    """Persist durable session state."""

    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_summarized_item_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessionItemRecord(Base):
    """Persist append-only session chronology."""

    __tablename__ = "session_items"

    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    turn_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prompt_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_owner_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prompt_owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_purpose: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)

    def set_payload(self, payload: dict[str, object]) -> None:
        self.payload_json = json.dumps(payload, sort_keys=True)


class SessionSummaryRecord(Base):
    """Persist the latest materialized session summary."""

    __tablename__ = "session_summaries"

    summary_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    coverage_start_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_end_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_id: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_owner_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_purpose: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanyProfileRecord(Base):
    """Persist the current company profile."""

    __tablename__ = "company_profiles"

    profile_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_customer: Mapped[str | None] = mapped_column(Text, nullable=True)
    pricing_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_team_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crm_tool: Mapped[str | None] = mapped_column(Text, nullable=True)
    average_deal_size: Mapped[str | None] = mapped_column(Text, nullable=True)
    average_sales_cycle: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_sales_constraint: Mapped[str | None] = mapped_column(Text, nullable=True)
    quarterly_sales_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class ProductRecord(Base):
    """Persist one product belonging to the company profile."""

    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("company_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    product_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_customer: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_use_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    pricing_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    list_price: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_cycle: Mapped[str | None] = mapped_column(Text, nullable=True)
    deal_size: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_share: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
