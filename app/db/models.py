from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BusinessDomain(Base):
    __tablename__ = "business_domain"
    __table_args__ = {"schema": "metric_center"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SemanticModel(Base):
    __tablename__ = "semantic_model"
    __table_args__ = {"schema": "metric_center"}

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    business_domain_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.business_domain.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    warehouse: Mapped[str] = mapped_column(String(64), nullable=False, default="clickhouse")
    physical_table: Mapped[str] = mapped_column(String(255), nullable=False)
    default_time_field: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    business_domain: Mapped[BusinessDomain] = relationship()


class Dimension(Base):
    __tablename__ = "dimension"
    __table_args__ = {"schema": "metric_center"}

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dimension_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    allowed_operators: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class Metric(Base):
    __tablename__ = "metric"
    __table_args__ = (
        Index("ix_metric_domain_status", "business_domain_id", "status"),
        {"schema": "metric_center"},
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    business_domain_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.business_domain.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metric_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    business_domain: Mapped[BusinessDomain] = relationship()
    versions: Mapped[list[MetricVersion]] = relationship(
        back_populates="metric", cascade="all, delete-orphan"
    )
    aliases: Mapped[list[MetricAlias]] = relationship(
        back_populates="metric", cascade="all, delete-orphan"
    )


class MetricVersion(Base):
    __tablename__ = "metric_version"
    __table_args__ = (
        UniqueConstraint("metric_id", "version", name="uq_metric_version"),
        {"schema": "metric_center"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.metric.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    semantic_model_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.semantic_model.id"), nullable=False
    )
    expression_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    default_aggregation: Mapped[str] = mapped_column(String(32), nullable=False, default="default")
    time_dimension_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.dimension.id"), nullable=False, default="D_DATE"
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PUBLISHED")
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    metric: Mapped[Metric] = relationship(back_populates="versions")
    semantic_model: Mapped[SemanticModel] = relationship()


class MetricAlias(Base):
    __tablename__ = "metric_alias"
    __table_args__ = (
        UniqueConstraint("metric_id", "alias", name="uq_metric_alias"),
        Index("ix_metric_alias_alias", "alias"),
        {"schema": "metric_center"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.metric.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(200), nullable=False)

    metric: Mapped[Metric] = relationship(back_populates="aliases")


class MetricDimension(Base):
    __tablename__ = "metric_dimension"
    __table_args__ = {"schema": "metric_center"}

    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.metric.id", ondelete="CASCADE"), primary_key=True
    )
    dimension_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.dimension.id", ondelete="CASCADE"), primary_key=True
    )


class ConversationContext(Base):
    __tablename__ = "conversation_context"
    __table_args__ = (
        UniqueConstraint("workspace_id", "conversation_id", name="uq_conversation_context"),
        {"schema": "app"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    last_query_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class QueryRun(Base):
    __tablename__ = "query_run"
    __table_args__ = (
        Index("ix_query_run_workspace_operator", "workspace_id", "operator_id"),
        Index("ix_query_run_status_created", "status", "created_at"),
        {"schema": "audit"},
    )

    query_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dsl_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dsl_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    sql_text: Mapped[str] = mapped_column(Text, nullable=False)
    sql_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sql_fingerprint: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    lineage_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    estimated_cost: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResultProfile(Base):
    __tablename__ = "result_profile"
    __table_args__ = (
        UniqueConstraint("query_id", name="uq_result_profile_query"),
        {"schema": "audit"},
    )

    profile_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    query_id: Mapped[str] = mapped_column(
        ForeignKey("audit.query_run.query_id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    profile_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_query_metric", "query_id", "metric_id"),
        {"schema": "audit"},
    )

    evidence_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("audit.result_profile.profile_id", ondelete="CASCADE"), nullable=False
    )
    query_id: Mapped[str] = mapped_column(
        ForeignKey("audit.query_run.query_id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metric_center.metric.id"), nullable=False
    )
    metric_version: Mapped[int] = mapped_column(Integer, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    time_range: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    comparison_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    calculation: Mapped[str] = mapped_column(String(128), nullable=False)
    row_refs: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReflectionValidation(Base):
    __tablename__ = "reflection_validation"
    __table_args__ = (
        UniqueConstraint(
            "query_id",
            "interpretation_hash",
            name="uq_reflection_query_interpretation",
        ),
        Index("ix_reflection_query_status", "query_id", "status"),
        {"schema": "audit"},
    )

    reflection_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    query_id: Mapped[str] = mapped_column(
        ForeignKey("audit.query_run.query_id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("audit.result_profile.profile_id", ondelete="CASCADE"), nullable=False
    )
    interpretation_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    issues_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    revision_instruction: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (
        Index("ix_user_feedback_query", "query_id"),
        Index("ix_user_feedback_status_created", "status", "created_at"),
        Index("ix_user_feedback_type", "feedback_type"),
        {"schema": "audit"},
    )

    feedback_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    operator_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    query_id: Mapped[str | None] = mapped_column(
        ForeignKey("audit.query_run.query_id", ondelete="SET NULL"), nullable=True
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False, default="")
    page_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    regression_candidate: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class GoldenQuestion(Base):
    __tablename__ = "golden_question"
    __table_args__ = (
        UniqueConstraint("source_feedback_id", name="uq_golden_question_feedback"),
        Index("ix_golden_question_workspace_status", "workspace_id", "status", "created_at"),
        {"schema": "audit"},
    )

    golden_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_feedback_id: Mapped[str | None] = mapped_column(
        ForeignKey("audit.user_feedback.feedback_id", ondelete="SET NULL"), nullable=True
    )
    query_id: Mapped[str | None] = mapped_column(
        ForeignKey("audit.query_run.query_id", ondelete="SET NULL"), nullable=True
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    biz_domain: Mapped[str] = mapped_column(String(64), nullable=False, default="auto")
    expected_status: Mapped[str] = mapped_column(String(32), nullable=False, default="SUCCESS")
    expected_metric_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expected_dimension_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_chart_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_reflection_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
