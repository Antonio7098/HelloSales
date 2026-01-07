"""Initial enterprise schema - WorkOS only.

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-05

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "0001_initial"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("CREATE TYPE pipeline_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled')")
    op.execute("CREATE TYPE event_level AS ENUM ('debug', 'info', 'warn', 'error')")

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("auth_provider", sa.String(50), nullable=False, server_default="workos"),
        sa.Column("auth_subject", sa.String(255), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("accepted_legal_version", sa.String(50), nullable=True),
        sa.Column("accepted_legal_at", sa.DateTime, nullable=True),
        sa.Column("onboarding_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("auth_subject", name="ux_users_auth_subject"),
    )

    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.String(255), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("org_id", name="uq_organizations_org_id"),
    )

    # Create organization_memberships table
    op.create_table(
        "organization_memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Text, nullable=True),
        sa.Column("permissions", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("ended_at", sa.DateTime, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )

    # Create interactions table
    op.create_table(
        "interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("sequence_number", sa.Integer, nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),  # 'inbound' or 'outbound'
        sa.Column("modality", sa.String(50), nullable=True),  # 'voice', 'text', etc.
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("transcript_metadata", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(50), nullable=True),  # processing status
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
    )

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),  # 'user', 'assistant', 'system'
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("content_type", sa.String(50), nullable=False, server_default="text"),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create skills table
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create user_skills table
    op.create_table(
        "user_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("tracked", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("current_level", sa.Integer, nullable=True),
        sa.Column("target_level", sa.Integer, nullable=True),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )

    # Create assessments table
    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("level", sa.Integer, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("mode", sa.String(50), nullable=True),  # 'explicit', 'implicit', 'manual'
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create skill_assessments table
    op.create_table(
        "skill_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.UniqueConstraint("assessment_id", "skill_id", name="uq_assessment_skill"),
    )

    # Create skill_level_history table
    op.create_table(
        "skill_level_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_level", sa.Integer, nullable=True),
        sa.Column("new_level", sa.Integer, nullable=True),
        sa.Column("source", sa.String(50), nullable=True),  # 'assessment', 'manual', 'import'
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create triage_logs table
    op.create_table(
        "triage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triage_result", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create profiles table
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("goals", postgresql.JSONB, nullable=True),
        sa.Column("preferences", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # Create summaries table
    op.create_table(
        "summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("skills", postgresql.JSONB, nullable=True),
        sa.Column("highlights", postgresql.JSONB, nullable=True),
        sa.Column("improvements", postgresql.JSONB, nullable=True),
        sa.Column("action_items", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create meta_summaries table
    op.create_table(
        "meta_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.DateTime, nullable=False),
        sa.Column("period_end", sa.DateTime, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("skill_progress", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "period_start", "period_end", name="uq_meta_summary"),
    )

    # Create feedback_events table
    op.create_table(
        "feedback_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create pipeline_runs table
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.String(255), nullable=False, unique=True),
        sa.Column("pipeline_type", sa.String(100), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed", "cancelled", name="pipeline_status"), nullable=False, server_default="pending"),
        sa.Column("input_payload", postgresql.JSONB, nullable=True),
        sa.Column("output_payload", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create pipeline_events table
    op.create_table(
        "pipeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.String(255), nullable=False, index=True),
        sa.Column("stage", sa.String(100), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("level", sa.Enum("debug", "info", "warn", "error", name="event_level"), nullable=False, server_default="info"),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create provider_calls table
    op.create_table(
        "provider_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.String(255), nullable=False, index=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("request_tokens", sa.Integer, nullable=True),
        sa.Column("response_tokens", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", sa.String(255), nullable=False, index=True),
        sa.Column("artifact_type", sa.String(100), nullable=False),
        sa.Column("content", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create sailwind tables
    op.create_table(
        "sailwind_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("archetype", sa.String(100), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "sailwind_client_archetypes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("traits", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "sailwind_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("archetype", sa.String(100), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "sailwind_product_archetypes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("traits", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "sailwind_strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "sailwind_practice_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sailwind_clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sailwind_products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sailwind_strategies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "sailwind_rep_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("practice_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sailwind_practice_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rep_number", sa.Integer, nullable=False),
        sa.Column("user_input", sa.Text, nullable=True),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create session_states table
    op.create_table(
        "session_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("state", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # Create eval tables
    op.create_table(
        "eval_test_suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "eval_test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_test_suites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("input", postgresql.JSONB, nullable=True),
        sa.Column("expected_output", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "eval_benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_test_suites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "eval_test_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("benchmark_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_benchmark_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_test_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),  # passed, failed, error
        sa.Column("actual_output", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    # Create triage_annotations table
    op.create_table(
        "triage_annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("interaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("annotation", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "triage_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("triage_datasets")
    op.drop_table("triage_annotations")
    op.drop_table("eval_test_results")
    op.drop_table("eval_benchmark_runs")
    op.drop_table("eval_test_cases")
    op.drop_table("eval_test_suites")
    op.drop_table("session_states")
    op.drop_table("sailwind_rep_assignments")
    op.drop_table("sailwind_practice_sessions")
    op.drop_table("sailwind_strategies")
    op.drop_table("sailwind_product_archetypes")
    op.drop_table("sailwind_products")
    op.drop_table("sailwind_client_archetypes")
    op.drop_table("sailwind_clients")
    op.drop_table("artifacts")
    op.drop_table("provider_calls")
    op.drop_table("pipeline_events")
    op.drop_table("pipeline_runs")
    op.drop_table("feedback_events")
    op.drop_table("meta_summaries")
    op.drop_table("summaries")
    op.drop_table("profiles")
    op.drop_table("triage_logs")
    op.drop_table("skill_level_history")
    op.drop_table("skill_assessments")
    op.drop_table("assessments")
    op.drop_table("user_skills")
    op.drop_table("skills")
    op.drop_table("messages")
    op.drop_table("interactions")
    op.drop_table("sessions")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
    op.drop_table("users")

    # Drop ENUM types
    op.execute("DROP TYPE pipeline_status")
    op.execute("DROP TYPE event_level")
