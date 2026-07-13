from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SemanticEntity, SemanticJoinRelation, SemanticModel


class JoinPlanningError(ValueError):
    pass


@dataclass(frozen=True)
class PlannedJoin:
    relation_id: str
    left_model_id: str
    right_model_id: str
    left_table: str
    right_table: str
    left_keys: tuple[str, ...]
    right_keys: tuple[str, ...]
    join_type: str
    relationship_type: str
    fanout_strategy: str


@dataclass(frozen=True)
class JoinPlan:
    query_mode: str
    base_model_id: str
    model_aliases: dict[str, str]
    joins: tuple[PlannedJoin, ...]


def expression_model_ids(expression: dict, default_model_id: str) -> set[str]:
    models = {str(expression.get("source_model_id") or default_model_id)}
    for key in ("numerator", "denominator"):
        nested = expression.get(key)
        if isinstance(nested, dict):
            models.update(expression_model_ids(nested, default_model_id))
    for nested in expression.get("terms") or []:
        if isinstance(nested, dict):
            models.update(expression_model_ids(nested, default_model_id))
    return models


def plan_query_models(
    session: Session,
    base_model_id: str,
    required_model_ids: set[str],
) -> JoinPlan:
    required = {item for item in required_model_ids if item} | {base_model_id}
    models = {
        item.id: item
        for item in session.scalars(
            select(SemanticModel).where(SemanticModel.id.in_(required))
        ).all()
    }
    if set(models) != required:
        raise JoinPlanningError("one or more required semantic models do not exist")
    if len(required) == 1:
        return JoinPlan("single_model", base_model_id, {base_model_id: ""}, ())

    entities = session.scalars(
        select(SemanticEntity).where(
            SemanticEntity.business_domain_id == models[base_model_id].business_domain_id,
            SemanticEntity.status == "ACTIVE",
        )
    ).all()
    entity_by_model = {item.semantic_model_id: item for item in entities}
    if not required.issubset(entity_by_model):
        raise JoinPlanningError("required semantic model is not an active join entity")

    relations = session.scalars(
        select(SemanticJoinRelation).where(
            SemanticJoinRelation.business_domain_id == models[base_model_id].business_domain_id,
            SemanticJoinRelation.status == "PUBLISHED",
        )
    ).all()
    entity_by_id = {item.id: item for item in entities}
    adjacency: dict[str, list[SemanticJoinRelation]] = {}
    for relation in relations:
        if relation.relationship_type != "many_to_one" or relation.fanout_strategy != "safe":
            continue
        adjacency.setdefault(relation.left_entity_id, []).append(relation)
    for edges in adjacency.values():
        edges.sort(key=lambda item: (item.priority, item.id))

    base_entity = entity_by_model[base_model_id]
    selected_relations: list[SemanticJoinRelation] = []
    selected_ids: set[str] = set()
    for target_model_id in sorted(required - {base_model_id}):
        target_entity_id = entity_by_model[target_model_id].id
        queue = deque([(base_entity.id, [])])
        visited = {base_entity.id}
        path: list[SemanticJoinRelation] | None = None
        while queue:
            current_id, current_path = queue.popleft()
            if current_id == target_entity_id:
                path = current_path
                break
            for relation in adjacency.get(current_id, []):
                if relation.right_entity_id in visited:
                    continue
                visited.add(relation.right_entity_id)
                queue.append((relation.right_entity_id, [*current_path, relation]))
        if path is None:
            raise JoinPlanningError(
                f"no published safe join path from {base_model_id} to {target_model_id}"
            )
        for relation in path:
            if relation.id not in selected_ids:
                selected_ids.add(relation.id)
                selected_relations.append(relation)

    model_aliases = {base_model_id: "t0"}
    planned: list[PlannedJoin] = []
    for relation in selected_relations:
        left_entity = entity_by_id[relation.left_entity_id]
        right_entity = entity_by_id[relation.right_entity_id]
        left_model_id = left_entity.semantic_model_id
        right_model_id = right_entity.semantic_model_id
        if left_model_id not in model_aliases:
            raise JoinPlanningError("join path is not connected to the planned base model")
        model_aliases.setdefault(right_model_id, f"t{len(model_aliases)}")
        left_model = session.get(SemanticModel, left_model_id)
        right_model = session.get(SemanticModel, right_model_id)
        if left_model is None or right_model is None:
            raise JoinPlanningError("join relation references a missing semantic model")
        if len(relation.left_keys_json) != len(relation.right_keys_json):
            raise JoinPlanningError("join relation key counts do not match")
        planned.append(
            PlannedJoin(
                relation_id=relation.id,
                left_model_id=left_model_id,
                right_model_id=right_model_id,
                left_table=left_model.physical_table,
                right_table=right_model.physical_table,
                left_keys=tuple(str(item) for item in relation.left_keys_json),
                right_keys=tuple(str(item) for item in relation.right_keys_json),
                join_type=relation.join_type,
                relationship_type=relation.relationship_type,
                fanout_strategy=relation.fanout_strategy,
            )
        )
    return JoinPlan("multi_entity", base_model_id, model_aliases, tuple(planned))
