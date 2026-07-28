from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.chatbi import StrictModel, TraceFields


class WarehouseConnection(StrictModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    database: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
    username: str = Field(min_length=1, max_length=128)
    credential_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")


class WarehouseSourceUpsertRequest(StrictModel):
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["clickhouse"] = "clickhouse"
    connection: WarehouseConnection
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)


class WarehouseTableGovernance(StrictModel):
    table: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
    enabled: bool = True
    semantic_model_id: str = Field(pattern=r"^SM_[A-Z0-9_]{2,96}$")
    model_name: str = Field(min_length=1, max_length=200)
    entity_id: str = Field(pattern=r"^E_[A-Z0-9_]{2,96}$")
    entity_name: str = Field(min_length=1, max_length=200)
    entity_type: Literal["fact", "dimension", "bridge", "aggregate"]
    grain: str = Field(min_length=1, max_length=500)
    primary_keys: list[str] = Field(min_length=1, max_length=12)
    default_time_field: str = Field(min_length=1, max_length=128)

    @field_validator("primary_keys")
    @classmethod
    def unique_keys(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class WarehouseDimensionMapping(StrictModel):
    semantic_model_id: str = Field(pattern=r"^SM_[A-Z0-9_]{2,96}$")
    field: str = Field(min_length=1, max_length=128)
    kind: Literal["field", "time_grain"] = "field"
    grain: Literal["day", "week", "month", "quarter", "year"] | None = None
    source_model_id: str | None = Field(default=None, pattern=r"^SM_[A-Z0-9_]{2,96}$")


class WarehouseDimensionGovernance(StrictModel):
    dimension_id: str = Field(pattern=r"^D_[A-Z0-9_]{2,96}$")
    name: str = Field(min_length=1, max_length=200)
    dimension_type: Literal["date", "time_grain", "enum", "string", "number"]
    allowed_operators: list[Literal["eq", "neq", "in", "not_in", "between", "gt", "gte", "lt", "lte"]] = Field(min_length=1, max_length=9)
    mappings: list[WarehouseDimensionMapping] = Field(min_length=1, max_length=100)


class WarehouseGovernanceRequest(StrictModel):
    workspace_id: str = "demo"
    business_domain_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    business_domain_name: str = Field(min_length=1, max_length=200)
    business_domain_description: str = Field(default="", max_length=2000)
    tables: list[WarehouseTableGovernance] = Field(min_length=1, max_length=200)
    dimensions: list[WarehouseDimensionGovernance] = Field(default_factory=list, max_length=100)
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)


class WarehouseSourceItem(StrictModel):
    id: str
    workspace_id: str
    name: str
    kind: str
    business_domain_id: str | None
    connection: dict[str, Any]
    scan_snapshot: dict[str, Any]
    governance: dict[str, Any]
    status: str


class WarehouseSourceResponse(TraceFields):
    status: Literal["SUCCESS"]
    source: WarehouseSourceItem


class WarehouseSourceListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[WarehouseSourceItem]


class BusinessDomainUpsertRequest(StrictModel):
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    owner: str = Field(min_length=1, max_length=128)
    business_goal: str = Field(min_length=1, max_length=2000)
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)


class BusinessDomainItem(StrictModel):
    id: str
    name: str
    description: str
    owner: str
    business_goal: str
    status: str
    readiness_score: int
    stage_status: dict[str, str]
    blockers: list[str]
    recommended_next_action: str
    can_create_metric: bool
    source_count: int
    binding_count: int
    model_count: int
    entity_count: int
    dimension_count: int
    join_count: int
    metric_count: int


class BusinessDomainListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[BusinessDomainItem]


class BusinessDomainResponse(TraceFields):
    status: Literal["SUCCESS"]
    domain: BusinessDomainItem


class PhysicalTableAssetItem(StrictModel):
    id: str
    source_id: str
    source_name: str
    database_name: str
    table_name: str
    physical_table: str
    columns: list[dict[str, Any]]
    status: str
    assigned_domain_ids: list[str]


class PhysicalTableAssetListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[PhysicalTableAssetItem]


class SchemaChangeImpactItem(StrictModel):
    id: str
    source_id: str
    source_name: str
    physical_asset_id: str
    physical_table: str
    change_type: str
    severity: str
    diff: dict[str, Any]
    impact: dict[str, Any]
    status: str
    detected_at: str
    resolved_at: str | None


class SchemaChangeImpactListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[SchemaChangeImpactItem]
    summary: dict[str, int]


class BusinessDomainTableBindingInput(StrictModel):
    physical_asset_id: str = Field(min_length=1, max_length=100)
    semantic_model_id: str = Field(pattern=r"^SM_[A-Z0-9_]{2,96}$")
    model_name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    entity_id: str = Field(pattern=r"^E_[A-Z0-9_]{2,96}$")
    entity_name: str = Field(min_length=1, max_length=200)
    entity_type: Literal["fact", "dimension", "bridge", "aggregate"]
    grain: str = Field(min_length=1, max_length=500)
    primary_keys: list[str] = Field(min_length=1, max_length=12)
    default_time_field: str = Field(default="", max_length=128)
    exposed_fields: list[str] = Field(min_length=1, max_length=500)

    @field_validator("primary_keys", "exposed_fields")
    @classmethod
    def unique_field_names(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class BusinessDomainTableBindingRequest(StrictModel):
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    tables: list[BusinessDomainTableBindingInput] = Field(min_length=1, max_length=200)
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)


class BusinessDomainTableSelectionRequest(StrictModel):
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    physical_asset_ids: list[str] = Field(min_length=1, max_length=200)
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)

    @field_validator("physical_asset_ids")
    @classmethod
    def unique_asset_ids(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class BusinessDomainModelUpdateRequest(StrictModel):
    workspace_id: str = Field(default="demo", min_length=1, max_length=128)
    model_name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    entity_type: Literal["fact", "dimension", "bridge", "aggregate"]
    grain: str = Field(min_length=1, max_length=500)
    primary_keys: list[str] = Field(min_length=1, max_length=12)
    default_time_field: str = Field(default="", max_length=128)
    exposed_fields: list[str] = Field(min_length=1, max_length=500)
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)

    @field_validator("primary_keys", "exposed_fields")
    @classmethod
    def unique_model_fields(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class BusinessDomainTableBindingItem(BusinessDomainTableBindingInput):
    id: str
    business_domain_id: str
    physical_table: str
    source_id: str
    table_name: str
    available_fields: list[str]
    status: str
    version: int


class BusinessDomainTableBindingListResponse(TraceFields):
    status: Literal["SUCCESS"]
    items: list[BusinessDomainTableBindingItem]


class MetricPreheatGenerateRequest(StrictModel):
    workspace_id: str = "demo"
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)


class MetricPreheatApplyRequest(StrictModel):
    workspace_id: str = "demo"
    aliases: list[str] = Field(default_factory=list, max_length=30)
    positive_examples: list[str] = Field(default_factory=list, max_length=80)
    negative_examples: list[str] = Field(default_factory=list, max_length=80)
    operator_id: str = Field(default="metric_admin", min_length=1, max_length=128)


class MetricPreheatResponse(TraceFields):
    status: Literal["SUCCESS"]
    metric_id: str
    proposal: dict[str, Any]
