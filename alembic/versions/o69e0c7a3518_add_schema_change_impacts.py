"""add schema change impacts

Revision ID: o69e0c7a3518
Revises: n58d9b6f2407
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "o69e0c7a3518"
down_revision = "n58d9b6f2407"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "business_domain_table_binding",
        sa.Column(
            "schema_contract_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="metric_center",
    )
    op.execute(
        """
        UPDATE metric_center.business_domain_table_binding AS binding
        SET schema_contract_json = contract.value
        FROM (
            SELECT
                asset.id,
                COALESCE(
                    jsonb_object_agg(column_item->>'name', column_item->>'type')
                        FILTER (WHERE column_item->>'name' IS NOT NULL),
                    '{}'::jsonb
                ) AS value
            FROM metric_center.physical_table_asset AS asset
            LEFT JOIN LATERAL jsonb_array_elements(asset.columns_json) AS column_item ON TRUE
            GROUP BY asset.id
        ) AS contract
        WHERE binding.physical_asset_id = contract.id
        """
    )
    op.create_table(
        "schema_change_event",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("physical_asset_id", sa.String(length=100), nullable=False),
        sa.Column("change_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("old_schema_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("new_schema_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "diff_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "impact_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="OPEN"),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["physical_asset_id"],
            ["metric_center.physical_table_asset.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["metric_center.warehouse_source.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="metric_center",
    )
    op.create_index(
        "ix_schema_change_source_status",
        "schema_change_event",
        ["source_id", "status"],
        schema="metric_center",
    )
    op.create_index(
        "ix_schema_change_asset_detected",
        "schema_change_event",
        ["physical_asset_id", "detected_at"],
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_schema_change_asset_detected",
        table_name="schema_change_event",
        schema="metric_center",
    )
    op.drop_index(
        "ix_schema_change_source_status",
        table_name="schema_change_event",
        schema="metric_center",
    )
    op.drop_table("schema_change_event", schema="metric_center")
    op.drop_column(
        "business_domain_table_binding",
        "schema_contract_json",
        schema="metric_center",
    )
