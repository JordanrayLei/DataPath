"""add join graph governance

Revision ID: a18c3d7f42b1
Revises: 84b6e2d91f0a
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a18c3d7f42b1"
down_revision = "84b6e2d91f0a"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("semantic_join_draft",
        sa.Column("draft_id", sa.String(120), primary_key=True),
        sa.Column("relation_id", sa.String(120), nullable=False, unique=True),
        sa.Column("business_domain_id", sa.String(64), nullable=False),
        sa.Column("definition_json", postgresql.JSONB(), nullable=False),
        sa.Column("validation_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_domain_id"], ["metric_center.business_domain.id"]),
        schema="metric_center")
    op.create_index("ix_semantic_join_draft_domain", "semantic_join_draft", ["business_domain_id"], schema="metric_center")
    op.create_table("semantic_join_version",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("relation_id", sa.String(120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition_json", postgresql.JSONB(), nullable=False),
        sa.Column("validation_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("published_by", sa.String(128), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("relation_id", "version", name="uq_semantic_join_version"),
        schema="metric_center")
    op.create_index("ix_semantic_join_version_relation", "semantic_join_version", ["relation_id"], schema="metric_center")

def downgrade() -> None:
    op.drop_table("semantic_join_version", schema="metric_center")
    op.drop_table("semantic_join_draft", schema="metric_center")
