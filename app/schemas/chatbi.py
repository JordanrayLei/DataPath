from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TraceFields(BaseModel):
    request_id: str
    trace_id: str


class ContextLoadRequest(StrictModel):
    workspace_id: str = Field(min_length=1, max_length=128)
    conversation_id: str = Field(min_length=1, max_length=128)
    identity_token: str = Field(min_length=1, max_length=4096)


class ContextLoadResponse(TraceFields):
    operator_id: str
    allowed_domains: list[str]
    role_ids: list[str]
    row_policy_token: str
    last_query_context: dict[str, Any]


class FilterMention(StrictModel):
    field: str = Field(max_length=200)
    value: str = Field(max_length=500)


class PreprocessData(StrictModel):
    normalized_query: str = Field(max_length=4000)
    metric_mentions: list[str] = Field(max_length=10)
    dimension_mentions: list[str] = Field(max_length=10)
    filter_mentions: list[FilterMention] = Field(max_length=20)
    time_text: str = Field(max_length=500)
    time_start: str = Field(max_length=50)
    time_end: str = Field(max_length=50)
    comparison: str = Field(max_length=200)
    inherit_context: bool


class MetricRetrieveRequest(StrictModel):
    query: str = Field(min_length=1, max_length=4000)
    normalized_query: str = Field(min_length=1, max_length=4000)
    workspace_id: str
    biz_domain: Literal["sales", "advertising"]
    operator_id: str
    context: dict[str, Any]
    preprocess: PreprocessData


class MetricCandidate(StrictModel):
    metric_id: str
    metric_version: int
    display_name: str
    metric_type: Literal["amount", "count", "ratio", "average"]
    unit: str
    business_definition: str
    probability: float = Field(ge=0, le=1)
    retrieval_sources: list[str]
    authorized: Literal[True] = True


class MetricMentionDecision(StrictModel):
    text: str
    selected_metric_id: str
    selected_metric_version: int | None
    probability: float = Field(ge=0, le=1)
    candidates: list[MetricCandidate]


class MetricRetrieveResponse(TraceFields):
    gate_status: Literal["PASS", "LLM_DISAMBIGUATE", "CLARIFY", "REJECT"]
    mentions: list[MetricMentionDecision]
    reason_codes: list[str]
    clarification_message: str
    time_resolution: dict[str, Any] = Field(default_factory=dict)
    dsl_generation_constraints: list[str] = Field(default_factory=list)


class MetricCatalogDimension(StrictModel):
    dimension_id: str
    name: str
    dimension_type: str
    allowed_operators: list[str]


class MetricCatalogSemanticModel(StrictModel):
    semantic_model_id: str
    name: str
    warehouse: str
    physical_table: str
    default_time_field: str


class MetricCatalogItem(StrictModel):
    metric_id: str
    business_domain_id: str
    business_domain_name: str
    name: str
    description: str
    metric_type: str
    unit: str
    owner: str
    status: str
    latest_version: int
    aliases: list[str]
    dimensions: list[MetricCatalogDimension]
    semantic_model: MetricCatalogSemanticModel
    formula_text: str
    lineage: dict[str, list[str]]
    example_questions: list[str]


class MetricCatalogListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[MetricCatalogItem]
    total: int
    domain_counts: dict[str, int]


class MetricCatalogDetailResponse(TraceFields):
    status: Literal["SUCCESS"]
    metric: MetricCatalogItem
    expression: dict[str, Any]
    version_status: str
    published_at: datetime


class QueryMetric(StrictModel):
    metric_id: str = Field(pattern=r"^M_[A-Z0-9_]{2,100}$")
    metric_version: int = Field(ge=1)
    aggregation: Literal[
        "default", "sum", "avg", "min", "max", "count", "count_distinct"
    ] = "default"
    alias: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


class QueryDimension(StrictModel):
    dimension_id: str = Field(pattern=r"^D_[A-Z0-9_]{2,100}$")
    alias: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


FilterScalar = str | float | bool


class QueryFilter(StrictModel):
    field_id: str = Field(pattern=r"^(D|M)_[A-Z0-9_]{2,100}$")
    operator: Literal[
        "eq",
        "neq",
        "in",
        "not_in",
        "gt",
        "gte",
        "lt",
        "lte",
        "between",
        "contains",
        "is_null",
        "is_not_null",
    ]
    values: list[FilterScalar] = Field(max_length=100)

    @model_validator(mode="after")
    def validate_value_count(self) -> QueryFilter:
        if self.operator == "between" and len(self.values) != 2:
            raise ValueError("between requires exactly two values")
        if self.operator in {"is_null", "is_not_null"} and self.values:
            raise ValueError(f"{self.operator} requires an empty values array")
        if self.operator not in {"is_null", "is_not_null"} and not self.values:
            raise ValueError(f"{self.operator} requires at least one value")
        return self


