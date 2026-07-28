from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    BusinessDomain,
    BusinessDomainTableBinding,
    Dimension,
    Metric,
    MetricVersion,
    PhysicalTableAsset,
    SchemaChangeEvent,
    SemanticEntity,
    SemanticJoinRelation,
    SemanticModel,
    WarehouseSource,
)
from app.schemas.governance import (
    BusinessDomainModelUpdateRequest,
    BusinessDomainItem,
    BusinessDomainTableBindingItem,
    BusinessDomainTableBindingRequest,
    BusinessDomainTableSelectionRequest,
    BusinessDomainUpsertRequest,
    PhysicalTableAssetItem,
    SchemaChangeImpactItem,
    WarehouseGovernanceRequest,
    WarehouseSourceItem,
    WarehouseSourceUpsertRequest,
)
from app.services.join_planner import expression_model_ids
from app.warehouse.clickhouse import ClickHouseClient


class WarehouseGovernanceError(ValueError):
    pass


def _domain_item(session: Session, domain: BusinessDomain) -> BusinessDomainItem:
    models = list(
        session.scalars(
            select(SemanticModel).where(
                SemanticModel.business_domain_id == domain.id,
                SemanticModel.status.in_(["ACTIVE", "DEGRADED"]),
            )
        ).all()
    )
    model_ids = [item.id for item in models]
    entities = list(
        session.scalars(
            select(SemanticEntity).where(
                SemanticEntity.business_domain_id == domain.id,
                SemanticEntity.status.in_(["ACTIVE", "DEGRADED"]),
            )
        ).all()
    )
    dimensions = session.scalars(
        select(Dimension).where(Dimension.status.in_(["ACTIVE", "DEGRADED"]))
    ).all()
    dimension_count = sum(
        bool(set((item.mapping_json or {}).keys()) & set(model_ids))
        for item in dimensions
    )
    join_count = int(
        session.scalar(
            select(func.count())
            .select_from(SemanticJoinRelation)
            .where(
                SemanticJoinRelation.business_domain_id == domain.id,
                SemanticJoinRelation.status == "PUBLISHED",
            )
        )
        or 0
    )
    metric_count = int(
        session.scalar(
            select(func.count())
            .select_from(Metric)
            .where(
                Metric.business_domain_id == domain.id,
                Metric.status == "PUBLISHED",
            )
        )
        or 0
    )
    blocked_relation_count = int(
        session.scalar(
            select(func.count())
            .select_from(SemanticJoinRelation)
            .where(
                SemanticJoinRelation.business_domain_id == domain.id,
                SemanticJoinRelation.status == "BLOCKED",
            )
        )
        or 0
    )
    blocked_metric_count = int(
        session.scalar(
            select(func.count())
            .select_from(Metric)
            .where(
                Metric.business_domain_id == domain.id,
                Metric.status == "BLOCKED",
            )
        )
        or 0
    )
    binding_count = int(
        session.scalar(
            select(func.count())
            .select_from(BusinessDomainTableBinding)
            .where(
                BusinessDomainTableBinding.business_domain_id == domain.id,
                BusinessDomainTableBinding.status.in_(
                    ["CONFIRMED", "PUBLISHED", "IMPACTED"]
                ),
            )
        )
        or 0
    )
    impacted_binding_count = int(
        session.scalar(
            select(func.count())
            .select_from(BusinessDomainTableBinding)
            .where(
                BusinessDomainTableBinding.business_domain_id == domain.id,
                BusinessDomainTableBinding.status == "IMPACTED",
            )
        )
        or 0
    )
    boundary_ready = bool(
        domain.name.strip()
        and domain.description.strip()
        and domain.owner.strip()
        and domain.business_goal.strip()
    )
    model_ready = bool(models)
    entity_by_model = {item.semantic_model_id: item for item in entities}
    blockers: list[str] = []
    degraded_models = [model for model in models if model.status == "DEGRADED"]
    if impacted_binding_count:
        blockers.append(f"{impacted_binding_count} 张业务表受到物理结构变更影响")
    if degraded_models:
        blockers.append(
            "受影响模型：" + "、".join(model.name for model in degraded_models)
        )
    if blocked_relation_count:
        blockers.append(f"{blocked_relation_count} 条模型关系已被阻断")
    if blocked_metric_count:
        blockers.append(f"{blocked_metric_count} 个指标已被阻断")
    if not model_ready:
        blockers.append("至少发布一个事实或维度语义模型")
    for model in models:
        entity = entity_by_model.get(model.id)
        if entity is None:
            blockers.append(f"{model.name}缺少已发布业务实体")
        elif entity.entity_type in {"fact", "aggregate"} and not model.default_time_field.strip():
            blockers.append(f"{model.name}缺少默认时间字段")
        elif not (entity.primary_key_json or []):
            blockers.append(f"{model.name}缺少业务唯一键")
        elif not entity.grain.strip():
            blockers.append(f"{model.name}缺少业务粒度")
    stage_status = {
        "boundary": "DONE" if boundary_ready else "PENDING",
        "data": (
            "BLOCKED"
            if impacted_binding_count
            else "DONE"
            if binding_count or model_ready
            else "PENDING"
        ),
        "models": "DONE" if model_ready and not blockers else "BLOCKED",
        "relations": (
            "BLOCKED"
            if blocked_relation_count
            else "DONE"
            if model_ready and (len(models) <= 1 or join_count > 0)
            else "PENDING"
        ),
        "metrics": (
            "BLOCKED"
            if blocked_metric_count
            else "DONE"
            if metric_count > 0
            else "PENDING"
        ),
    }
    readiness_score = sum(value == "DONE" for value in stage_status.values()) * 20
    can_create_metric = model_ready and not blockers
    if not boundary_ready:
        recommended_next_action = "完善业务目标、范围和负责人"
    elif not (binding_count or model_ready):
        recommended_next_action = "从物理资产中添加业务表"
    elif blockers:
        recommended_next_action = f"修复模型门禁：{blockers[0]}"
    elif dimension_count == 0:
        recommended_next_action = "配置业务可用维度"
    elif len(models) > 1 and join_count == 0:
        recommended_next_action = "治理并发布模型关系"
    elif metric_count == 0:
        recommended_next_action = "创建当前业务域的第一个指标"
    else:
        recommended_next_action = "检查语义策略或处理资产变更影响"
    return BusinessDomainItem(
        id=domain.id,
        name=domain.name,
        description=domain.description,
        owner=domain.owner,
        business_goal=domain.business_goal,
        status=domain.status,
        readiness_score=readiness_score,
        stage_status=stage_status,
        blockers=blockers,
        recommended_next_action=recommended_next_action,
        can_create_metric=can_create_metric,
        source_count=int(
            session.scalar(
                select(func.count(distinct(PhysicalTableAsset.source_id)))
                .select_from(BusinessDomainTableBinding)
                .join(
                    PhysicalTableAsset,
                    PhysicalTableAsset.id == BusinessDomainTableBinding.physical_asset_id,
                )
                .where(BusinessDomainTableBinding.business_domain_id == domain.id)
            )
            or 0
        ),
        binding_count=binding_count,
        model_count=len(model_ids),
        entity_count=len(entities),
        dimension_count=dimension_count,
        join_count=join_count,
        metric_count=metric_count,
    )


