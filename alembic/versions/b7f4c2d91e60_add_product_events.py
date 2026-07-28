"""add privacy-preserving product events

Revision ID: b7f4c2d91e60
Revises: a18c3d7f42b1
Create Date: 2026-07-13 17:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b7f4c2d91e60"
down_revision = "a18c3d7f42b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_event",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("actor_hash", sa.String(length=64), nullable=False),
        sa.Column("conversation_hash", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("query_id", sa.String(length=128), nullable=True),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("reason_code", sa.String(length=128), nullable=False, server_default=""),
        sa.Column(
            "properties_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["query_id"], ["audit.query_run.query_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("event_id"),
        schema="audit",
    )
    op.create_index(
        "ix_product_event_workspace_name_created",
        "product_event",
        ["workspace_id", "event_name", "created_at"],
        schema="audit",
    )
    op.create_index(
        "ix_product_event_trace",
        "product_event",
        ["trace_id"],
        schema="audit",
    )
    op.create_index(
        "ix_product_event_query",
        "product_event",
        ["query_id"],
        schema="audit",
    )


def downgrade() -> None:
    op.drop_index("ix_product_event_query", table_name="product_event", schema="audit")
    op.drop_index("ix_product_event_trace", table_name="product_event", schema="audit")
    op.drop_index(
        "ix_product_event_workspace_name_created",
        table_name="product_event",
        schema="audit",
    )
    op.drop_table("product_event", schema="audit")
