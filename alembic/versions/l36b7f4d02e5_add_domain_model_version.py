"""add domain semantic model version

Revision ID: l36b7f4d02e5
Revises: k25a6e3c91d4
"""

from alembic import op
import sqlalchemy as sa


revision = "l36b7f4d02e5"
down_revision = "k25a6e3c91d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "business_domain_table_binding",
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_column(
        "business_domain_table_binding",
        "version",
        schema="metric_center",
    )