def list_business_domains(
    session: Session, workspace_id: str
) -> list[BusinessDomainItem]:
    if workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    domains = session.scalars(
        select(BusinessDomain)
        .where(BusinessDomain.status.in_(["ACTIVE", "DRAFT", "DEGRADED"]))
        .order_by(BusinessDomain.name)
    ).all()
    return [_domain_item(session, domain) for domain in domains]


def save_business_domain(
    session: Session,
    domain_id: str,
    payload: BusinessDomainUpsertRequest,
) -> BusinessDomainItem:
    if payload.workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", domain_id):
        raise WarehouseGovernanceError("business domain ID is invalid")
    domain = session.get(BusinessDomain, domain_id)
    values = {
        "name": payload.name,
        "description": payload.description,
        "owner": payload.owner,
        "business_goal": payload.business_goal,
    }
    if domain is None:
        domain = BusinessDomain(id=domain_id, status="DRAFT", **values)
        session.add(domain)
    else:
        for key, value in values.items():
            setattr(domain, key, value)
    session.commit()
    session.refresh(domain)
    return _domain_item(session, domain)


def _item(source: WarehouseSource) -> WarehouseSourceItem:
    return WarehouseSourceItem(
        id=source.id,
        workspace_id=source.workspace_id,
        name=source.name,
        kind=source.kind,
        business_domain_id=source.business_domain_id,
        connection=dict(source.connection_json or {}),
        scan_snapshot=dict(source.scan_snapshot_json or {}),
        governance=dict(source.governance_json or {}),
        status=source.status,
    )


def list_sources(session: Session, workspace_id: str) -> list[WarehouseSourceItem]:
    rows = session.scalars(
        select(WarehouseSource)
        .where(WarehouseSource.workspace_id == workspace_id)
        .order_by(WarehouseSource.updated_at.desc())
    ).all()
    return [_item(row) for row in rows]


def save_source(
    session: Session, source_id: str, payload: WarehouseSourceUpsertRequest
) -> WarehouseSourceItem:
    connection = payload.connection.model_dump()
    if "password" in connection:
        raise WarehouseGovernanceError("password must not be stored; use credential_env")
    source = session.get(WarehouseSource, source_id)
    if source is None:
        source = WarehouseSource(
            id=source_id,
            workspace_id=payload.workspace_id,
            name=payload.name,
            kind=payload.kind,
            connection_json=connection,
            created_by=payload.operator_id,
        )
        session.add(source)
    elif source.workspace_id != payload.workspace_id:
        raise WarehouseGovernanceError("warehouse source belongs to another workspace")
    else:
        source.name = payload.name
        source.kind = payload.kind
        source.connection_json = connection
        source.status = "DRAFT"
    session.commit()
    session.refresh(source)
    return _item(source)


def _allowed_host(host: str) -> bool:
    configured = {
        value.strip().lower()
        for value in get_settings().warehouse_scan_allowed_hosts.split(",")
        if value.strip()
    }
    configured.add(get_settings().clickhouse_host.lower())
    return host.lower() in configured


def _suggest_table(table: str, columns: list[dict[str, Any]]) -> dict[str, Any]:
    names = [str(column["name"]) for column in columns]
    prefix_type = (
        "fact" if table.startswith("fct_") else
        "dimension" if table.startswith("dim_") else
        "bridge" if table.startswith("bridge_") else
        "aggregate" if table.startswith("agg_") else
        "unknown"
    )
    enabled = prefix_type != "unknown"
    keys = [name for name in names if name == "id" or name.endswith("_id")][:3]
    time_fields = [
        name for name in names
        if re.search(r"(^|_)(date|time|timestamp|at)$", name, re.IGNORECASE)
    ]
    token = re.sub(r"^(fct|dim|bridge|agg)_", "", table).upper()
    return {
        "enabled": enabled,
        "classification_suggestion": prefix_type,
        "semantic_model_id_suggestion": f"SM_{token}",
        "entity_id_suggestion": f"E_{token}",
        "primary_key_suggestions": keys,
        "default_time_field_suggestion": time_fields[0] if time_fields else "",
        "requires_human_confirmation": True,
    }


