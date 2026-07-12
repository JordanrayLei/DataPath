"""add metric vector index

Revision ID: c7e91d4a620f
Revises: f4b2d7a1c903
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "c7e91d4a620f"
down_revision: Union[str, Sequence[str], None] = "f4b2d7a1c903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "metric_embedding",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("metric_id", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["metric_id"], ["metric_center.metric.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_id", "source_type", "source_hash", "embedding_model", name="uq_metric_embedding_source"),
        schema="metric_center",
    )
    op.create_index(
        "ix_metric_embedding_metric_active",
        "metric_embedding",
        ["metric_id", "is_active"],
        schema="metric_center",
    )
    op.execute(
        "CREATE INDEX ix_metric_embedding_hnsw_cosine "
        "ON metric_center.metric_embedding USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS metric_center.ix_metric_embedding_hnsw_cosine")
    op.drop_index("ix_metric_embedding_metric_active", table_name="metric_embedding", schema="metric_center")
    op.drop_table("metric_embedding", schema="metric_center")
