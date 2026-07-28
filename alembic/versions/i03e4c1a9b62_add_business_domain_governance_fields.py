"""add business domain governance fields

Revision ID: i03e4c1a9b62
Revises: h92d3b0e8f51
"""

from alembic import op
import sqlalchemy as sa


revision = "i03e4c1a9b62"
down_revision = "h92d3b0e8f51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "business_domain",
        sa.Column(
            "owner",
            sa.String(length=128),
            nullable=False,
            server_default="data-platform",
        ),
        schema="metric_center",
    )
    op.add_column(
        "business_domain",
        sa.Column(
            "business_goal",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_column("business_domain", "business_goal", schema="metric_center")
    op.drop_column("business_domain", "owner", schema="metric_center")
