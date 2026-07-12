"""add semantic join graph

Revision ID: 84b6e2d91f0a
Revises: 51e3c28a7d6b
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "84b6e2d91f0a"
down_revision = "51e3c28a7d6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_entity",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("semantic_model_id", sa.String(length=100), nullable=False),
        sa.Column("business_domain_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("grain", sa.String(length=500), nullable=False),
        sa.Column("primary_key_json", postgresql.JSONB(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["business_domain_id"], ["metric_center.business_domain.id"]),
        sa.ForeignKeyConstraint(
            ["semantic_model_id"], ["metric_center.semantic_model.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("semantic_model_id"),
        schema="metric_center",
    )
    op.create_index(
        "ix_semantic_entity_domain", "semantic_entity", ["business_domain_id"],
        schema="metric_center",
    )
    op.create_table(
        "semantic_join_relation",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("business_domain_id", sa.String(length=64), nullable=False),
        sa.Column("left_entity_id", sa.String(length=100), nullable=False),
        sa.Column("right_entity_id", sa.String(length=100), nullable=False),
        sa.Column("left_keys_json", postgresql.JSONB(), nullable=False),
        sa.Column("right_keys_json", postgresql.JSONB(), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("join_type", sa.String(length=16), nullable=False),
        sa.Column("fanout_strategy", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["business_domain_id"], ["metric_center.business_domain.id"]),
        sa.ForeignKeyConstraint(
            ["left_entity_id"], ["metric_center.semantic_entity.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["right_entity_id"], ["metric_center.semantic_entity.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "left_entity_id", "right_entity_id", name="uq_semantic_join_relation_edge"
        ),
        schema="metric_center",
    )
    op.create_index(
        "ix_semantic_join_relation_domain", "semantic_join_relation", ["business_domain_id"],
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_semantic_join_relation_domain", table_name="semantic_join_relation",
        schema="metric_center",
    )
    op.drop_table("semantic_join_relation", schema="metric_center")
    op.drop_index(
        "ix_semantic_entity_domain", table_name="semantic_entity", schema="metric_center"
    )
    op.drop_table("semantic_entity", schema="metric_center")