class TimeRange(StrictModel):
    start: date
    end: date
    timezone: str

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("unknown IANA timezone") from error
        return value

    @model_validator(mode="after")
    def validate_order(self) -> TimeRange:
        if self.end < self.start:
            raise ValueError("time_range.end must not precede time_range.start")
        return self


class Comparison(StrictModel):
    mode: Literal["period_over_period", "year_over_year", "custom"]
    custom_range: TimeRange | None = None

    @model_validator(mode="after")
    def validate_custom_range(self) -> Comparison:
        if self.mode == "custom" and self.custom_range is None:
            raise ValueError("custom comparison requires custom_range")
        if self.mode != "custom" and self.custom_range is not None:
            raise ValueError("custom_range is only allowed for custom comparison")
        return self


class SortItem(StrictModel):
    field_id: str = Field(pattern=r"^(D|M)_[A-Z0-9_]{2,100}$")
    direction: Literal["asc", "desc"]


class QueryDsl(StrictModel):
    dsl_version: Literal["1.0"]
    intent: Literal[
        "aggregate_query", "trend_query", "comparison_query", "ranking_query"
    ]
    metrics: list[QueryMetric] = Field(min_length=1, max_length=5)
    dimensions: list[QueryDimension] = Field(max_length=5)
    filters: list[QueryFilter] = Field(max_length=10)
    time_range: TimeRange
    comparison: Comparison | None = None
    sort: list[SortItem] = Field(max_length=5)
    limit: int = Field(default=500, ge=1, le=5000)

    @model_validator(mode="after")
    def validate_intent_shape(self) -> QueryDsl:
        metric_keys = {(metric.metric_id, metric.metric_version) for metric in self.metrics}
        if len(metric_keys) != len(self.metrics):
            raise ValueError("metrics must be unique")
        dimension_ids = [item.dimension_id for item in self.dimensions]
        if len(set(dimension_ids)) != len(dimension_ids):
            raise ValueError("dimensions must be unique")
        if self.intent == "comparison_query" and self.comparison is None:
            raise ValueError("comparison_query requires comparison")
        if self.intent == "trend_query" and not set(dimension_ids) & {
            "D_DATE",
            "D_WEEK",
            "D_MONTH",
            "D_QUARTER",
        }:
            raise ValueError("trend_query requires a time-grain dimension")
        if self.intent == "ranking_query" and (not self.dimensions or not self.sort):
            raise ValueError("ranking_query requires a dimension and sort")
        return self


class DslValidateRequest(StrictModel):
    workspace_id: str
    operator_id: str
    row_policy_context: dict[str, Any]
    dsl: dict[str, Any]


class ValidationIssue(StrictModel):
    code: str
    message: str
    field_path: str
    safe_to_show: bool = True


class DslValidateResponse(TraceFields):
    status: Literal["VALID", "CLARIFY", "DENY", "INVALID"]
    normalized_dsl: dict[str, Any] | None
    issues: list[ValidationIssue]
    message: str


class CompileRequest(StrictModel):
    workspace_id: str
    operator_id: str
    dsl: QueryDsl
    permission_context: dict[str, Any]


class EstimatedCost(StrictModel):
    risk_level: Literal["low", "medium", "high", "blocked"]
    estimated_rows: int = Field(ge=0)
    estimated_bytes: int = Field(ge=0)


class Lineage(StrictModel):
    models: list[str]
    tables: list[str]
    fields: list[str]


class CompileResponse(TraceFields):
    status: Literal["READY", "NEED_APPROVAL", "BLOCKED"]
    query_id: str
    sql_fingerprint: str
    dsl_hash: str
    metric_versions: dict[str, int]
    lineage: Lineage
    estimated_cost: EstimatedCost
    execution_token: str | None = None
    expires_at: datetime
    message: str


class ExecuteRequest(StrictModel):
    workspace_id: str
    operator_id: str
    query_id: str
    execution_token: str | None = None
    approval_token: str | None = None
    compiled_query: dict[str, Any] | None = Field(
        default=None,
        deprecated=True,
        description="Ignored compatibility field. SQL is loaded server-side by query_id.",
    )


class ResultColumn(StrictModel):
    name: str
    type: Literal["string", "integer", "decimal", "boolean", "date", "datetime"]
    unit: str | None = None
    metric_id: str | None = None
    dimension_id: str | None = None


