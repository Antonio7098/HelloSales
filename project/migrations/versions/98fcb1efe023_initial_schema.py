"""Initial schema - all tables for HelloSales backend

Revision ID: 98fcb1efe023
Revises:
Create Date: 2026-01-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "98fcb1efe023"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Core Identity Tables ===

    # Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("auth_provider", sa.String(50), nullable=False, server_default="workos"),
        sa.Column("auth_subject", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("auth_provider", "auth_subject", name="users_auth_unique"),
    )

    # Organizations table
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=True),
        sa.Column("settings", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Organization memberships table
    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("permissions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "organization_id", name="org_membership_unique"),
    )

    # Company profiles table
    op.create_table(
        "company_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Company basics
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("company_size", sa.String(50), nullable=True),
        sa.Column("headquarters_city", sa.String(100), nullable=True),
        sa.Column("headquarters_country", sa.String(100), nullable=True),
        sa.Column("website", sa.Text, nullable=True),
        # Sales operations
        sa.Column("sales_team_size", sa.Integer, nullable=True),
        sa.Column("average_deal_size_usd", sa.Integer, nullable=True),
        sa.Column("sales_cycle_days", sa.Integer, nullable=True),
        sa.Column("target_market", sa.Text, nullable=True),
        sa.Column("market_segments", postgresql.JSONB, nullable=False, server_default="[]"),
        # Product/service context
        sa.Column("primary_products", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("sales_regions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("deal_types", postgresql.JSONB, nullable=False, server_default="[]"),
        # Sales maturity & process
        sa.Column("sales_methodology", sa.String(100), nullable=True),
        sa.Column("sales_stage", sa.String(50), nullable=True),
        sa.Column("typical_buying_cycle", postgresql.JSONB, nullable=False, server_default="{}"),
        # Competitive context
        sa.Column("main_competitors", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("competitive_advantages", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("unique_selling_points", postgresql.JSONB, nullable=False, server_default="[]"),
        # Additional context
        sa.Column("company_description", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_company_profiles_org_id", "company_profiles", ["org_id"])

    # === Session & Interaction Tables ===

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # State
        sa.Column("state", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        # Metrics
        sa.Column("interaction_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        # Metadata
        sa.Column("session_type", sa.String(50), nullable=False, server_default="chat"),
        sa.Column("session_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index("idx_sessions_org_id", "sessions", ["org_id"])
    op.create_index("idx_sessions_state", "sessions", ["state"])
    op.create_index("idx_sessions_created_at", "sessions", ["created_at"])

    # Interactions table
    op.create_table(
        "interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Identity
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("message_id", sa.String(100), nullable=True),
        # Content
        sa.Column("input_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        # Audio
        sa.Column("audio_url", sa.Text, nullable=True),
        sa.Column("audio_duration_ms", sa.Integer, nullable=True),
        # Provider call references
        sa.Column("llm_provider_call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stt_provider_call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tts_provider_call_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Ordering
        sa.Column("sequence_number", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_interactions_session_id", "interactions", ["session_id"])
    op.create_index(
        "idx_interactions_session_seq", "interactions", ["session_id", "sequence_number"]
    )
    op.create_index("idx_interactions_created_at", "interactions", ["created_at"])

    # Session summaries table
    op.create_table(
        "session_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("cutoff_sequence", sa.Integer, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("session_id", "version", name="session_summary_version_unique"),
    )
    op.create_index("idx_session_summaries_session_id", "session_summaries", ["session_id"])

    # Summary states table
    op.create_table(
        "summary_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("turns_since_summary", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_cutoff_sequence", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_summary_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # === HelloSales Content Tables ===

    # Products table
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("key_features", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("pricing_info", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("target_audience", sa.Text, nullable=True),
        sa.Column("competitive_advantages", sa.Text, nullable=True),
        sa.Column("use_cases", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_products_org_id", "products", ["org_id"])
    op.create_index("idx_products_active", "products", ["org_id", "is_active"])

    # Clients table
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("pain_points", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("goals", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("objection_patterns", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("communication_style", sa.Text, nullable=True),
        sa.Column("decision_criteria", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_clients_org_id", "clients", ["org_id"])
    op.create_index("idx_clients_active", "clients", ["org_id", "is_active"])

    # Sales scripts table
    op.create_table(
        "sales_scripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("script_type", sa.String(50), nullable=False, server_default="general"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("key_talking_points", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("objection_handlers", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("discovery_questions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("closing_techniques", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "generated_by_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generation_prompt", sa.Text, nullable=True),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "parent_script_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sales_scripts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_sales_scripts_org_id", "sales_scripts", ["org_id"])
    op.create_index("idx_sales_scripts_product_id", "sales_scripts", ["product_id"])
    op.create_index("idx_sales_scripts_client_id", "sales_scripts", ["client_id"])
    op.create_index("idx_sales_scripts_type", "sales_scripts", ["org_id", "script_type"])

    # Sales emails table
    op.create_table(
        "sales_emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("email_type", sa.String(50), nullable=False, server_default="general"),
        sa.Column("subject", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("call_to_action", sa.Text, nullable=True),
        sa.Column("personalization_fields", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "generated_by_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generation_prompt", sa.Text, nullable=True),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "parent_email_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sales_emails.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_sales_emails_org_id", "sales_emails", ["org_id"])
    op.create_index("idx_sales_emails_product_id", "sales_emails", ["product_id"])
    op.create_index("idx_sales_emails_client_id", "sales_emails", ["client_id"])
    op.create_index("idx_sales_emails_type", "sales_emails", ["org_id", "email_type"])

    # === Observability Tables ===

    # Provider calls table
    op.create_table(
        "provider_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "interaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("prompt_messages", postgresql.JSONB, nullable=True),
        sa.Column("prompt_text", sa.Text, nullable=True),
        sa.Column("output_content", sa.Text, nullable=True),
        sa.Column("output_parsed", postgresql.JSONB, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("tokens_in", sa.Integer, nullable=True),
        sa.Column("tokens_out", sa.Integer, nullable=True),
        sa.Column("audio_duration_ms", sa.Integer, nullable=True),
        sa.Column("cost_cents", sa.Integer, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_provider_calls_request_id", "provider_calls", ["request_id"])
    op.create_index("idx_provider_calls_pipeline_run_id", "provider_calls", ["pipeline_run_id"])
    op.create_index("idx_provider_calls_session_id", "provider_calls", ["session_id"])
    op.create_index("idx_provider_calls_user_id", "provider_calls", ["user_id"])
    op.create_index("idx_provider_calls_org_id", "provider_calls", ["org_id"])
    op.create_index("idx_provider_calls_provider", "provider_calls", ["provider", "model_id"])
    op.create_index("idx_provider_calls_created_at", "provider_calls", ["created_at"])

    # Pipeline runs table
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("topology", sa.String(50), nullable=True),
        sa.Column("behavior", sa.String(50), nullable=True),
        sa.Column("quality_mode", sa.String(20), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "interaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("interactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "stt_provider_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "llm_provider_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tts_provider_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("total_latency_ms", sa.Integer, nullable=True),
        sa.Column("ttft_ms", sa.Integer, nullable=True),
        sa.Column("ttfa_ms", sa.Integer, nullable=True),
        sa.Column("ttfc_ms", sa.Integer, nullable=True),
        sa.Column("tokens_in", sa.Integer, nullable=True),
        sa.Column("tokens_out", sa.Integer, nullable=True),
        sa.Column("tokens_per_second", sa.Float, nullable=True),
        sa.Column("input_audio_duration_ms", sa.Integer, nullable=True),
        sa.Column("output_audio_duration_ms", sa.Integer, nullable=True),
        sa.Column("total_cost_cents", sa.Integer, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("stages", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("run_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("context_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_pipeline_runs_request_id", "pipeline_runs", ["request_id"])
    op.create_index("idx_pipeline_runs_session_id", "pipeline_runs", ["session_id"])
    op.create_index("idx_pipeline_runs_user_id", "pipeline_runs", ["user_id"])
    op.create_index("idx_pipeline_runs_org_id", "pipeline_runs", ["org_id"])
    op.create_index("idx_pipeline_runs_service", "pipeline_runs", ["service"])
    op.create_index("idx_pipeline_runs_success", "pipeline_runs", ["success"])
    op.create_index("idx_pipeline_runs_created_at", "pipeline_runs", ["created_at"])

    # Pipeline events table
    op.create_table(
        "pipeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_pipeline_events_run_id", "pipeline_events", ["pipeline_run_id"])
    op.create_index("idx_pipeline_events_type", "pipeline_events", ["event_type"])
    op.create_index("idx_pipeline_events_occurred_at", "pipeline_events", ["occurred_at"])

    # Dead letter queue table
    op.create_table(
        "dead_letter_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error_type", sa.String(100), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("failed_stage", sa.String(100), nullable=True),
        sa.Column("stack_trace", sa.Text, nullable=True),
        sa.Column("context_snapshot", postgresql.JSONB, nullable=False),
        sa.Column("input_data", postgresql.JSONB, nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "resolved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_dlq_status", "dead_letter_queue", ["status"])
    op.create_index("idx_dlq_error_type", "dead_letter_queue", ["error_type"])
    op.create_index("idx_dlq_created_at", "dead_letter_queue", ["created_at"])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("dead_letter_queue")
    op.drop_table("pipeline_events")
    op.drop_table("pipeline_runs")
    op.drop_table("provider_calls")
    op.drop_table("sales_emails")
    op.drop_table("sales_scripts")
    op.drop_table("clients")
    op.drop_table("products")
    op.drop_table("summary_states")
    op.drop_table("session_summaries")
    op.drop_table("interactions")
    op.drop_table("sessions")
    op.drop_table("company_profiles")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
    op.drop_table("users")
