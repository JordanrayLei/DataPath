"""add physical assets and domain bindings

Revision ID: j14f5d2b0c73
Revises: i03e4c1a9b62
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "j14f5d2b0c73"
down_revision = "i03e4c1a9b62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "physical_table_asset",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("database_name", sa.String(length=128), nullable=False),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("physical_table", sa.String(length=255), nullable=False),
        sa.Column("columns_json", postgresql.JSONB(), nullable=False),
        sa.Column("schema_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["source_id"], ["metric_center.warehouse_source.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id", "table_name", name="uq_physical_table_asset_source_table"
        ),
        schema="metric_center",
    )
    op.create_index(
        op.f("ix_metric_center_physical_table_asset_source_id"),
        "physical_table_asset",
        ["source_id"],
        unique=False,
        schema="metric_center",
    )
    op.create_table(
        "business_domain_table_binding",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("business_domain_id", sa.String(length=64), nullable=False),
        sa.Column("physical_asset_id", sa.String(length=100), nullable=False),
        sa.Column("semantic_model_id", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("entity_name", sa.String(length=200), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("grain", sa.String(length=500), nullable=False),
        sa.Column("primary_keys_json", postgresql.JSONB(), nullable=False),
        sa.Column("default_time_field", sa.String(length=128), nullable=False),
        sa.Column("exposed_fields_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CONFIRMED"),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["business_domain_id"], ["metric_center.business_domain.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["physical_asset_id"], ["metric_center.physical_table_asset.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_domain_id",
            "physical_asset_id",
            name="uq_domain_physical_table_binding",
        ),
        sa.UniqueConstraint("semantic_model_id", name="uq_domain_binding_semantic_model"),
        sa.UniqueConstraint("entity_id", name="uq_domain_binding_entity"),
        schema="metric_center",
    )
    op.create_index(
        op.f("ix_metric_center_business_domain_table_binding_business_domain_id"),
        "business_domain_table_binding",
        ["business_domain_id"],
        unique=False,
        schema="metric_center",
    )
    op.create_index(
        op.f("ix_metric_center_business_domain_table_binding_physical_asset_id"),
        "business_domain_table_binding",
        ["physical_asset_id"],
        unique=False,
        schema="metric_center",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_metric_center_business_domain_table_binding_physical_asset_id"),
        table_name="business_domain_table_binding",
        schema="metric_center",
    )
    op.drop_index(
        op.f("ix_metric_center_business_domain_table_binding_business_domain_id"),
        table_name="business_domain_table_binding",
        schema="metric_center",
    )
    op.drop_table("business_domain_table_binding", schema="metric_center")
    op.drop_index(
        op.f("ix_metric_center_physical_table_asset_source_id"),
        table_name="physical_table_asset",
        schema="metric_center",
    )
    op.drop_table("physical_table_asset", schema="metric_center")