class DataQualitySummary(StrictModel):
    freshness: Literal["normal", "delayed", "unknown"]
    data_updated_at: datetime | None = None
    completeness: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class ExecuteResponse(TraceFields):
    query_id: str
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT"]
    columns: list[ResultColumn]
    rows: list[dict[str, Any]]
    row_count: int
    execution_ms: int
    cached: bool
    truncated: bool
    result_ref: str | None
    data_quality: DataQualitySummary
    error: dict[str, Any] | None = None


class ProfileRequest(StrictModel):
    workspace_id: str
    query_id: str
    execution_result: ExecuteResponse
    dsl: QueryDsl


class EvidenceComparison(StrictModel):
    method: str
    baseline_value: float | int | str | None = None
    absolute_change: float | None = None
    change_rate: float | None = None
    z_score: float | None = None
    share: float | None = None


class Evidence(StrictModel):
    evidence_id: str
    evidence_type: Literal["headline", "trend", "anomaly", "contribution"]
    statement: str
    metric_id: str
    metric_version: int
    value: float | int | str | None
    unit: str
    time_range: TimeRange
    dimensions: dict[str, str | int | float | bool]
    comparison: EvidenceComparison | None = None
    query_id: str
    calculation: str
    row_refs: list[int]


class HeadlineMetric(StrictModel):
    metric_id: str
    metric_version: int
    display_name: str
    value: float | int | str | None
    unit: str
    scope: Literal["latest_period", "full_range", "single_result"]
    dimensions: dict[str, str | int | float | bool]
    evidence_id: str


class TrendSummary(StrictModel):
    metric_id: str
    metric_version: int
    start_value: float
    end_value: float
    absolute_change: float
    change_rate: float | None
    direction: Literal["up", "down", "flat"]
    point_count: int
    evidence_id: str


class AnomalyPoint(StrictModel):
    metric_id: str
    metric_version: int
    time_value: str
    value: float
    z_score: float
    direction: Literal["high", "low"]
    dimensions: dict[str, str | int | float | bool]
    evidence_id: str


class DimensionContribution(StrictModel):
    metric_id: str
    metric_version: int
    dimension_id: str
    dimension_value: str | int | float | bool
    value: float
    share: float
    rank: int
    evidence_id: str


class ChartSpec(StrictModel):
    type: Literal["line", "bar", "grouped_bar", "stacked_bar", "area", "table", "metric"]
    x: str
    y: str | list[str]
    series: str | None = None
    title: str


class ProfileResponse(TraceFields):
    profile_id: str
    profile_version: Literal["1.0"]
    query_id: str
    headline_metrics: list[HeadlineMetric]
    trend_summary: list[TrendSummary]
    anomalies: list[AnomalyPoint]
    dimension_contributions: list[DimensionContribution]
    chart_spec: ChartSpec
    evidence: list[Evidence]
    caveats: list[str]


class Finding(StrictModel):
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("evidence_ids")
    @classmethod
    def validate_unique_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("evidence_ids must be unique")
        return value


class Interpretation(StrictModel):
    title: str = Field(min_length=1, max_length=500)
    findings: list[Finding] = Field(max_length=10)
    caveats: list[str] = Field(max_length=10)
    next_actions: list[str] = Field(max_length=10)


class ReflectionRequest(StrictModel):
    workspace_id: str = Field(min_length=1, max_length=128)
    query_id: str = Field(min_length=1, max_length=128)
    dsl: QueryDsl
    profile: ProfileResponse
    interpretation: Interpretation


class InterpretationGenerateRequest(StrictModel):
    workspace_id: str = Field(min_length=1, max_length=128)
    query_id: str = Field(min_length=1, max_length=128)
    dsl: QueryDsl
    profile: ProfileResponse


class InterpretationGenerateResponse(TraceFields):
    interpretation: Interpretation


ReflectionIssueCode = Literal[
    "UNKNOWN_EVIDENCE_ID",
    "NUMERIC_MISMATCH",
    "UNIT_MISMATCH",
    "TIME_RANGE_MISMATCH",
    "METRIC_VERSION_MISMATCH",
    "MISSING_DATA_QUALITY_CAVEAT",
    "UNSUPPORTED_CAUSAL_CLAIM",
    "SENSITIVE_DATA_EXPOSURE",
    "UNSUPPORTED_CLAIM",
]


class ReflectionIssue(StrictModel):
    code: ReflectionIssueCode
    message: str
    finding_index: int | None = Field(default=None, ge=0)


class ReflectionResponse(TraceFields):
    status: Literal["PASS", "REVISE", "BLOCK"]
    issues: list[ReflectionIssue]
    revision_instruction: str = Field(max_length=4000)


class ChatbiAskRequest(StrictModel):
    query: str = Field(min_length=1, max_length=1000)
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    conversation_id: str = Field(default="frontend_demo", min_length=1, max_length=128)
    biz_domain: Literal["auto", "sales", "advertising"] = "auto"
    timezone: str = "Asia/Shanghai"

    @field_validator("timezone")
    @classmethod
    def validate_ask_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("unknown IANA timezone") from error
        return value


