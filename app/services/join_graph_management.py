from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    SemanticEntity, SemanticJoinDraft, SemanticJoinRelation,
    SemanticJoinVersion, SemanticModel, WarehouseSource,
)
from app.warehouse.clickhouse import ClickHouseClient


class JoinGraphManagementError(ValueError):
    pass


def _client() -> ClickHouseClient:
    settings = get_settings()
    return ClickHouseClient(settings.clickhouse_host, settings.clickhouse_http_port,
        settings.clickhouse_reader_user, settings.clickhouse_reader_password)


def _entity(session: Session, entity_id: str) -> tuple[SemanticEntity, SemanticModel]:
    entity = session.get(SemanticEntity, entity_id)
    if entity is None:
        raise JoinGraphManagementError(f"entity does not exist: {entity_id}")
    model = session.get(SemanticModel, entity.semantic_model_id)
    published_databases = {
        str((source.connection_json or {}).get("database", ""))
        for source in session.scalars(
            select(WarehouseSource).where(WarehouseSource.status == "PUBLISHED")
        ).all()
    }
    database = model.physical_table.split(".", 1)[0] if model else ""
    if model is None or database not in published_databases:
        raise JoinGraphManagementError("entity model is not available in governed warehouse")
    return entity, model


def graph_snapshot(session: Session, workspace_id: str = "demo") -> dict[str, Any]:
    if workspace_id != get_settings().default_workspace_id:
        raise JoinGraphManagementError("workspace is not allowed")
    models = session.scalars(select(SemanticModel).order_by(SemanticModel.id)).all()
    entities = session.scalars(select(SemanticEntity).order_by(SemanticEntity.id)).all()
    relations = session.scalars(select(SemanticJoinRelation).order_by(SemanticJoinRelation.priority)).all()
    drafts = session.scalars(select(SemanticJoinDraft).order_by(SemanticJoinDraft.updated_at.desc())).all()
    return {"status": "SUCCESS", "models": [
        {"id": m.id, "name": m.name, "domain": m.business_domain_id, "table": m.physical_table,
         "time_field": m.default_time_field, "status": m.status} for m in models],
        "entities": [{"id": e.id, "model_id": e.semantic_model_id, "name": e.name,
          "grain": e.grain, "primary_keys": e.primary_key_json, "entity_type": e.entity_type,
          "status": e.status} for e in entities],
        "relations": [{"id": r.id, "left_entity_id": r.left_entity_id,
          "right_entity_id": r.right_entity_id, "left_keys": r.left_keys_json,
          "right_keys": r.right_keys_json, "relationship_type": r.relationship_type,
          "join_type": r.join_type, "fanout_strategy": r.fanout_strategy,
          "priority": r.priority, "status": r.status, "version": r.version} for r in relations],
        "drafts": [_draft_item(d) for d in drafts]}


