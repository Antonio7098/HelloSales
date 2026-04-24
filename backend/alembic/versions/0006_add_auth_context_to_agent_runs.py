"""Add auth context snapshot columns to agent runs.

Revision ID: 0006_agent_run_auth_context
Revises: 0005_company_profile_products
Create Date: 2026-04-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_agent_run_auth_context"
down_revision = "0005_company_profile_products"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]
        for column in inspector.get_columns("agent_runs")
    } if "agent_runs" in inspector.get_table_names() else set()

    if "org_id" not in columns:
        op.add_column("agent_runs", sa.Column("org_id", sa.String(length=64), nullable=True))
    if "permissions_json" not in columns:
        op.add_column("agent_runs", sa.Column("permissions_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]
        for column in inspector.get_columns("agent_runs")
    } if "agent_runs" in inspector.get_table_names() else set()

    if "permissions_json" in columns:
        op.drop_column("agent_runs", "permissions_json")
    if "org_id" in columns:
        op.drop_column("agent_runs", "org_id")