class ChatbiPipelineStep(StrictModel):
    key: str
    label: str
    status: Literal["PASS", "CLARIFY", "REJECT", "BLOCKED", "ERROR"]
    detail: str = ""


class ChatbiAskResponse(TraceFields):
    status: Literal["SUCCESS", "CLARIFY", "REJECT", "BLOCKED", "ERROR"]
    message: str
    query: str
    workspace_id: str
    conversation_id: str
    operator_id: str | None = None
    biz_domain: str
    selected_metric: dict[str, Any] | None = None
    dsl: dict[str, Any] | None = None
    retrieval: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    compiled: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None
    profile: dict[str, Any] | None = None
    interpretation: dict[str, Any] | None = None
    reflection: dict[str, Any] | None = None
    answer_markdown: str = ""
    steps: list[ChatbiPipelineStep]


class FeedbackSubmitRequest(StrictModel):
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    conversation_id: str = Field(default="frontend_demo", min_length=1, max_length=128)
    query_id: str | None = Field(default=None, max_length=128)
    user_query: str = Field(min_length=1, max_length=1000)
    feedback_type: Literal[
        "METRIC_WRONG",
        "DATA_WRONG",
        "INTERPRETATION_UNTRUSTED",
        "CHART_WRONG",
        "PERMISSION_ISSUE",
        "UI_ISSUE",
        "OTHER",
    ]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    message: str = Field(min_length=1, max_length=2000)
    expected_behavior: str = Field(default="", max_length=2000)
    page_context: dict[str, Any] = Field(default_factory=dict)


class FeedbackSubmitResponse(TraceFields):
    status: Literal["ACCEPTED"]
    feedback_id: str
    query_id: str | None
    feedback_type: str
    severity: str
    regression_candidate: bool
    message: str


class FeedbackItem(StrictModel):
    feedback_id: str
    workspace_id: str
    conversation_id: str
    operator_id: str | None
    query_id: str | None
    user_query: str
    feedback_type: str
    severity: str
    message: str
    expected_behavior: str
    status: str
    regression_candidate: bool
    created_at: datetime
    page_context: dict[str, Any]
    snapshot: dict[str, Any]


class FeedbackListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[FeedbackItem]
    total: int
    status_counts: dict[str, int]


class FeedbackStatusUpdateRequest(StrictModel):
    status: Literal["OPEN", "CONFIRMED", "FIXED", "WONT_FIX"]


class FeedbackStatusUpdateResponse(TraceFields):
    status: Literal["SUCCESS"]
    feedback: FeedbackItem
    message: str


class GoldenQuestionItem(StrictModel):
    golden_id: str
    workspace_id: str
    source_feedback_id: str | None
    query_id: str | None
    user_query: str
    biz_domain: str
    expected_status: str
    expected_metric_id: str | None
    expected_intent: str | None
    expected_dimension_id: str | None
    expected_chart_type: str | None
    expected_row_count: int | None
    expected_reflection_status: str | None
    expected_notes: str
    status: str
    created_at: datetime
    updated_at: datetime


class GoldenQuestionListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[GoldenQuestionItem]
    total: int
    status_counts: dict[str, int]


class GoldenQuestionCreateFromFeedbackRequest(StrictModel):
    biz_domain: Literal["auto", "sales", "advertising"] = "auto"
    expected_status: Literal["SUCCESS", "CLARIFY", "REJECT", "BLOCKED", "ERROR"] = "SUCCESS"
    expected_notes: str = Field(default="", max_length=2000)


class GoldenQuestionCreateResponse(TraceFields):
    status: Literal["SUCCESS"]
    golden_question: GoldenQuestionItem
    created: bool
    message: str


class GoldenQuestionEvaluationRequest(StrictModel):
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    status: Literal["ACTIVE", "ARCHIVED", "ALL"] = "ACTIVE"
    limit: int = Field(default=20, ge=1, le=100)


class GoldenQuestionCaseResult(StrictModel):
    golden_id: str
    user_query: str
    passed: bool
    errors: list[str]
    latency_ms: int
    observed_status: str | None
    observed_metric_id: str | None
    observed_intent: str | None
    observed_dimension_id: str | None
    observed_chart_type: str | None
    observed_row_count: int | None
    observed_reflection_status: str | None


class GoldenQuestionEvaluationResponse(TraceFields):
    status: Literal["PASS", "FAIL", "EMPTY"]
    total: int
    passed: int
    pass_rate: float
    results: list[GoldenQuestionCaseResult]
