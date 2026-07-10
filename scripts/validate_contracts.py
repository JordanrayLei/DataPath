"""Validate ChatBI product contracts and their alignment with the Dify workflow."""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate_spec


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DOCUMENT = ROOT / "document"
QUERY_DSL_SCHEMA_PATH = DOCUMENT / "query-dsl-v1.schema.json"
OPENAPI_PATH = DOCUMENT / "chatbi-openapi.yaml"
DIFY_DSL_PATH = DOCUMENT / "dify-chatbi-workflow.zh-CN.dsl.yml"
METRIC_CATALOG_PATH = DOCUMENT / "initial-metric-catalog.md"

EXPECTED_PATHS = {
    "/api/chatbi/context/load",
    "/api/chatbi/metrics/retrieve",
    "/api/chatbi/dsl/validate",
    "/api/chatbi/query/compile",
    "/api/chatbi/query/execute",
    "/api/chatbi/result/profile",
    "/api/chatbi/interpretation/generate",
    "/api/chatbi/reflection/validate",
}

EXPECTED_DIFY_URL_SUFFIXES = {
    "/context/load",
    "/metrics/retrieve",
    "/dsl/validate",
    "/query/compile",
    "/query/execute",
    "/result/profile",
    "/interpretation/generate",
    "/reflection/validate",
}

REQUIRED_DIFY_SAFETY_NODES = {
    "context_gate",
    "context_error_end",
    "execute_parse",
    "execute_gate",
    "execute_failed_end",
    "profile_gate",
    "profile_failed_end",
    "interpret_http",
    "interpret_parse",
    "revision_reflection_http",
    "revision_reflection_parse",
    "revision_reflection_gate",
    "revision_data_only_template",
    "revision_data_only_end",
}

REQUIRED_DIFY_SAFETY_EDGES = {
    ("context_parse", "context_gate", "source"),
    ("context_gate", "preprocess_llm", "case_ok"),
    ("context_gate", "context_error_end", "false"),
    ("execute_http", "execute_parse", "source"),
    ("execute_parse", "execute_gate", "source"),
    ("execute_gate", "profile_http", "case_succeeded"),
    ("execute_gate", "execute_failed_end", "false"),
    ("profile_parse", "profile_gate", "source"),
    ("profile_gate", "interpret_http", "case_ok"),
    ("profile_gate", "profile_failed_end", "false"),
    ("interpret_http", "interpret_parse", "source"),
    ("interpret_parse", "reflection_http", "source"),
    ("revision_llm", "revision_reflection_http", "source"),
    ("revision_reflection_http", "revision_reflection_parse", "source"),
    ("revision_reflection_parse", "revision_reflection_gate", "source"),
    ("revision_reflection_gate", "revision_template", "case_pass"),
    ("revision_reflection_gate", "revision_data_only_template", "false"),
    ("revision_data_only_template", "revision_data_only_end", "source"),
}

EXPECTED_DIFY_LLM_NODES = {
    "preprocess_llm",
    "disambiguate_llm",
    "dsl_llm",
    "revision_llm",
}

EXPECTED_IMPLEMENTED_PATHS = {
    "/api/chatbi/context/load",
    "/api/chatbi/metrics/retrieve",
    "/api/chatbi/dsl/validate",
    "/api/chatbi/query/compile",
    "/api/chatbi/query/execute",
    "/api/chatbi/result/profile",
    "/api/chatbi/interpretation/generate",
    "/api/chatbi/reflection/validate",
}

