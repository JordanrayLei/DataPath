"""add physical asset governance

Revision ID: k25a6e3c91d4
Revises: j14f5d2b0c73
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "k25a6e3c91d4"
down_revision = "j14f5d2b0c73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "physical_table_asset",
        sa.Column(
            "governance_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_column(
        "physical_table_asset",
        "governance_json",
        schema="metric_center",
    )