def update_model(session: Session, model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    model = session.get(SemanticModel, model_id)
    if model is None: raise JoinGraphManagementError("semantic model does not exist")
    for key in ("name", "default_time_field", "status"):
        if key in payload: setattr(model, key, payload[key])
    entity = session.scalar(select(SemanticEntity).where(SemanticEntity.semantic_model_id == model_id))
    if entity:
        for source, target in (("grain", "grain"), ("primary_keys", "primary_key_json"),
                               ("entity_type", "entity_type"), ("entity_status", "status")):
            if source in payload: setattr(entity, target, payload[source])
    session.commit()
    return {"status": "UPDATED", "model_id": model_id}


def _draft_item(draft: SemanticJoinDraft) -> dict[str, Any]:
    return {"draft_id": draft.draft_id, "relation_id": draft.relation_id,
        "domain": draft.business_domain_id, "definition": draft.definition_json,
        "validation": draft.validation_json, "status": draft.status,
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else None}


def save_draft(session: Session, relation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("workspace_id", "demo") != get_settings().default_workspace_id:
        raise JoinGraphManagementError("workspace is not allowed")
    if not re.fullmatch(r"J_[A-Z0-9_]{3,110}", relation_id):
        raise JoinGraphManagementError("relation_id must use J_* format")
    required = ("left_entity_id", "right_entity_id", "left_keys", "right_keys",
                "relationship_type", "join_type", "fanout_strategy")
    definition = {key: payload.get(key) for key in required}
    left, _ = _entity(session, str(definition["left_entity_id"]))
    right, _ = _entity(session, str(definition["right_entity_id"]))
    if left.business_domain_id != right.business_domain_id:
        raise JoinGraphManagementError("entities must belong to the same business domain")
    if not definition["left_keys"] or len(definition["left_keys"]) != len(definition["right_keys"] or []):
        raise JoinGraphManagementError("left and right join keys must be non-empty and aligned")
    if definition["relationship_type"] not in {"one_to_one", "many_to_one", "one_to_many", "many_to_many"}:
        raise JoinGraphManagementError("unsupported relationship type")
    definition["priority"] = int(payload.get("priority", 100))
    draft = session.scalar(select(SemanticJoinDraft).where(SemanticJoinDraft.relation_id == relation_id))
    values = {"business_domain_id": left.business_domain_id, "definition_json": definition,
              "validation_json": {}, "status": "DRAFT",
              "created_by": get_settings().default_operator_id, "updated_at": datetime.now(UTC)}
    if draft is None:
        draft = SemanticJoinDraft(draft_id=f"jd_{uuid.uuid4().hex}", relation_id=relation_id, **values)
        session.add(draft)
    else:
        for key, value in values.items(): setattr(draft, key, value)
    session.commit(); session.refresh(draft)
    return {"status": "DRAFT", "draft": _draft_item(draft)}


def validate_draft(session: Session, relation_id: str) -> dict[str, Any]:
    draft = session.scalar(select(SemanticJoinDraft).where(SemanticJoinDraft.relation_id == relation_id))
    if draft is None: raise JoinGraphManagementError("join draft does not exist")
    d = draft.definition_json
    _, left_model = _entity(session, d["left_entity_id"])
    _, right_model = _entity(session, d["right_entity_id"])
    for value in [left_model.physical_table, right_model.physical_table, *d["left_keys"], *d["right_keys"]]:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", value):
            raise JoinGraphManagementError("unsafe table or field identifier")
    left_on = " AND ".join(f"l.{a}=r.{b}" for a, b in zip(d["left_keys"], d["right_keys"]))
    right_tuple = ", ".join(d["right_keys"])
    sql = f"""SELECT
      (SELECT count() FROM {left_model.physical_table}) AS left_rows,
      (SELECT count() FROM {right_model.physical_table}) AS right_rows,
      (SELECT uniqExact(tuple({right_tuple})) FROM {right_model.physical_table}) AS right_unique,
      (SELECT count() FROM {left_model.physical_table} l INNER JOIN {right_model.physical_table} r ON {left_on}) AS matched_rows
    """
    rows = _client().execute_json_rows(sql, {})
    stats = rows[0] if rows else {}
    left_rows = int(stats.get("left_rows", 0)); right_rows = int(stats.get("right_rows", 0))
    matched = int(stats.get("matched_rows", 0)); right_unique = int(stats.get("right_unique", 0))
    coverage = matched / left_rows if left_rows else 0.0
    fanout = matched / left_rows if left_rows else 0.0
    unique_rate = right_unique / right_rows if right_rows else 0.0
    safe = d["relationship_type"] in {"one_to_one", "many_to_one"} and unique_rate >= .999 and fanout <= 1.001
    validation = {"valid": True, "safe_to_publish": safe, "left_rows": left_rows,
        "right_rows": right_rows, "matched_rows": matched, "join_coverage": round(coverage, 6),
        "right_key_unique_rate": round(unique_rate, 6), "fanout_multiplier": round(fanout, 6),
        "risk_level": "LOW" if safe else "HIGH",
        "recommendation": "safe" if safe else "aggregate_before_join",
        "validated_at": datetime.now(UTC).isoformat()}
    draft.validation_json = validation; draft.status = "VALIDATED"; session.commit()
    return {"status": "VALIDATED", "relation_id": relation_id, "validation": validation}


def publish_draft(session: Session, relation_id: str) -> dict[str, Any]:
    draft = session.scalar(select(SemanticJoinDraft).where(SemanticJoinDraft.relation_id == relation_id))
    if draft is None or draft.status != "VALIDATED":
        raise JoinGraphManagementError("draft must be validated before publish")
    if not draft.validation_json.get("safe_to_publish"):
        raise JoinGraphManagementError("fanout validation does not permit publication")
    d = draft.definition_json
    current = session.get(SemanticJoinRelation, relation_id)
    history_version = session.scalar(select(func.max(SemanticJoinVersion.version)).where(
        SemanticJoinVersion.relation_id == relation_id
    ))
    version = max(int(current.version if current else 0), int(history_version or 0)) + 1
    values = {"business_domain_id": draft.business_domain_id, "left_entity_id": d["left_entity_id"],
        "right_entity_id": d["right_entity_id"], "left_keys_json": d["left_keys"],
        "right_keys_json": d["right_keys"], "relationship_type": d["relationship_type"],
        "join_type": d["join_type"], "fanout_strategy": "safe", "priority": d["priority"],
        "status": "PUBLISHED", "version": version}
    if current is None: session.add(SemanticJoinRelation(id=relation_id, **values))
    else:
        for key, value in values.items(): setattr(current, key, value)
    session.add(SemanticJoinVersion(relation_id=relation_id, version=version,
        definition_json=d, validation_json=draft.validation_json, status="PUBLISHED",
        published_by=get_settings().default_operator_id))
    session.delete(draft); session.commit()
    return {"status": "PUBLISHED", "relation_id": relation_id, "version": version}


def deprecate_relation(session: Session, relation_id: str) -> dict[str, Any]:
    relation = session.get(SemanticJoinRelation, relation_id)
    if relation is None: raise JoinGraphManagementError("relation does not exist")
    relation.status = "DEPRECATED"; session.commit()
    return {"status": "DEPRECATED", "relation_id": relation_id, "version": relation.version}


def scan_candidates(session: Session, domain: str = "production_benchmark") -> dict[str, Any]:
    entities = session.scalars(select(SemanticEntity).where(SemanticEntity.business_domain_id == domain)).all()
    models = {e.id: session.get(SemanticModel, e.semantic_model_id) for e in entities}
    databases = {m.physical_table.split(".", 1)[0] for m in models.values() if m}
    if len(databases) != 1:
        raise JoinGraphManagementError("candidate scan requires one governed warehouse database")
    database = next(iter(databases))
    table_names = [m.physical_table.split(".", 1)[1] for m in models.values() if m]
    quoted = ",".join(f"'{name}'" for name in table_names)
    rows = _client().execute_json_rows(
        f"SELECT table, name FROM system.columns WHERE database={{database:String}} AND table IN ({quoted})",
        {"database": database},
    )
    fields_by_table: dict[str, set[str]] = {}
    for row in rows: fields_by_table.setdefault(str(row["table"]), set()).add(str(row["name"]))
    candidates = []
    for left in entities:
        for right in entities:
            if left.id == right.id: continue
            left_model = models.get(left.id); right_model = models.get(right.id)
            if not left_model or not right_model: continue
            left_fields = fields_by_table.get(left_model.physical_table.split(".", 1)[1], set())
            right_keys = [str(key) for key in (right.primary_key_json or [])]
            common = [key for key in right_keys if key in left_fields]
            if common and len(common) == len(right_keys) and left.entity_type in {"fact", "bridge"}:
                candidates.append({"left_entity_id": left.id, "right_entity_id": right.id,
                    "left_keys": common, "right_keys": common, "confidence": .72,
                    "reason": "left table contains the governed key of the target entity; validate cardinality before publishing"})
    return {"status": "SUCCESS", "domain": domain, "candidates": candidates}
