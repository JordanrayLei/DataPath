"""add golden questions

Revision ID: d91f4f01c6d2
Revises: 7b6d829c53e2
Create Date: 2026-07-09 22:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d91f4f01c6d2"
down_revision: Union[str, Sequence[str], None] = "7b6d829c53e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "golden_question",
        sa.Column("golden_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("source_feedback_id", sa.String(length=128), nullable=True),
        sa.Column("query_id", sa.String(length=128), nullable=True),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("biz_domain", sa.String(length=64), nullable=False, server_default="auto"),
        sa.Column("expected_status", sa.String(length=32), nullable=False, server_default="SUCCESS"),
        sa.Column("expected_metric_id", sa.String(length=128), nullable=True),
        sa.Column("expected_intent", sa.String(length=64), nullable=True),
        sa.Column("expected_dimension_id", sa.String(length=128), nullable=True),
        sa.Column("expected_chart_type", sa.String(length=32), nullable=True),
        sa.Column("expected_row_count", sa.Integer(), nullable=True),
        sa.Column("expected_reflection_status", sa.String(length=32), nullable=True),
        sa.Column("expected_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["query_id"], ["audit.query_run.query_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_feedback_id"], ["audit.user_feedback.feedback_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("golden_id"),
        sa.UniqueConstraint("source_feedback_id", name="uq_golden_question_feedback"),
        schema="audit",
    )
    op.create_index(
        "ix_golden_question_workspace_status",
        "golden_question",
        ["workspace_id", "status", "created_at"],
        unique=False,
        schema="audit",
    )


def downgrade() -> None:
    op.drop_index("ix_golden_question_workspace_status", table_name="golden_question", schema="audit")
    op.drop_table("golden_question", schema="audit")
