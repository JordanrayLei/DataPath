"""add semantic scope policy

Revision ID: e3a14c7d92f6
Revises: b7f4c2d91e60
"""

from alembic import op
import sqlalchemy as sa


revision = "e3a14c7d92f6"
down_revision = "b7f4c2d91e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_scope_policy",
        sa.Column("business_domain_id", sa.String(length=64), nullable=False),
        sa.Column("negative_threshold", sa.Float(), nullable=False),
        sa.Column("margin", sa.Float(), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["business_domain_id"],
            ["metric_center.business_domain.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("business_domain_id"),
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_table("semantic_scope_policy", schema="metric_center")
