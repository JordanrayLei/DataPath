"""add warehouse source governance

Revision ID: h92d3b0e8f51
Revises: g81c2a9d7e40
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "h92d3b0e8f51"
down_revision = "g81c2a9d7e40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "semantic_model",
        sa.Column("fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        schema="metric_center",
    )
    op.create_table(
        "warehouse_source",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("business_domain_id", sa.String(length=64), nullable=True),
        sa.Column("connection_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scan_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("governance_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_warehouse_source_workspace_name"),
        schema="metric_center",
    )
    op.create_index(
        "ix_metric_center_warehouse_source_workspace_id",
        "warehouse_source",
        ["workspace_id"],
        unique=False,
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_metric_center_warehouse_source_workspace_id",
        table_name="warehouse_source",
        schema="metric_center",
    )
    op.drop_table("warehouse_source", schema="metric_center")
    op.drop_column("semantic_model", "fields_json", schema="metric_center")
