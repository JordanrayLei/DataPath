"""add semantic scope examples

Revision ID: 51e3c28a7d6b
Revises: c7e91d4a620f
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "51e3c28a7d6b"
down_revision = "c7e91d4a620f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_scope_example",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("business_domain_id", sa.String(length=100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(dim=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_domain_id", "source_hash", name="uq_scope_example_domain_hash"),
        schema="metric_center",
    )
    op.create_index(
        "ix_scope_example_domain",
        "semantic_scope_example",
        ["business_domain_id"],
        schema="metric_center",
    )
    op.execute(
        "CREATE INDEX ix_scope_example_hnsw_cosine "
        "ON metric_center.semantic_scope_example "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_scope_example_hnsw_cosine", table_name="semantic_scope_example", schema="metric_center")
    op.drop_index("ix_scope_example_domain", table_name="semantic_scope_example", schema="metric_center")
    op.drop_table("semantic_scope_example", schema="metric_center")