OPTIONAL_PUBLIC_ENTRYPOINTS = {
    "/api/chatbi/ask",
    "/api/chatbi/feedback",
    "/api/chatbi/golden-questions/from-feedback/{feedback_id}",
    "/api/chatbi/golden-questions/evaluate",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        value = yaml.safe_load(file)
    if not isinstance(value, dict):
        raise AssertionError(f"{path.name} must contain a YAML object")
    return value


def validate_query_dsl_schema() -> None:
    schema = load_json(QUERY_DSL_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)

    examples = schema.get("examples", [])
    if not examples:
        raise AssertionError("Query DSL schema must contain at least one example")

    validator = Draft202012Validator(schema)
    for index, example in enumerate(examples):
        errors = sorted(validator.iter_errors(example), key=lambda error: list(error.path))
        if errors:
            details = "; ".join(error.message for error in errors)
            raise AssertionError(f"Query DSL example {index} is invalid: {details}")


def validate_openapi() -> None:
    spec = load_yaml(OPENAPI_PATH)
    if spec.get("components", {}).get("schemas", {}).get("QueryDsl") != {
        "$ref": "./query-dsl-v1.schema.json"
    }:
        raise AssertionError("OpenAPI QueryDsl must reference query-dsl-v1.schema.json")

    # openapi-spec-validator 0.9 does not resolve relative file references on
    # Windows reliably. Validate an in-memory bundle while keeping the source
    # contract modular and portable.
    bundled_spec = deepcopy(spec)
    bundled_query_schema = load_json(QUERY_DSL_SCHEMA_PATH)
    bundled_query_schema.pop("$schema", None)
    bundled_query_schema.pop("$id", None)

    def rewrite_local_refs(value: object) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                value["$ref"] = ref.replace(
                    "#/$defs/", "#/components/schemas/QueryDsl/$defs/", 1
                )
            for child in value.values():
                rewrite_local_refs(child)
        elif isinstance(value, list):
            for child in value:
                rewrite_local_refs(child)

    rewrite_local_refs(bundled_query_schema)
    bundled_spec["components"]["schemas"]["QueryDsl"] = bundled_query_schema
    validate_spec(bundled_spec)

    paths = set(spec.get("paths", {}))
    if paths != EXPECTED_PATHS:
        missing = sorted(EXPECTED_PATHS - paths)
        extra = sorted(paths - EXPECTED_PATHS)
        raise AssertionError(f"OpenAPI path mismatch; missing={missing}, extra={extra}")

    for path in EXPECTED_PATHS:
        operation = spec["paths"][path].get("post")
        if not isinstance(operation, dict):
            raise AssertionError(f"{path} must define POST")
        if not operation.get("operationId"):
            raise AssertionError(f"{path} must define operationId")


def validate_dify_endpoint_alignment() -> None:
    dsl = load_yaml(DIFY_DSL_PATH)
    nodes = dsl.get("workflow", {}).get("graph", {}).get("nodes", [])
    urls: set[str] = set()

    for node in nodes:
        data = node.get("data", {})
        if data.get("type") != "http-request":
            continue
        url = data.get("url")
        if isinstance(url, str):
            urls.add(url)

    suffixes = {
        url.split("CHATBI_API_BASE_URL#}}", maxsplit=1)[-1]
        for url in urls
        if "CHATBI_API_BASE_URL" in url
    }
    if suffixes != EXPECTED_DIFY_URL_SUFFIXES:
        missing = sorted(EXPECTED_DIFY_URL_SUFFIXES - suffixes)
        extra = sorted(suffixes - EXPECTED_DIFY_URL_SUFFIXES)
        raise AssertionError(f"Dify endpoint mismatch; missing={missing}, extra={extra}")


def validate_dify_safety_flow() -> None:
    dsl = load_yaml(DIFY_DSL_PATH)
    graph = dsl.get("workflow", {}).get("graph", {})
    nodes = graph.get("nodes", [])
    node_by_id = {node.get("id"): node for node in nodes}
    if len(node_by_id) != len(nodes):
        raise AssertionError("Dify node IDs must be unique")
    missing_nodes = sorted(REQUIRED_DIFY_SAFETY_NODES - set(node_by_id))
    if missing_nodes:
        raise AssertionError(f"Dify safety nodes missing: {missing_nodes}")

    edges = {
        (edge.get("source"), edge.get("target"), str(edge.get("sourceHandle")))
        for edge in graph.get("edges", [])
    }
    if len(edges) != len(graph.get("edges", [])):
        raise AssertionError("Dify edges must be unique")
    unknown_edge_nodes = sorted(
        {
            node_id
            for source, target, _ in edges
            for node_id in (source, target)
            if node_id not in node_by_id
        }
    )
    if unknown_edge_nodes:
        raise AssertionError(f"Dify edges reference unknown nodes: {unknown_edge_nodes}")
    missing_edges = sorted(REQUIRED_DIFY_SAFETY_EDGES - edges)
    if missing_edges:
        raise AssertionError(f"Dify safety edges missing: {missing_edges}")

    forbidden_edges = {
        ("context_parse", "preprocess_llm"),
        ("execute_http", "profile_http"),
        ("profile_parse", "interpret_http"),
        ("revision_llm", "revision_template"),
    }
    actual_pairs = {(source, target) for source, target, _ in edges}
    present_forbidden = sorted(forbidden_edges & actual_pairs)
    if present_forbidden:
        raise AssertionError(f"Dify unsafe bypass edges remain: {present_forbidden}")

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
    for source, target, _ in edges:
        adjacency[source].add(target)
    reachable = {"start"}
    pending = ["start"]
    while pending:
        source = pending.pop()
        for target in adjacency[source] - reachable:
            reachable.add(target)
            pending.append(target)
    unreachable = sorted(set(node_by_id) - reachable)
    if unreachable:
        raise AssertionError(f"Dify graph contains unreachable nodes: {unreachable}")

    for node in nodes:
        node_id = node["id"]
        node_type = node.get("data", {}).get("type")
        if node_type == "end" and adjacency[node_id]:
            raise AssertionError(f"Dify end node has outgoing edges: {node_id}")
        if node_type not in {"end"} and not adjacency[node_id]:
            raise AssertionError(f"Dify non-end node has no outgoing edge: {node_id}")
        if node_type == "code":
            try:
                compile(str(node["data"].get("code", "")), f"dify:{node_id}", "exec")
            except SyntaxError as error:
                raise AssertionError(f"Dify code node is invalid: {node_id}: {error}") from error

    serialized_graph = yaml.safe_dump(graph, allow_unicode=True)
    referenced_node_ids = set(re.findall(r"\{\{#([A-Za-z0-9_-]+)\.", serialized_graph))
    unknown_references = sorted(referenced_node_ids - set(node_by_id) - {"env", "sys"})
    if unknown_references:
        raise AssertionError(f"Dify templates reference unknown nodes: {unknown_references}")

    http_nodes = [node for node in nodes if node.get("data", {}).get("type") == "http-request"]
    for node in http_nodes:
        headers = str(node["data"].get("headers", ""))
        if "X-Request-ID: {{#sys.workflow_run_id#}}" not in headers:
            raise AssertionError(f"{node['id']} does not propagate X-Request-ID")
        if "X-Trace-ID: {{#sys.workflow_run_id#}}" not in headers:
            raise AssertionError(f"{node['id']} does not propagate X-Trace-ID")

    compile_parse = node_by_id["compile_parse"]["data"]
    if "execution_token" not in compile_parse.get("outputs", {}):
        raise AssertionError("compile_parse must expose execution_token")
    execute_body = str(node_by_id["execute_http"]["data"].get("body", {}).get("data", ""))
    if "compile_parse.execution_token" not in execute_body:
        raise AssertionError("execute_http must send the signed execution_token")
    if "compiled_query" in execute_body:
        raise AssertionError("execute_http must not send compiled_query")

    interpret_body = str(node_by_id["interpret_http"]["data"].get("body", {}).get("data", ""))
    if "profile_parse.profile_json" not in interpret_body:
        raise AssertionError("interpret_http must send the profiled evidence")
    reflection_body = str(node_by_id["reflection_http"]["data"].get("body", {}).get("data", ""))
    if "interpret_parse.interpretation_json" not in reflection_body:
        raise AssertionError("reflection_http must validate the deterministic interpretation")

    revision_body = str(
        node_by_id["revision_reflection_http"]["data"].get("body", {}).get("data", "")
    )
    if "revision_llm.structured_output" not in revision_body:
        raise AssertionError("second Reflection must validate the revised interpretation")

    for node_id in EXPECTED_DIFY_LLM_NODES:
        model = node_by_id[node_id]["data"].get("model", {})
        if model.get("provider") != "langgenius/deepseek/deepseek":
            raise AssertionError(f"{node_id} must use the Dify DeepSeek provider")
        if model.get("name") != "deepseek-chat":
            raise AssertionError(f"{node_id} must use deepseek-chat")


def validate_metric_catalog() -> None:
    text = METRIC_CATALOG_PATH.read_text(encoding="utf-8")
    metric_ids = re.findall(r"^#### `(?P<id>M_[A-Z0-9_]+)`", text, flags=re.MULTILINE)
    unique_ids = set(metric_ids)

    if len(metric_ids) != len(unique_ids):
        duplicates = sorted({item for item in metric_ids if metric_ids.count(item) > 1})
        raise AssertionError(f"Duplicate detailed metric definitions: {duplicates}")
    if len(unique_ids) != 24:
        raise AssertionError(f"Expected 24 detailed metrics, found {len(unique_ids)}")

    invalid_ids = sorted(
        metric_id
        for metric_id in unique_ids
        if not re.fullmatch(r"M_[A-Z0-9_]{2,100}", metric_id)
    )
    if invalid_ids:
        raise AssertionError(f"Invalid metric IDs: {invalid_ids}")


def validate_fastapi_routes() -> None:
    from app.main import app

    implemented = {
        path
        for path, operations in app.openapi().get("paths", {}).items()
        if path.startswith("/api/chatbi/") and "post" in operations
    }
    allowed = EXPECTED_IMPLEMENTED_PATHS | OPTIONAL_PUBLIC_ENTRYPOINTS
    if not EXPECTED_IMPLEMENTED_PATHS.issubset(implemented) or not implemented.issubset(allowed):
        missing = sorted(EXPECTED_IMPLEMENTED_PATHS - implemented)
        extra = sorted(implemented - allowed)
        raise AssertionError(f"FastAPI route mismatch; missing={missing}, unexpected_extra={extra}")


def main() -> None:
    checks = [
        ("Query DSL JSON Schema and examples", validate_query_dsl_schema),
        ("OpenAPI 3.1 and eight POST paths", validate_openapi),
        ("Dify HTTP endpoint alignment", validate_dify_endpoint_alignment),
        ("Dify fail-closed safety flow", validate_dify_safety_flow),
        ("24 unique metric definitions", validate_metric_catalog),
        ("eight implemented FastAPI ChatBI routes", validate_fastapi_routes),
    ]

    for label, check in checks:
        check()
        print(f"PASS: {label}")


if __name__ == "__main__":
    main()
