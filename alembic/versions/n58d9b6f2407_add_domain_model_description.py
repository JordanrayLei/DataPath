"""add domain semantic model description

Revision ID: n58d9b6f2407
Revises: m47c8a5e13f6
"""

from alembic import op
import sqlalchemy as sa


revision = "n58d9b6f2407"
down_revision = "m47c8a5e13f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "business_domain_table_binding",
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_column(
        "business_domain_table_binding",
        "description",
        schema="metric_center",
    )
