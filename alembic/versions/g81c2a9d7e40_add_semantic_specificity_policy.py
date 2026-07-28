"""add semantic specificity policy

Revision ID: g81c2a9d7e40
Revises: f62b917d4a30
"""

from alembic import op
import sqlalchemy as sa


revision = "g81c2a9d7e40"
down_revision = "f62b917d4a30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("semantic_scope_policy", sa.Column("specificity_threshold", sa.Float(), nullable=False, server_default="0.60"), schema="metric_center")
    op.add_column("semantic_scope_policy", sa.Column("specificity_margin", sa.Float(), nullable=False, server_default="0.02"), schema="metric_center")


def downgrade() -> None:
    op.drop_column("semantic_scope_policy", "specificity_margin", schema="metric_center")
    op.drop_column("semantic_scope_policy", "specificity_threshold", schema="metric_center")
