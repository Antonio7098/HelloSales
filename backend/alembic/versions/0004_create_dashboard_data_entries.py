"""Create dashboard data entries table.

Revision ID: 0004_dashboard_data
Revises: 0003_runtime_session_schema
Create Date: 2026-04-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_dashboard_data"
down_revision = "0003_runtime_session_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_data_entries",
        sa.Column("entry_id", sa.String(length=128), primary_key=True),
        sa.Column("dataset_key", sa.String(length=64), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("section_label", sa.String(length=128), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("answer_type", sa.String(length=64), nullable=False),
        sa.Column("example_answer", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_dashboard_data_entries_dataset_key",
        "dashboard_data_entries",
        ["dataset_key"],
    )
    op.create_index(
        "ix_dashboard_data_entries_sequence_no",
        "dashboard_data_entries",
        ["sequence_no"],
    )


def downgrade() -> None:
    op.drop_index("ix_dashboard_data_entries_sequence_no", table_name="dashboard_data_entries")
    op.drop_index("ix_dashboard_data_entries_dataset_key", table_name="dashboard_data_entries")
    op.drop_table("dashboard_data_entries")
