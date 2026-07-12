"""add metric semantic profiles

Revision ID: f4b2d7a1c903
Revises: ed8a4f2c7b19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f4b2d7a1c903"
down_revision: Union[str, Sequence[str], None] = "ed8a4f2c7b19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_semantic_profile",
        sa.Column("metric_id", sa.String(length=100), nullable=False),
        sa.Column("positive_examples_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("negative_examples_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retrieval_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["metric_id"], ["metric_center.metric.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("metric_id"),
        schema="metric_center",
    )
    op.add_column(
        "metric_draft",
        sa.Column("positive_examples_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        schema="metric_center",
    )
    op.add_column(
        "metric_draft",
        sa.Column("negative_examples_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_column("metric_draft", "negative_examples_json", schema="metric_center")
    op.drop_column("metric_draft", "positive_examples_json", schema="metric_center")
    op.drop_table("metric_semantic_profile", schema="metric_center")
