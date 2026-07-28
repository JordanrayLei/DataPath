"""backfill published domain semantic model versions

Revision ID: m47c8a5e13f6
Revises: l36b7f4d02e5
"""

from alembic import op


revision = "m47c8a5e13f6"
down_revision = "l36b7f4d02e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE metric_center.business_domain_table_binding
        SET version = 1
        WHERE status = 'PUBLISHED' AND version = 0
        """
    )


def downgrade() -> None:
    pass
