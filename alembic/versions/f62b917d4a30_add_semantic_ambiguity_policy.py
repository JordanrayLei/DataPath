"""add semantic ambiguity policy

Revision ID: f62b917d4a30
Revises: e3a14c7d92f6
"""

from alembic import op
import sqlalchemy as sa


revision = "f62b917d4a30"
down_revision = "e3a14c7d92f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "semantic_scope_policy",
        sa.Column("selection_margin", sa.Float(), nullable=False, server_default="0.08"),
        schema="metric_center",
    )
    op.add_column(
        "semantic_scope_policy",
        sa.Column("ambiguity_threshold", sa.Float(), nullable=False, server_default="0.64"),
        schema="metric_center",
    )
    op.add_column(
        "semantic_scope_policy",
        sa.Column("ambiguity_margin", sa.Float(), nullable=False, server_default="0.06"),
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_column("semantic_scope_policy", "ambiguity_margin", schema="metric_center")
    op.drop_column("semantic_scope_policy", "ambiguity_threshold", schema="metric_center")
    op.drop_column("semantic_scope_policy", "selection_margin", schema="metric_center")
