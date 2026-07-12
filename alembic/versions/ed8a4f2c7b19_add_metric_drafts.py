"""add metric drafts

Revision ID: ed8a4f2c7b19
Revises: d91f4f01c6d2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "ed8a4f2c7b19"
down_revision: Union[str, Sequence[str], None] = "d91f4f01c6d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_draft",
        sa.Column("draft_id", sa.String(length=128), nullable=False),
        sa.Column("metric_id", sa.String(length=100), nullable=False),
        sa.Column("business_domain_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metric_type", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("semantic_model_id", sa.String(length=100), nullable=False),
        sa.Column("expression_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("default_aggregation", sa.String(length=32), nullable=False),
        sa.Column("time_dimension_id", sa.String(length=100), nullable=False),
        sa.Column("aliases_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dimension_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["metric_id"], ["metric_center.metric.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_domain_id"], ["metric_center.business_domain.id"]),
        sa.ForeignKeyConstraint(["semantic_model_id"], ["metric_center.semantic_model.id"]),
        sa.ForeignKeyConstraint(["time_dimension_id"], ["metric_center.dimension.id"]),
        sa.PrimaryKeyConstraint("draft_id"),
        sa.UniqueConstraint("metric_id", name="uq_metric_draft_metric"),
        schema="metric_center",
    )
    op.create_index(
        "ix_metric_center_metric_draft_metric_id",
        "metric_draft",
        ["metric_id"],
        unique=False,
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_metric_center_metric_draft_metric_id",
        table_name="metric_draft",
        schema="metric_center",
    )
    op.drop_table("metric_draft", schema="metric_center")