def _asset_id(source_id: str, table_name: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{table_name}".encode()).hexdigest()[:24]
    return f"PTA_{digest}"


def _binding_id(domain_id: str, asset_id: str) -> str:
    digest = hashlib.sha256(f"{domain_id}:{asset_id}".encode()).hexdigest()[:24]
    return f"DTB_{digest}"


def _canonical_columns(columns: list[dict[str, Any]]) -> str:
    return json.dumps(columns, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _column_type_map(columns: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(item.get("name", "")): str(item.get("type", "Unknown"))
        for item in columns
        if str(item.get("name", ""))
    }


def _schema_diff(
    old_columns: list[dict[str, Any]],
    new_columns: list[dict[str, Any]],
) -> dict[str, Any]:
    old_map = _column_type_map(old_columns)
    new_map = _column_type_map(new_columns)
    return {
        "added_columns": sorted(set(new_map) - set(old_map)),
        "removed_columns": sorted(set(old_map) - set(new_map)),
        "type_changes": [
            {"field": field, "old_type": old_map[field], "new_type": new_map[field]}
            for field in sorted(set(old_map) & set(new_map))
            if old_map[field] != new_map[field]
        ],
    }


def _metric_models(version: MetricVersion) -> set[str]:
    try:
        return expression_model_ids(version.expression_json, version.semantic_model_id)
    except (AttributeError, TypeError):
        return {version.semantic_model_id}


def _propagate_schema_impact(
    session: Session,
    asset: PhysicalTableAsset,
    *,
    table_removed: bool,
    diff: dict[str, Any],
) -> dict[str, Any]:
    changed_fields = set(diff.get("removed_columns") or [])
    changed_fields.update(
        str(item.get("field", "")) for item in (diff.get("type_changes") or [])
    )
    impacted_bindings: list[str] = []
    impacted_models: list[str] = []
    impacted_entities: list[str] = []
    impacted_relations: set[str] = set()
    impacted_dimensions: set[str] = set()
    impacted_metrics: set[str] = set()
    impacted_domains: set[str] = set()
    bindings = session.scalars(
        select(BusinessDomainTableBinding).where(
            BusinessDomainTableBinding.physical_asset_id == asset.id
        )
    ).all()
    for binding in bindings:
        used_fields = set(binding.exposed_fields_json or [])
        used_fields.update(binding.primary_keys_json or [])
        if binding.default_time_field:
            used_fields.add(binding.default_time_field)
        if not table_removed and not (changed_fields & used_fields):
            continue
        impacted_bindings.append(binding.id)
        impacted_models.append(binding.semantic_model_id)
        impacted_domains.add(binding.business_domain_id)
        binding.status = "IMPACTED"
        model = session.get(SemanticModel, binding.semantic_model_id)
        if model is not None:
            model.status = "DEGRADED"
        entity = session.get(SemanticEntity, binding.entity_id)
        if entity is not None:
            impacted_entities.append(entity.id)
            entity.status = "DEGRADED"
            relations = session.scalars(
                select(SemanticJoinRelation).where(
                    (SemanticJoinRelation.left_entity_id == entity.id)
                    | (SemanticJoinRelation.right_entity_id == entity.id)
                )
            ).all()
            for relation in relations:
                relation.status = "BLOCKED"
                impacted_relations.add(relation.id)
        for dimension in session.scalars(select(Dimension)).all():
            mapping = (dimension.mapping_json or {}).get(binding.semantic_model_id)
            if mapping is None:
                continue
            if table_removed or bool(_mapping_fields(mapping) & changed_fields):
                dimension.status = "DEGRADED"
                impacted_dimensions.add(dimension.id)
        versions = session.scalars(
            select(MetricVersion).where(MetricVersion.status == "PUBLISHED")
        ).all()
        for version in versions:
            if binding.semantic_model_id not in _metric_models(version):
                continue
            metric = session.get(Metric, version.metric_id)
            if metric is not None and metric.status in {"PUBLISHED", "BLOCKED"}:
                metric.status = "BLOCKED"
                impacted_metrics.add(metric.id)
        domain = session.get(BusinessDomain, binding.business_domain_id)
        if domain is not None:
            domain.status = "DEGRADED"
    return {
        "binding_ids": sorted(impacted_bindings),
        "model_ids": sorted(impacted_models),
        "entity_ids": sorted(impacted_entities),
        "relation_ids": sorted(impacted_relations),
        "dimension_ids": sorted(impacted_dimensions),
        "metric_ids": sorted(impacted_metrics),
        "domain_ids": sorted(impacted_domains),
    }


def _record_schema_event(
    session: Session,
    source: WarehouseSource,
    asset: PhysicalTableAsset,
    *,
    change_type: str,
    severity: str,
    old_hash: str,
    new_hash: str,
    diff: dict[str, Any],
    impact: dict[str, Any],
) -> SchemaChangeEvent:
    event = SchemaChangeEvent(
        id=f"SCE_{uuid.uuid4().hex}",
        source_id=source.id,
        physical_asset_id=asset.id,
        change_type=change_type,
        severity=severity,
        old_schema_sha256=old_hash,
        new_schema_sha256=new_hash,
        diff_json=diff,
        impact_json=impact,
        status="OPEN" if severity in {"HIGH", "CRITICAL"} else "INFORMATIONAL",
    )
    session.add(event)
    return event


def _upsert_scanned_assets(
    session: Session,
    source: WarehouseSource,
    database: str,
    grouped: dict[str, list[dict[str, Any]]],
) -> list[SchemaChangeEvent]:
    current_names = set(grouped)
    existing = {
        item.table_name: item
        for item in session.scalars(
            select(PhysicalTableAsset).where(PhysicalTableAsset.source_id == source.id)
        ).all()
    }
    now = datetime.now(UTC)
    events: list[SchemaChangeEvent] = []
    for table_name, columns in grouped.items():
        canonical = _canonical_columns(columns)
        new_hash = hashlib.sha256(canonical.encode()).hexdigest()
        values = {
            "database_name": database,
            "table_name": table_name,
            "physical_table": f"{database}.{table_name}",
            "columns_json": columns,
            "schema_sha256": new_hash,
            "status": "ACTIVE",
            "scanned_at": now,
        }
        asset = existing.get(table_name)
        if asset is None:
            asset = PhysicalTableAsset(
                id=_asset_id(source.id, table_name),
                source_id=source.id,
                **values,
            )
            session.add(asset)
            session.flush()
            if existing:
                events.append(
                    _record_schema_event(
                        session,
                        source,
                        asset,
                        change_type="TABLE_ADDED",
                        severity="INFO",
                        old_hash="",
                        new_hash=new_hash,
                        diff={
                            "added_columns": sorted(_column_type_map(columns)),
                            "removed_columns": [],
                            "type_changes": [],
                        },
                        impact={},
                    )
                )
        else:
            old_hash = asset.schema_sha256
            old_columns = list(asset.columns_json or [])
            was_missing = asset.status == "MISSING"
            if old_hash != new_hash or was_missing:
                diff = _schema_diff(old_columns, columns)
                breaking = bool(diff["removed_columns"] or diff["type_changes"])
                impact = (
                    _propagate_schema_impact(
                        session, asset, table_removed=False, diff=diff
                    )
                    if breaking
                    else {}
                )
                change_type = (
                    "BREAKING_COLUMNS"
                    if breaking
                    else "TABLE_RESTORED"
                    if was_missing
                    else "ADDITIVE_COLUMNS"
                )
                events.append(
                    _record_schema_event(
                        session,
                        source,
                        asset,
                        change_type=change_type,
                        severity="HIGH" if breaking else "INFO",
                        old_hash=old_hash,
                        new_hash=new_hash,
                        diff=diff,
                        impact=impact,
                    )
                )
            for key, value in values.items():
                setattr(asset, key, value)
            if old_hash != new_hash and (diff["removed_columns"] or diff["type_changes"]):
                asset.status = "CHANGED"
    for table_name, asset in existing.items():
        if table_name not in current_names and asset.status != "MISSING":
            diff = {
                "added_columns": [],
                "removed_columns": sorted(_column_type_map(list(asset.columns_json or []))),
                "type_changes": [],
            }
            impact = _propagate_schema_impact(
                session, asset, table_removed=True, diff=diff
            )
            asset.status = "MISSING"
            asset.scanned_at = now
            events.append(
                _record_schema_event(
                    session,
                    source,
                    asset,
                    change_type="TABLE_REMOVED",
                    severity="CRITICAL",
                    old_hash=asset.schema_sha256,
                    new_hash="",
                    diff=diff,
                    impact=impact,
                )
            )
    return events


def scan_source(session: Session, source_id: str, workspace_id: str) -> WarehouseSourceItem:
    source = session.get(WarehouseSource, source_id)
    if source is None or source.workspace_id != workspace_id:
        raise WarehouseGovernanceError("warehouse source does not exist")
    connection = dict(source.connection_json or {})
    if not _allowed_host(str(connection.get("host", ""))):
        raise WarehouseGovernanceError("warehouse host is not in WAREHOUSE_SCAN_ALLOWED_HOSTS")
    credential_env = str(connection.get("credential_env", ""))
    settings = get_settings()
    configured_credentials = {
        "CLICKHOUSE_READER_PASSWORD": settings.clickhouse_reader_password,
        "CLICKHOUSE_COMPILER_PASSWORD": settings.clickhouse_compiler_password,
    }
    password = os.getenv(credential_env) or configured_credentials.get(credential_env)
    if not password:
        raise WarehouseGovernanceError(f"credential environment variable is missing: {credential_env}")
    client = ClickHouseClient(
        str(connection["host"]), int(connection["port"]), str(connection["username"]), password
    )
    database = str(connection["database"])
    rows = client.execute_json_rows(
        "SELECT table, name, type, position FROM system.columns "
        "WHERE database = {database:String} ORDER BY table, position",
        {"database": database},
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["table"]), []).append(
            {"name": str(row["name"]), "type": str(row["type"]), "position": int(row["position"])}
        )
    tables = [
        {"name": table, "columns": columns, "suggestion": _suggest_table(table, columns)}
        for table, columns in grouped.items()
    ]
    canonical = json.dumps(tables, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source.scan_snapshot_json = {
        "database": database,
        "scanned_at": datetime.now(UTC).isoformat(),
        "schema_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "table_count": len(tables),
        "column_count": sum(len(item["columns"]) for item in tables),
        "tables": tables,
    }
    events = _upsert_scanned_assets(session, source, database, grouped)
    existing_open_events = session.scalar(
        select(func.count())
        .select_from(SchemaChangeEvent)
        .where(
            SchemaChangeEvent.source_id == source.id,
            SchemaChangeEvent.status == "OPEN",
        )
    )
    source.status = (
        "DEGRADED"
        if any(event.severity in {"HIGH", "CRITICAL"} for event in events)
        or bool(existing_open_events)
        else "SCANNED"
    )
    session.commit()
    session.refresh(source)
    return _item(source)


def _column_items(model: SemanticModel) -> list[dict[str, Any]]:
    return [
        {"name": str(item.get("name", "")), "type": str(item.get("type", "Unknown")), "position": index}
        if isinstance(item, dict)
        else {"name": str(item), "type": "Unknown", "position": index}
        for index, item in enumerate(model.fields_json or [], start=1)
    ]


def _ensure_legacy_assets(session: Session, workspace_id: str) -> None:
    """Materialize assets for installations created before the physical-asset layer."""
    sources = session.scalars(
        select(WarehouseSource).where(WarehouseSource.workspace_id == workspace_id)
    ).all()
    if not sources:
        return
    changed = False
    models = session.scalars(select(SemanticModel).where(SemanticModel.status == "ACTIVE")).all()
    for model in models:
        database, separator, table_name = model.physical_table.partition(".")
        if not separator:
            continue
        source = next(
            (
                item
                for item in sources
                if str((item.connection_json or {}).get("database", "")) == database
            ),
            None,
        )
        if source is None:
            source = next(
                (item for item in sources if item.business_domain_id == model.business_domain_id),
                None,
            )
        if source is None:
            continue
        asset = session.scalar(
            select(PhysicalTableAsset).where(
                PhysicalTableAsset.source_id == source.id,
                PhysicalTableAsset.table_name == table_name,
            )
        )
        columns = _column_items(model)
        if asset is None:
            canonical = _canonical_columns(columns)
            asset = PhysicalTableAsset(
                id=_asset_id(source.id, table_name),
                source_id=source.id,
                database_name=database,
                table_name=table_name,
                physical_table=model.physical_table,
                columns_json=columns,
                schema_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
                status="ACTIVE",
            )
            session.add(asset)
            session.flush()
            changed = True
        binding = session.scalar(
            select(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.business_domain_id == model.business_domain_id,
                BusinessDomainTableBinding.physical_asset_id == asset.id,
            )
        )
        if binding is not None:
            continue
        entity = session.scalar(
            select(SemanticEntity).where(SemanticEntity.semantic_model_id == model.id)
        )
        field_names = [item["name"] for item in columns if item["name"]]
        session.add(
            BusinessDomainTableBinding(
                id=_binding_id(model.business_domain_id, asset.id),
                business_domain_id=model.business_domain_id,
                physical_asset_id=asset.id,
                semantic_model_id=model.id,
                model_name=model.name,
                description="",
                entity_id=entity.id if entity else f"E_{model.id.removeprefix('SM_')}",
                entity_name=entity.name if entity else model.name,
                entity_type=entity.entity_type if entity else "fact",
                grain=entity.grain if entity else "请确认业务粒度",
                primary_keys_json=list(entity.primary_key_json or []) if entity else field_names[:1],
                default_time_field=model.default_time_field,
                exposed_fields_json=field_names,
                schema_contract_json=_column_type_map(columns),
                status="PUBLISHED",
                created_by="legacy-backfill",
            )
        )
        changed = True
    if changed:
        session.commit()


def list_physical_assets(
    session: Session, workspace_id: str
) -> list[PhysicalTableAssetItem]:
    if workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    _ensure_legacy_assets(session, workspace_id)
    rows = session.execute(
        select(PhysicalTableAsset, WarehouseSource)
        .join(WarehouseSource, WarehouseSource.id == PhysicalTableAsset.source_id)
        .where(WarehouseSource.workspace_id == workspace_id)
        .order_by(PhysicalTableAsset.physical_table)
    ).all()
    assignments: dict[str, list[str]] = {}
    for binding in session.scalars(
        select(BusinessDomainTableBinding).order_by(
            BusinessDomainTableBinding.physical_asset_id,
            BusinessDomainTableBinding.status.desc(),
            BusinessDomainTableBinding.id,
        )
    ).all():
        assignments.setdefault(binding.physical_asset_id, []).append(
            binding.business_domain_id
        )
    return [
        PhysicalTableAssetItem(
            id=asset.id,
            source_id=source.id,
            source_name=source.name,
            database_name=asset.database_name,
            table_name=asset.table_name,
            physical_table=asset.physical_table,
            columns=list(asset.columns_json or []),
            status=asset.status,
            assigned_domain_ids=sorted(assignments.get(asset.id, [])),
        )
        for asset, source in rows
    ]


def list_schema_change_impacts(
    session: Session,
    workspace_id: str,
    event_status: str = "ALL",
) -> list[SchemaChangeImpactItem]:
    if workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    statement = (
        select(SchemaChangeEvent, PhysicalTableAsset, WarehouseSource)
        .join(
            PhysicalTableAsset,
            PhysicalTableAsset.id == SchemaChangeEvent.physical_asset_id,
        )
        .join(WarehouseSource, WarehouseSource.id == SchemaChangeEvent.source_id)
        .where(WarehouseSource.workspace_id == workspace_id)
        .order_by(SchemaChangeEvent.detected_at.desc())
    )
    if event_status != "ALL":
        statement = statement.where(SchemaChangeEvent.status == event_status)
    return [
        SchemaChangeImpactItem(
            id=event.id,
            source_id=event.source_id,
            source_name=source.name,
            physical_asset_id=event.physical_asset_id,
            physical_table=asset.physical_table,
            change_type=event.change_type,
            severity=event.severity,
            diff=dict(event.diff_json or {}),
            impact=dict(event.impact_json or {}),
            status=event.status,
            detected_at=event.detected_at.isoformat(),
            resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
        )
        for event, asset, source in session.execute(statement).all()
    ]


def _asset_field_names(asset: PhysicalTableAsset) -> list[str]:
    return [
        str(item.get("name", "")) if isinstance(item, dict) else str(item)
        for item in (asset.columns_json or [])
        if (str(item.get("name", "")) if isinstance(item, dict) else str(item))
    ]


def _asset_model_suggestion(asset: PhysicalTableAsset) -> dict[str, Any]:
    fields = _asset_field_names(asset)
    table_token = re.sub(r"^(fct|dim|bridge|agg)_", "", asset.table_name, flags=re.I)
    business_name = " ".join(part for part in table_token.split("_") if part)
    entity_type = (
        "dimension"
        if asset.table_name.startswith("dim_")
        else "bridge"
        if asset.table_name.startswith("bridge_")
        else "aggregate"
        if asset.table_name.startswith("agg_")
        else "fact"
    )
    key_candidates = [
        name for name in fields if name == "id" or name.endswith("_id")
    ]
    inferred = {
        "business_name": business_name or asset.table_name,
        "description": "",
        "entity_type": entity_type,
        "grain": f"每行一个 {business_name or asset.table_name} 业务记录",
        "primary_keys": key_candidates[:2] or fields[:1],
        "exposed_fields": fields,
    }
    return inferred


def _binding_item(
    binding: BusinessDomainTableBinding, asset: PhysicalTableAsset
) -> BusinessDomainTableBindingItem:
    fields = [
        str(item.get("name", "")) if isinstance(item, dict) else str(item)
        for item in (asset.columns_json or [])
    ]
    return BusinessDomainTableBindingItem(
        id=binding.id,
        business_domain_id=binding.business_domain_id,
        physical_asset_id=binding.physical_asset_id,
        semantic_model_id=binding.semantic_model_id,
        model_name=binding.model_name,
        description=binding.description,
        entity_id=binding.entity_id,
        entity_name=binding.entity_name,
        entity_type=binding.entity_type,
        grain=binding.grain,
        primary_keys=list(binding.primary_keys_json or []),
        default_time_field=binding.default_time_field,
        exposed_fields=list(binding.exposed_fields_json or []),
        physical_table=asset.physical_table,
        source_id=asset.source_id,
        table_name=asset.table_name,
        available_fields=fields,
        status=binding.status,
        version=binding.version,
    )


def list_domain_table_bindings(
    session: Session, domain_id: str, workspace_id: str
) -> list[BusinessDomainTableBindingItem]:
    if workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    if session.get(BusinessDomain, domain_id) is None:
        raise WarehouseGovernanceError("business domain does not exist")
    _ensure_legacy_assets(session, workspace_id)
    rows = session.execute(
        select(BusinessDomainTableBinding, PhysicalTableAsset)
        .join(
            PhysicalTableAsset,
            PhysicalTableAsset.id == BusinessDomainTableBinding.physical_asset_id,
        )
        .where(BusinessDomainTableBinding.business_domain_id == domain_id)
        .order_by(PhysicalTableAsset.physical_table)
    ).all()
    return [_binding_item(binding, asset) for binding, asset in rows]


def save_domain_table_bindings(
    session: Session,
    domain_id: str,
    payload: BusinessDomainTableBindingRequest,
) -> list[BusinessDomainTableBindingItem]:
    if payload.workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    domain = session.get(BusinessDomain, domain_id)
    if domain is None:
        raise WarehouseGovernanceError("business domain does not exist")
    seen_assets: set[str] = set()
    for definition in payload.tables:
        if definition.physical_asset_id in seen_assets:
            raise WarehouseGovernanceError("physical table bindings must be unique")
        seen_assets.add(definition.physical_asset_id)
        asset = session.get(PhysicalTableAsset, definition.physical_asset_id)
        if asset is None or asset.status != "ACTIVE":
            raise WarehouseGovernanceError(
                f"physical table asset is unavailable: {definition.physical_asset_id}"
            )
        if (
            definition.entity_type in {"fact", "aggregate"}
            and not definition.default_time_field
        ):
            raise WarehouseGovernanceError(
                "default time field is required for fact and aggregate tables"
            )
        source = session.get(WarehouseSource, asset.source_id)
        if source is None or source.workspace_id != payload.workspace_id:
            raise WarehouseGovernanceError("physical table belongs to another workspace")
        available = {
            str(item.get("name", "")) if isinstance(item, dict) else str(item)
            for item in (asset.columns_json or [])
        }
        requested = set(
            definition.primary_keys
            + ([definition.default_time_field] if definition.default_time_field else [])
            + definition.exposed_fields
        )
        unknown = requested - available
        if unknown:
            raise WarehouseGovernanceError(
                f"fields are not present in {asset.physical_table}: {', '.join(sorted(unknown))}"
            )
        conflict = session.scalar(
            select(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.semantic_model_id == definition.semantic_model_id,
                BusinessDomainTableBinding.business_domain_id != domain_id,
            )
        )
        if conflict:
            raise WarehouseGovernanceError(
                f"semantic model ID is already used by another domain: {definition.semantic_model_id}"
            )
        entity_conflict = session.scalar(
            select(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.entity_id == definition.entity_id,
                BusinessDomainTableBinding.business_domain_id != domain_id,
            )
        )
        if entity_conflict:
            raise WarehouseGovernanceError(
                f"entity ID is already used by another domain: {definition.entity_id}"
            )
        binding = session.scalar(
            select(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.business_domain_id == domain_id,
                BusinessDomainTableBinding.physical_asset_id == asset.id,
            )
        )
        values = {
            "semantic_model_id": definition.semantic_model_id,
            "model_name": definition.model_name,
            "description": definition.description,
            "entity_id": definition.entity_id,
            "entity_name": definition.entity_name,
            "entity_type": definition.entity_type,
            "grain": definition.grain,
            "primary_keys_json": definition.primary_keys,
            "default_time_field": definition.default_time_field,
            "exposed_fields_json": definition.exposed_fields,
            "schema_contract_json": _column_type_map(list(asset.columns_json or [])),
            "status": "CONFIRMED",
            "created_by": payload.operator_id,
        }
        if binding is None:
            session.add(
                BusinessDomainTableBinding(
                    id=_binding_id(domain_id, asset.id),
                    business_domain_id=domain_id,
                    physical_asset_id=asset.id,
                    **values,
                )
            )
        else:
            for key, value in values.items():
                setattr(binding, key, value)
    session.commit()
    return list_domain_table_bindings(session, domain_id, payload.workspace_id)


def _domain_model_identifiers(domain_id: str, asset: PhysicalTableAsset) -> tuple[str, str]:
    domain_token = re.sub(r"[^A-Z0-9]+", "_", domain_id.upper()).strip("_")[:40]
    table_token = re.sub(
        r"[^A-Z0-9]+",
        "_",
        re.sub(r"^(fct|dim|bridge|agg)_", "", asset.table_name, flags=re.I).upper(),
    ).strip("_")[:36]
    digest = hashlib.sha256(f"{domain_id}:{asset.id}".encode()).hexdigest()[:8].upper()
    token = f"{domain_token}_{table_token}_{digest}".strip("_")
    return f"SM_{token}"[:99], f"E_{token}"[:99]


def _default_time_field(fields: list[str]) -> str:
    return next(
        (
            field
            for field in fields
            if re.search(r"(^|_)(date|time|timestamp|at|ts)$", field, flags=re.I)
        ),
        "",
    )


def save_domain_table_selection(
    session: Session,
    domain_id: str,
    payload: BusinessDomainTableSelectionRequest,
) -> list[BusinessDomainTableBindingItem]:
    if payload.workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    if session.get(BusinessDomain, domain_id) is None:
        raise WarehouseGovernanceError("business domain does not exist")
    _ensure_legacy_assets(session, payload.workspace_id)
    selected = set(payload.physical_asset_ids)
    existing = {
        item.physical_asset_id: item
        for item in session.scalars(
            select(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.business_domain_id == domain_id
            )
        ).all()
    }
    removed_published = [
        item.physical_asset_id
        for item in existing.values()
        if item.physical_asset_id not in selected and item.status == "PUBLISHED"
    ]
    if removed_published:
        raise WarehouseGovernanceError(
            "published semantic models cannot be removed from table selection; "
            "deactivate the model first"
        )
    for asset_id in selected:
        asset = session.get(PhysicalTableAsset, asset_id)
        if asset is None or asset.status != "ACTIVE":
            raise WarehouseGovernanceError(f"physical table asset is unavailable: {asset_id}")
        source = session.get(WarehouseSource, asset.source_id)
        if source is None or source.workspace_id != payload.workspace_id:
            raise WarehouseGovernanceError("physical table belongs to another workspace")
        if asset_id in existing:
            continue
        suggestion = _asset_model_suggestion(asset)
        fields = _asset_field_names(asset)
        model_id, entity_id = _domain_model_identifiers(domain_id, asset)
        session.add(
            BusinessDomainTableBinding(
                id=_binding_id(domain_id, asset.id),
                business_domain_id=domain_id,
                physical_asset_id=asset.id,
                semantic_model_id=model_id,
                model_name=str(suggestion["business_name"]),
                description=str(suggestion["description"]),
                entity_id=entity_id,
                entity_name=str(suggestion["business_name"]),
                entity_type=str(suggestion["entity_type"]),
                grain=str(suggestion["grain"]),
                primary_keys_json=list(suggestion["primary_keys"]),
                default_time_field=_default_time_field(fields),
                exposed_fields_json=fields,
                schema_contract_json=_column_type_map(list(asset.columns_json or [])),
                status="CONFIRMED",
                version=0,
                created_by=payload.operator_id,
            )
        )
    for asset_id, binding in existing.items():
        if asset_id not in selected:
            session.delete(binding)
    session.commit()
    return list_domain_table_bindings(session, domain_id, payload.workspace_id)


def update_domain_semantic_model(
    session: Session,
    domain_id: str,
    binding_id: str,
    payload: BusinessDomainModelUpdateRequest,
) -> BusinessDomainTableBindingItem:
    if payload.workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    binding = session.get(BusinessDomainTableBinding, binding_id)
    if binding is None or binding.business_domain_id != domain_id:
        raise WarehouseGovernanceError("domain semantic model does not exist")
    asset = session.get(PhysicalTableAsset, binding.physical_asset_id)
    if asset is None or asset.status not in {"ACTIVE", "CHANGED"}:
        raise WarehouseGovernanceError("physical table asset is unavailable")
    available = set(_asset_field_names(asset))
    requested = set(payload.primary_keys + payload.exposed_fields)
    if payload.default_time_field:
        requested.add(payload.default_time_field)
    unknown = requested - available
    if unknown:
        raise WarehouseGovernanceError(
            f"fields are not present in {asset.physical_table}: {', '.join(sorted(unknown))}"
        )
    hidden_required = set(payload.primary_keys) - set(payload.exposed_fields)
    if payload.default_time_field and payload.default_time_field not in payload.exposed_fields:
        hidden_required.add(payload.default_time_field)
    if hidden_required:
        raise WarehouseGovernanceError(
            "business keys and default analysis time must be included in domain-open fields: "
            + ", ".join(sorted(hidden_required))
        )
    if (
        payload.entity_type in {"fact", "aggregate"}
        and not payload.default_time_field
    ):
        raise WarehouseGovernanceError(
            "default analysis time is required for fact and aggregate models"
        )
    binding.model_name = payload.model_name
    binding.description = payload.description
    binding.entity_name = payload.model_name
    binding.entity_type = payload.entity_type
    binding.grain = payload.grain
    binding.primary_keys_json = payload.primary_keys
    binding.default_time_field = payload.default_time_field
    binding.exposed_fields_json = payload.exposed_fields
    binding.status = "CONFIRMED"
    binding.created_by = payload.operator_id
    session.commit()
    return _binding_item(binding, asset)


def _publish_domain_binding(
    session: Session,
    domain_id: str,
    binding: BusinessDomainTableBinding,
    asset: PhysicalTableAsset,
) -> None:
    if asset.status not in {"ACTIVE", "CHANGED"}:
        raise WarehouseGovernanceError(f"physical table is unavailable: {asset.physical_table}")
    if binding.entity_type in {"fact", "aggregate"} and not binding.default_time_field:
        raise WarehouseGovernanceError("default analysis time is required before publishing")
    model = session.get(SemanticModel, binding.semantic_model_id)
    if model is not None and model.business_domain_id != domain_id:
        raise WarehouseGovernanceError(
            f"semantic model ID is owned by another domain: {binding.semantic_model_id}"
        )
    values = {
        "business_domain_id": domain_id,
        "name": binding.model_name,
        "warehouse": "clickhouse",
        "physical_table": asset.physical_table,
        "default_time_field": binding.default_time_field,
        "fields_json": list(binding.exposed_fields_json or []),
        "status": "ACTIVE",
    }
    if model is None:
        session.add(SemanticModel(id=binding.semantic_model_id, **values))
    else:
        for key, value in values.items():
            setattr(model, key, value)
    session.flush()
    entity = session.get(SemanticEntity, binding.entity_id)
    if entity is not None and entity.business_domain_id != domain_id:
        raise WarehouseGovernanceError(
            f"entity ID is owned by another domain: {binding.entity_id}"
        )
    entity_values = {
        "semantic_model_id": binding.semantic_model_id,
        "business_domain_id": domain_id,
        "name": binding.entity_name,
        "grain": binding.grain,
        "primary_key_json": list(binding.primary_keys_json or []),
        "entity_type": binding.entity_type,
        "status": "ACTIVE",
    }
    if entity is None:
        session.add(SemanticEntity(id=binding.entity_id, **entity_values))
    else:
        for key, value in entity_values.items():
            setattr(entity, key, value)
    binding.status = "PUBLISHED"
    binding.version = int(binding.version or 0) + 1
    binding.schema_contract_json = _column_type_map(list(asset.columns_json or []))


def _expression_fields_by_model(
    expression: Any,
    default_model_id: str,
    inherited_model_id: str | None = None,
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if isinstance(expression, dict):
        model_id = str(
            expression.get("source_model_id")
            or inherited_model_id
            or default_model_id
        )
        field = expression.get("field")
        if isinstance(field, str) and field:
            result.setdefault(model_id, set()).add(field)
        for value in expression.values():
            nested = _expression_fields_by_model(value, default_model_id, model_id)
            for nested_model, fields in nested.items():
                result.setdefault(nested_model, set()).update(fields)
    elif isinstance(expression, list):
        for value in expression:
            nested = _expression_fields_by_model(
                value, default_model_id, inherited_model_id
            )
            for nested_model, fields in nested.items():
                result.setdefault(nested_model, set()).update(fields)
    return result


def _mapping_fields(value: Any) -> set[str]:
    fields: set[str] = set()
    if isinstance(value, dict):
        if isinstance(value.get("field"), str):
            fields.add(value["field"])
        for item in value.values():
            fields.update(_mapping_fields(item))
    elif isinstance(value, list):
        for item in value:
            fields.update(_mapping_fields(item))
    return fields


def _reconcile_after_model_publish(
    session: Session,
    binding: BusinessDomainTableBinding,
    asset: PhysicalTableAsset,
) -> None:
    entity = session.get(SemanticEntity, binding.entity_id)
    for dimension in session.scalars(select(Dimension)).all():
        if dimension.status != "DEGRADED":
            continue
        valid = True
        for model_id, mapping in (dimension.mapping_json or {}).items():
            model = session.get(SemanticModel, model_id)
            if model is None or model.status != "ACTIVE":
                valid = False
                break
            if not _mapping_fields(mapping).issubset(set(model.fields_json or [])):
                valid = False
                break
        if valid:
            dimension.status = "ACTIVE"
    if entity is not None:
        relations = session.scalars(
            select(SemanticJoinRelation).where(
                (SemanticJoinRelation.left_entity_id == entity.id)
                | (SemanticJoinRelation.right_entity_id == entity.id),
                SemanticJoinRelation.status == "BLOCKED",
            )
        ).all()
        for relation in relations:
            left = session.get(SemanticEntity, relation.left_entity_id)
            right = session.get(SemanticEntity, relation.right_entity_id)
            if left is None or right is None:
                continue
            left_model = session.get(SemanticModel, left.semantic_model_id)
            right_model = session.get(SemanticModel, right.semantic_model_id)
            left_binding = session.scalar(
                select(BusinessDomainTableBinding).where(
                    BusinessDomainTableBinding.semantic_model_id == left.semantic_model_id
                )
            )
            right_binding = session.scalar(
                select(BusinessDomainTableBinding).where(
                    BusinessDomainTableBinding.semantic_model_id == right.semantic_model_id
                )
            )
            left_keys = relation.left_keys_json or []
            right_keys = relation.right_keys_json or []
            key_types_match = (
                bool(left_binding and right_binding)
                and bool(left_keys)
                and len(left_keys) == len(right_keys)
                and all(
                    (left_binding.schema_contract_json or {}).get(left_key)
                    == (right_binding.schema_contract_json or {}).get(right_key)
                    for left_key, right_key in zip(
                        left_keys,
                        right_keys,
                        strict=False,
                    )
                )
            )
            if (
                left.status == "ACTIVE"
                and right.status == "ACTIVE"
                and left_model is not None
                and right_model is not None
                and set(relation.left_keys_json or []).issubset(
                    set(left_model.fields_json or [])
                )
                and set(relation.right_keys_json or []).issubset(
                    set(right_model.fields_json or [])
                )
                and key_types_match
            ):
                relation.status = "PUBLISHED"
    for metric in session.scalars(
        select(Metric).where(
            Metric.business_domain_id == binding.business_domain_id,
            Metric.status == "BLOCKED",
        )
    ).all():
        version = session.scalar(
            select(MetricVersion)
            .where(
                MetricVersion.metric_id == metric.id,
                MetricVersion.status == "PUBLISHED",
            )
            .order_by(MetricVersion.version.desc())
            .limit(1)
        )
        if version is None:
            continue
        fields_by_model = _expression_fields_by_model(
            version.expression_json, version.semantic_model_id
        )
        valid = True
        for model_id, fields in fields_by_model.items():
            model = session.get(SemanticModel, model_id)
            if (
                model is None
                or model.status != "ACTIVE"
                or not fields.issubset(set(model.fields_json or []))
            ):
                valid = False
                break
        if valid:
            metric.status = "PUBLISHED"
    reconcile_domain_schema_impacts(session, binding.business_domain_id)


def reconcile_domain_schema_impacts(session: Session, domain_id: str) -> None:
    events = session.scalars(
        select(SchemaChangeEvent).where(SchemaChangeEvent.status == "OPEN")
    ).all()
    touched_sources: set[str] = set()
    touched_assets: set[str] = set()
    now = datetime.now(UTC)
    for event in events:
        impact = dict(event.impact_json or {})
        if domain_id not in set(impact.get("domain_ids") or []):
            continue
        unresolved = False
        for binding_id in impact.get("binding_ids") or []:
            row = session.get(BusinessDomainTableBinding, binding_id)
            unresolved = unresolved or row is None or row.status == "IMPACTED"
        for model_id in impact.get("model_ids") or []:
            row = session.get(SemanticModel, model_id)
            unresolved = unresolved or row is None or row.status != "ACTIVE"
        for relation_id in impact.get("relation_ids") or []:
            row = session.get(SemanticJoinRelation, relation_id)
            unresolved = unresolved or row is None or row.status == "BLOCKED"
        for dimension_id in impact.get("dimension_ids") or []:
            row = session.get(Dimension, dimension_id)
            unresolved = unresolved or row is None or row.status == "DEGRADED"
        for metric_id in impact.get("metric_ids") or []:
            row = session.get(Metric, metric_id)
            unresolved = unresolved or row is None or row.status == "BLOCKED"
        if not unresolved:
            event.status = "RESOLVED"
            event.resolved_at = now
            touched_sources.add(event.source_id)
            touched_assets.add(event.physical_asset_id)
    session.flush()
    for asset_id in touched_assets:
        open_events = session.scalar(
            select(func.count())
            .select_from(SchemaChangeEvent)
            .where(
                SchemaChangeEvent.physical_asset_id == asset_id,
                SchemaChangeEvent.status == "OPEN",
            )
        )
        asset = session.get(PhysicalTableAsset, asset_id)
        if not open_events and asset is not None and asset.status == "CHANGED":
            asset.status = "ACTIVE"
    for source_id in touched_sources:
        open_events = session.scalar(
            select(func.count())
            .select_from(SchemaChangeEvent)
            .where(
                SchemaChangeEvent.source_id == source_id,
                SchemaChangeEvent.status == "OPEN",
            )
        )
        source = session.get(WarehouseSource, source_id)
        if not open_events and source is not None and source.status == "DEGRADED":
            source.status = "SCANNED"
    blocked_bindings = session.scalar(
        select(func.count())
        .select_from(BusinessDomainTableBinding)
        .where(
            BusinessDomainTableBinding.business_domain_id == domain_id,
            BusinessDomainTableBinding.status == "IMPACTED",
        )
    )
    blocked_metrics = session.scalar(
        select(func.count())
        .select_from(Metric)
        .where(Metric.business_domain_id == domain_id, Metric.status == "BLOCKED")
    )
    domain = session.get(BusinessDomain, domain_id)
    if domain is not None and not blocked_bindings and not blocked_metrics:
        domain.status = "ACTIVE"


def publish_domain_semantic_model(
    session: Session,
    domain_id: str,
    binding_id: str,
    workspace_id: str,
) -> BusinessDomainTableBindingItem:
    if workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    binding = session.get(BusinessDomainTableBinding, binding_id)
    if binding is None or binding.business_domain_id != domain_id:
        raise WarehouseGovernanceError("domain semantic model does not exist")
    asset = session.get(PhysicalTableAsset, binding.physical_asset_id)
    if asset is None:
        raise WarehouseGovernanceError("physical table asset does not exist")
    _publish_domain_binding(session, domain_id, binding, asset)
    _reconcile_after_model_publish(session, binding, asset)
    session.commit()
    return _binding_item(binding, asset)


def publish_domain_table_bindings(
    session: Session, domain_id: str, workspace_id: str
) -> list[BusinessDomainTableBindingItem]:
    if workspace_id != get_settings().default_workspace_id:
        raise WarehouseGovernanceError("workspace is not allowed")
    domain = session.get(BusinessDomain, domain_id)
    if domain is None:
        raise WarehouseGovernanceError("business domain does not exist")
    rows = session.execute(
        select(BusinessDomainTableBinding, PhysicalTableAsset)
        .join(
            PhysicalTableAsset,
            PhysicalTableAsset.id == BusinessDomainTableBinding.physical_asset_id,
        )
        .where(
            BusinessDomainTableBinding.business_domain_id == domain_id,
            BusinessDomainTableBinding.status.in_(["CONFIRMED", "PUBLISHED"]),
        )
    ).all()
    if not rows:
        raise WarehouseGovernanceError("confirm at least one physical table before publishing")
    for binding, asset in rows:
        _publish_domain_binding(session, domain_id, binding, asset)
        _reconcile_after_model_publish(session, binding, asset)
    domain.status = "ACTIVE"
    session.commit()
    return list_domain_table_bindings(session, domain_id, workspace_id)


def save_governance(
    session: Session, source_id: str, payload: WarehouseGovernanceRequest
) -> WarehouseSourceItem:
    source = session.get(WarehouseSource, source_id)
    if source is None or source.workspace_id != payload.workspace_id:
        raise WarehouseGovernanceError("warehouse source does not exist")
    snapshot_tables = {
        item["name"]: {column["name"] for column in item["columns"]}
        for item in (source.scan_snapshot_json or {}).get("tables", [])
    }
    if not snapshot_tables:
        raise WarehouseGovernanceError("scan the warehouse before confirming governance")
    seen_models: set[str] = set()
    model_tables: dict[str, str] = {}
    for table in payload.tables:
        columns = snapshot_tables.get(table.table)
        if columns is None:
            raise WarehouseGovernanceError(f"table is not present in scan snapshot: {table.table}")
        unknown = set(table.primary_keys + [table.default_time_field]) - columns
        if unknown:
            raise WarehouseGovernanceError(
                f"confirmed fields are not present in {table.table}: {', '.join(sorted(unknown))}"
            )
        if table.semantic_model_id in seen_models:
            raise WarehouseGovernanceError("semantic model IDs must be unique")
        seen_models.add(table.semantic_model_id)
        model_tables[table.semantic_model_id] = table.table
    seen_dimensions: set[str] = set()
    for dimension in payload.dimensions:
        if dimension.dimension_id in seen_dimensions:
            raise WarehouseGovernanceError("dimension IDs must be unique")
        seen_dimensions.add(dimension.dimension_id)
        mapped_models: set[str] = set()
        for mapping in dimension.mappings:
            if mapping.semantic_model_id in mapped_models:
                raise WarehouseGovernanceError(
                    f"dimension mapping is duplicated: {dimension.dimension_id}/{mapping.semantic_model_id}"
                )
            mapped_models.add(mapping.semantic_model_id)
            physical_model_id = mapping.source_model_id or mapping.semantic_model_id
            table_name = model_tables.get(physical_model_id)
            if table_name is None:
                raise WarehouseGovernanceError(
                    f"dimension references an unpublished model: {physical_model_id}"
                )
            if mapping.field not in snapshot_tables[table_name]:
                raise WarehouseGovernanceError(
                    f"dimension field is not present in {table_name}: {mapping.field}"
                )
            if mapping.kind == "time_grain" and mapping.grain is None:
                raise WarehouseGovernanceError("time grain mapping requires grain")
    source.business_domain_id = payload.business_domain_id
    source.governance_json = payload.model_dump(mode="json")
    source.status = "CONFIRMED"
    session.commit()
    session.refresh(source)
    return _item(source)


def publish_governance(session: Session, source_id: str, workspace_id: str) -> WarehouseSourceItem:
    source = session.get(WarehouseSource, source_id)
    if source is None or source.workspace_id != workspace_id:
        raise WarehouseGovernanceError("warehouse source does not exist")
    if source.status != "CONFIRMED":
        raise WarehouseGovernanceError("human confirmation is required before publishing")
    governance = dict(source.governance_json or {})
    domain_id = str(governance["business_domain_id"])
    domain = session.get(BusinessDomain, domain_id)
    if domain is None:
        domain = BusinessDomain(
            id=domain_id,
            name=str(governance["business_domain_name"]),
            description=str(governance.get("business_domain_description", "")),
            owner="data-platform",
            business_goal=str(governance.get("business_domain_description", "")),
            status="ACTIVE",
        )
        session.add(domain)
        session.flush()
    else:
        domain.status = "ACTIVE"
    snapshot = {
        item["name"]: [column["name"] for column in item["columns"]]
        for item in source.scan_snapshot_json["tables"]
    }
    database = str(source.connection_json["database"])
    for definition in governance["tables"]:
        if not definition.get("enabled", True):
            continue
        model = session.get(SemanticModel, definition["semantic_model_id"])
        values = {
            "business_domain_id": domain_id,
            "name": definition["model_name"],
            "warehouse": source.kind,
            "physical_table": f"{database}.{definition['table']}",
            "default_time_field": definition["default_time_field"],
            "fields_json": snapshot[definition["table"]],
            "status": "ACTIVE",
        }
        if model is None:
            model = SemanticModel(id=definition["semantic_model_id"], **values)
            session.add(model)
        else:
            for key, value in values.items():
                setattr(model, key, value)
        session.flush()
        entity = session.get(SemanticEntity, definition["entity_id"])
        entity_values = {
            "semantic_model_id": definition["semantic_model_id"],
            "business_domain_id": domain_id,
            "name": definition["entity_name"],
            "grain": definition["grain"],
            "primary_key_json": definition["primary_keys"],
            "entity_type": definition["entity_type"],
            "status": "ACTIVE",
        }
        if entity is None:
            session.add(SemanticEntity(id=definition["entity_id"], **entity_values))
        else:
            for key, value in entity_values.items():
                setattr(entity, key, value)
    published_model_ids = {
        item["semantic_model_id"] for item in governance["tables"] if item.get("enabled", True)
    }
    for definition in governance.get("dimensions", []):
        mapping_json = {}
        for mapping in definition["mappings"]:
            if mapping["semantic_model_id"] not in published_model_ids:
                continue
            item = {"kind": mapping["kind"], "field": mapping["field"]}
            if mapping.get("grain"):
                item["grain"] = mapping["grain"]
            if mapping.get("source_model_id"):
                item["source_model_id"] = mapping["source_model_id"]
            mapping_json[mapping["semantic_model_id"]] = item
        dimension = session.get(Dimension, definition["dimension_id"])
        if dimension is None:
            session.add(
                Dimension(
                    id=definition["dimension_id"],
                    name=definition["name"],
                    dimension_type=definition["dimension_type"],
                    mapping_json=mapping_json,
                    allowed_operators=definition["allowed_operators"],
                    status="ACTIVE",
                )
            )
        else:
            dimension.name = definition["name"]
            dimension.dimension_type = definition["dimension_type"]
            dimension.mapping_json = {**(dimension.mapping_json or {}), **mapping_json}
            dimension.allowed_operators = definition["allowed_operators"]
            dimension.status = "ACTIVE"
    source.status = "PUBLISHED"
    session.commit()
    session.refresh(source)
    return _item(source)
