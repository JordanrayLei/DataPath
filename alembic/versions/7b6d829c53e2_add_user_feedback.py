"""add user feedback

Revision ID: 7b6d829c53e2
Revises: 28df3bb0422e
Create Date: 2026-07-09 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '7b6d829c53e2'
down_revision: Union[str, Sequence[str], None] = '28df3bb0422e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_feedback',
        sa.Column('feedback_id', sa.String(length=128), nullable=False),
        sa.Column('workspace_id', sa.String(length=128), nullable=False),
        sa.Column('conversation_id', sa.String(length=128), nullable=False),
        sa.Column('operator_id', sa.String(length=128), nullable=True),
        sa.Column('query_id', sa.String(length=128), nullable=True),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('feedback_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('expected_behavior', sa.Text(), nullable=False, server_default=''),
        sa.Column('page_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('snapshot_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='OPEN'),
        sa.Column('regression_candidate', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['query_id'], ['audit.query_run.query_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('feedback_id'),
        schema='audit',
    )
    op.create_index('ix_user_feedback_query', 'user_feedback', ['query_id'], unique=False, schema='audit')
    op.create_index('ix_user_feedback_status_created', 'user_feedback', ['status', 'created_at'], unique=False, schema='audit')
    op.create_index('ix_user_feedback_type', 'user_feedback', ['feedback_type'], unique=False, schema='audit')


def downgrade() -> None:
    op.drop_index('ix_user_feedback_type', table_name='user_feedback', schema='audit')
    op.drop_index('ix_user_feedback_status_created', table_name='user_feedback', schema='audit')
    op.drop_index('ix_user_feedback_query', table_name='user_feedback', schema='audit')
    op.drop_table('user_feedback', schema='audit')
