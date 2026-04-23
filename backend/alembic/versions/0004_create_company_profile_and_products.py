"""Create company profile and products tables.

Revision ID: 0004_dashboard_data
Revises: 0003_runtime_session_schema
Create Date: 2026-04-23
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
        "company_profiles",
        sa.Column("profile_id", sa.String(length=64), primary_key=True),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("target_customer", sa.Text(), nullable=True),
        sa.Column("pricing_model", sa.Text(), nullable=True),
        sa.Column("sales_team_size", sa.Integer(), nullable=True),
        sa.Column("crm_tool", sa.Text(), nullable=True),
        sa.Column("average_deal_size", sa.Text(), nullable=True),
        sa.Column("average_sales_cycle", sa.Text(), nullable=True),
        sa.Column("primary_sales_constraint", sa.Text(), nullable=True),
        sa.Column("quarterly_sales_focus", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("product_id", sa.String(length=64), primary_key=True),
        sa.Column("company_profile_id", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("product_description", sa.Text(), nullable=True),
        sa.Column("target_customer", sa.Text(), nullable=True),
        sa.Column("primary_use_case", sa.Text(), nullable=True),
        sa.Column("pricing_model", sa.Text(), nullable=True),
        sa.Column("list_price", sa.Text(), nullable=True),
        sa.Column("sales_cycle", sa.Text(), nullable=True),
        sa.Column("deal_size", sa.Text(), nullable=True),
        sa.Column("revenue_share", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_profile_id"],
            ["company_profiles.profile_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_products_company_profile_id", "products", ["company_profile_id"])


def downgrade() -> None:
    op.drop_index("ix_products_company_profile_id", table_name="products")
    op.drop_table("products")
    op.drop_table("company_profiles")
