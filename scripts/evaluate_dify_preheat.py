"""Evaluate the clean preheated Development split through the published Dify workflow.

This evaluator deliberately never resolves a human-input pause. A clarification is
recorded as the first-query outcome, then cancelled only to release Dify resources.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import httpx
from sqlalchemy import func, select

from app.db.models import QueryRun, ReflectionValidation, UserFeedback
from app.db.session import SessionLocal
from app.services.access_policy import issue_demo_identity_token
from scripts.zero_to_one_evaluation_utils import (
    build_report,
    checksum,
    evaluate_body,
    normalized_rows,
    percentile,
    semantic_assets_sha256,
    product_code_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "evaluation" / "production" / "frontend_closure_v1"
REPORTS = ROOT / "reports" / "dify-preheat"
LOCAL_ENV = ROOT / ".env.preheat.local"
PREHEAT_PACKAGE = ROOT / "data" / "semantic_bootstrap" / "production_ai_preheat_v1.json"
CAPABILITY_PROFILES = DATA / "capability_profiles"
SPLIT = "development"
EVALUATION_DOMAIN = "production_benchmark"
END_RESULT_KEYS = (
    "final_result",
    "revised_result",
    "data_only_result",
    "revision_data_only_result",
)
TRANSIENT_WORKFLOW_ERROR_MARKERS = (
    "chunkedencodingerror",
    "response ended prematurely",
    "connection reset",
    "connection aborted",
    "remote protocol error",
    "read timeout",
    "connect timeout",
    "temporarily unavailable",
    "service unavailable",
    "too many requests",
    "reached maximum retries",
    "error: operation not permitted",
)
RETRYABLE_HTTP_STATUSES = {429, 502, 503, 504}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_failed_cases(
    cases: list[dict[str, Any]],
    baseline_report_path: Path | None,
    category_names: list[str],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if baseline_report_path is None:
        if category_names:
            raise RuntimeError("--case-categories requires --baseline-failures-report")
        return cases, None
    if not baseline_report_path.is_file():
        raise RuntimeError(f"baseline failures report does not exist: {baseline_report_path}")
    baseline = json.loads(baseline_report_path.read_text(encoding="utf-8"))
    if baseline.get("split") != SPLIT:
        raise RuntimeError("baseline failures report split mismatch")
    baseline_golden_sha256 = (baseline.get("provenance") or {}).get(
        "golden_sha256"
    ) or baseline.get("golden_sha256")
    if baseline_golden_sha256 != manifest[f"{SPLIT}_sha256"]:
        raise RuntimeError("baseline failures report does not match the sealed Development input")
    baseline_cases = baseline.get("cases") or baseline.get("results") or []
    failed_ids = {
        str(item["case_id"])
        for item in baseline_cases
        if isinstance(item, dict) and item.get("case_id") and not item.get("passed", False)
    }
    known_categories = {str(case.get("category")) for case in cases}
    categories = sorted(set(category_names))
    unknown = sorted(set(categories) - known_categories)
    if unknown:
        raise RuntimeError(f"unknown case categories: {unknown}")
    selected = [
        case
        for case in cases
        if case["case_id"] in failed_ids
        and (not categories or str(case.get("category")) in categories)
    ]
    selected_ids = [str(case["case_id"]) for case in selected]
    if not selected:
        raise RuntimeError("failed-case selection is empty")
    selection = {
        "mode": "baseline_failures",
        "baseline_report": str(baseline_report_path.resolve()),
        "baseline_report_sha256": file_sha256(baseline_report_path),
        "categories": categories,
        "baseline_failed_case_count": len(failed_ids),
        "selected_case_count": len(selected_ids),
        "selected_case_ids_sha256": stable_json_sha256(selected_ids),
    }
    selection["selection_sha256"] = stable_json_sha256(selection)
    return selected, selection


def load_capability_profile(name: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    if not name:
        return None
    if not all(character.isalnum() or character in {"-", "_"} for character in name):
        raise RuntimeError("capability profile may contain only letters, digits, '-' and '_'")
    path = CAPABILITY_PROFILES / f"{name}.json"
    if not path.exists():
        raise RuntimeError(f"capability profile does not exist: {path}")
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("profile_id") != name or profile.get("schema_version") != 1:
        raise RuntimeError("invalid capability profile identity or schema version")
    if profile.get("base_split") != SPLIT:
        raise RuntimeError("capability profile split mismatch")
    if profile.get("base_split_sha256") != manifest[f"{SPLIT}_sha256"]:
        raise RuntimeError("capability profile does not match the sealed Development input")
    package = profile["capability_package"]
    package_path = ROOT / package["path"]
    if not package_path.is_file() or file_sha256(package_path) != package["sha256"]:
        raise RuntimeError("capability package provenance mismatch")
    profile["profile_sha256"] = file_sha256(path)
    return profile


def _matches_capability(case: dict[str, Any], profile: dict[str, Any]) -> bool:
    eligibility = profile["eligibility"]
    metric_ids = case.get("metric_ids") or []
    supported_metrics = set(profile["oracle"]["metrics"])
    return bool(
        case.get("expected_status") == eligibility["original_expected_status"]
        and case.get("category") == eligibility["category"]
        and case.get("sql_skeleton_id") == eligibility["sql_skeleton_id"]
        and len(metric_ids) == eligibility["metric_count"]
        and metric_ids[0] in supported_metrics
        and eligibility["question_must_contain"] in case.get("query", "")
        and (not eligibility["dimensions_must_be_empty"] or not case.get("dimension_ids"))
        and (not eligibility["filters_must_be_empty"] or not case.get("filters"))
    )


def apply_capability_profile(
    cases: list[dict[str, Any]], profile: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if profile is None:
        return cases, {}
    rewritten = copy.deepcopy(cases)
    counts: Counter[str] = Counter()
    for case in rewritten:
        if not _matches_capability(case, profile):
            continue
        metric_id = case["metric_ids"][0]
        oracle = profile["oracle"]["metrics"][metric_id]
        case["expected_status"] = "SUCCESS"
        case["must_not_compile"] = False
        case["must_not_execute"] = False
        case["expected_result"] = {
            "row_count": 1,
            "result_checksum_sha256": oracle["result_checksum_sha256"],
            "total_value": oracle["value"],
            "top_dimension": None,
            "top_value": oracle["value"],
            "numeric_tolerance": 0.01,
            "dimension_id": None,
        }
        case["expectation_overlay"] = profile["profile_id"]
        counts[metric_id] += 1
    eligibility = profile["eligibility"]
    if sum(counts.values()) != eligibility["expected_case_count"]:
        raise RuntimeError(f"capability profile matched an unexpected case count: {dict(counts)}")
    expected_per_metric = eligibility["expected_cases_per_metric"]
    if set(counts) != set(profile["oracle"]["metrics"]) or any(
        count != expected_per_metric for count in counts.values()
    ):
        raise RuntimeError(f"capability profile metric distribution mismatch: {dict(counts)}")
    return rewritten, dict(sorted(counts.items()))


def load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def clean_state_counts() -> dict[str, int]:
    from app.db.models import GoldenQuestion, MetricAlias, MetricSemanticProfile

    package = json.loads(PREHEAT_PACKAGE.read_text(encoding="utf-8"))
    metric_ids = list(package["metrics"])
    with SessionLocal() as session:
        return {
            "query_runs": session.scalar(select(func.count()).select_from(QueryRun)) or 0,
            "feedback": session.scalar(select(func.count()).select_from(UserFeedback)) or 0,
            "golden_questions": session.scalar(select(func.count()).select_from(GoldenQuestion)) or 0,
            "aliases": session.scalar(
                select(func.count()).select_from(MetricAlias).where(MetricAlias.metric_id.in_(metric_ids))
            ) or 0,
            "semantic_profiles": session.scalar(
                select(func.count())
                .select_from(MetricSemanticProfile)
                .where(MetricSemanticProfile.metric_id.in_(metric_ids))
            ) or 0,
        }


def verify_protocol(
    manifest: dict[str, Any],
    allow_existing_runs: bool,
    capability_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = DATA / f"{SPLIT}.json"
    if file_sha256(path) != manifest[f"{SPLIT}_sha256"]:
        raise RuntimeError("sealed Development input changed")
    counts = clean_state_counts()
    if counts["feedback"] or counts["golden_questions"]:
        raise RuntimeError(f"historical closure data is present: {counts}")
    if not allow_existing_runs and counts["query_runs"]:
        raise RuntimeError(
            "QueryRun is not empty; use the existing matching checkpoint or reset the clean preheat state"
        )
    if counts["aliases"] != 54 or counts["semantic_profiles"] != 9:
        raise RuntimeError(f"preheat asset count mismatch: {counts}")
    if capability_profile:
        from app.db.models import Metric, MetricAlias, MetricSemanticProfile

        metric_ids = capability_profile["capability_package"]["required_published_metric_ids"]
        with SessionLocal() as session:
            metrics = {metric_id: session.get(Metric, metric_id) for metric_id in metric_ids}
            capability = {
                "statuses": {
                    metric_id: (metric.status if metric else None)
                    for metric_id, metric in metrics.items()
                },
                "aliases": session.scalar(
                    select(func.count()).select_from(MetricAlias).where(MetricAlias.metric_id.in_(metric_ids))
                ) or 0,
                "semantic_profiles": session.scalar(
                    select(func.count())
                    .select_from(MetricSemanticProfile)
                    .where(MetricSemanticProfile.metric_id.in_(metric_ids))
                ) or 0,
            }
        if set(capability["statuses"].values()) != {"PUBLISHED"}:
            raise RuntimeError(f"required cross-fact capabilities are not published: {capability}")
        package = capability_profile["capability_package"]
        if (
            capability["aliases"] != package["expected_alias_count"]
            or capability["semantic_profiles"] != package["expected_semantic_profile_count"]
        ):
            raise RuntimeError(f"cross-fact preheat asset count mismatch: {capability}")
        counts["capability"] = capability
    return counts


def iter_sse(response: httpx.Response) -> Iterator[dict[str, Any]]:
    for line in response.iter_lines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def recursive_find(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = recursive_find(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = recursive_find(child, key)
            if found is not None:
                return found
    return None


def json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def node_title(event: dict[str, Any]) -> str:
    data = event.get("data") or {}
    return str(data.get("title") or data.get("node_title") or "")


def node_outputs(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data") or {}
    outputs = data.get("outputs")
    return outputs if isinstance(outputs, dict) else {}


def parse_retrieval(outputs: dict[str, Any]) -> dict[str, Any] | None:
    value = outputs.get("retrieval_json")
    parsed = json_value(value)
    if isinstance(parsed, dict):
        return parsed
    body = json_value(outputs.get("body"))
    return body if isinstance(body, dict) and "mentions" in body else None


def candidate_details(retrieval: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    candidates: list[dict[str, Any]] = []
    for mention in (retrieval or {}).get("mentions", []) or []:
        candidates.extend(mention.get("candidates") or [])
    ids = [str(item["metric_id"]) for item in candidates if item.get("metric_id")]
    sources = sorted(
        {
            str(source)
            for item in candidates
            for source in (item.get("retrieval_sources") or [])
        }
    )
    return ids, sources


def parse_terminal_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    for key in END_RESULT_KEYS:
        parsed = json_value(outputs.get(key))
        if isinstance(parsed, dict):
            return parsed
    if "metric_reject_status" in outputs:
        status = str(outputs.get("metric_reject_status") or "REJECT")
        return {"status": status if status in {"REJECT", "CLARIFY"} else "REJECT"}
    if "dsl_clarify_status" in outputs:
        return {"status": "CLARIFY"}
    if "dsl_deny_status" in outputs:
        return {"status": "REJECT"}
    if "query_blocked_status" in outputs or "approval_status" in outputs:
        return {"status": "BLOCKED"}
    if "execute_status" in outputs:
        return (
            {}
            if str(outputs.get("execute_status")) == "SUCCEEDED"
            else {"status": "BLOCKED"}
        )
    if outputs.get("context_ok") is False:
        return {"status": "BLOCKED"}
    return {}


def result_body_from_database(terminal: dict[str, Any]) -> dict[str, Any]:
    status = str(terminal.get("status") or "UNKNOWN")
    body: dict[str, Any] = {"status": status}
    if status not in {"SUCCESS", "DATA_ONLY"}:
        return body
    query_id = terminal.get("query_id")
    metric_context = terminal.get("metric_context") or {}
    metrics = metric_context.get("metrics") or [] if isinstance(metric_context, dict) else []
    selected_metric_id = metrics[0].get("metric_id") if metrics else None
    with SessionLocal() as session:
        run = session.get(QueryRun, str(query_id)) if query_id else None
        reflection = (
            session.scalar(
                select(ReflectionValidation)
                .where(ReflectionValidation.query_id == str(query_id))
                .order_by(ReflectionValidation.created_at.desc())
                .limit(1)
            )
            if query_id
            else None
        )
    if not selected_metric_id and run:
        versions = run.metric_versions or {}
        selected_metric_id = next(iter(versions), None)
    body.update(
        {
            "status": "SUCCESS" if status in {"SUCCESS", "DATA_ONLY"} else status,
            "selected_metric": {"metric_id": selected_metric_id},
            "compiled": run.dsl_json if run else None,
            "execution": (
                {"status": "SUCCEEDED", "rows": (run.result_json or {}).get("rows", [])}
                if run and run.status == "SUCCEEDED"
                else None
            ),
            "reflection": {"status": reflection.status if reflection else "PASS"},
        }
    )
    return body


def cancel_human_input(
    client: httpx.Client, base_url: str, headers: dict[str, str], token: str, user: str
) -> str | None:
    response = client.post(
        f"{base_url}/form/human_input/{token}",
        headers=headers,
        json={"inputs": {}, "action": "cancel", "user": user},
    )
    if response.status_code != 200:
        return f"HTTP {response.status_code}: {response.text[:200]}"
    return None


def is_retryable_infrastructure_failure(turn_result: dict[str, Any]) -> bool:
    """Retry only transport/provider failures, never a semantic outcome."""

    body = turn_result.get("body") or {}
    status = body.get("status")
    if status == "HTTP_ERROR":
        return body.get("http_status") in RETRYABLE_HTTP_STATUSES
    if status != "WORKFLOW_ERROR":
        return False
    message = str(turn_result.get("stream_error") or "").casefold()
    return bool(message) and any(
        marker in message for marker in TRANSIENT_WORKFLOW_ERROR_MARKERS
    )


def load_workflow_failure_detail(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    workflow_run_id: str,
) -> str | None:
    """Recover an error omitted by Dify's terminal SSE event."""

    try:
        response = client.get(
            f"{base_url}/workflows/run/{workflow_run_id}", headers=headers
        )
    except httpx.TransportError:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if payload.get("status") != "failed":
        return None
    error = payload.get("error")
    return str(error) if error else None


def checkpoint_infrastructure_retry_ids(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    results: list[dict[str, Any]],
) -> tuple[set[str], list[dict[str, Any]]]:
    """Find failed checkpoint entries whose final Dify run failed transiently.

    This deliberately consults Dify's persisted run record. An evaluator result is
    never removed merely because it failed semantically or contains a vague error.
    """

    headers = {"Authorization": f"Bearer {api_key}"}
    retry_ids: set[str] = set()
    evidence: list[dict[str, Any]] = []
    for result in results:
        if result.get("passed") or not result.get("case_id"):
            continue
        workflow_ids = result.get("dify_workflow_run_ids") or []
        workflow_run_id = (
            workflow_ids[-1]
            if workflow_ids
            else result.get("dify_workflow_run_id")
        )
        if not workflow_run_id:
            continue
        error = load_workflow_failure_detail(
            client, base_url, headers, str(workflow_run_id)
        )
        retryable = is_retryable_infrastructure_failure(
            {"body": {"status": "WORKFLOW_ERROR"}, "stream_error": error}
        )
        evidence.append(
            {
                "case_id": str(result["case_id"]),
                "workflow_run_id": str(workflow_run_id),
                "dify_error": error,
                "retryable": retryable,
            }
        )
        if retryable:
            retry_ids.add(str(result["case_id"]))
    return retry_ids, evidence


def run_turn(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    query: str,
    conversation_id: str,
    user: str,
    identity_token: str,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "inputs": {
            "query": query,
            "workspace_id": "demo",
            "biz_domain": "production_benchmark",
            "conversation_id": conversation_id,
            "timezone": "Asia/Shanghai",
            "identity_token": identity_token,
        },
        "response_mode": "streaming",
        "user": user,
    }
    retrieval: dict[str, Any] | None = None
    terminal: dict[str, Any] = {}
    judge_invoked = False
    judge_usage: dict[str, Any] | None = None
    workflow_run_id: str | None = None
    human_input_cancel_error: str | None = None
    stream_error: str | None = None
    workflow_failed = False
    try:
        with client.stream("POST", f"{base_url}/workflows/run", headers=headers, json=payload) as response:
            if response.status_code != 200:
                return {
                    "body": {"status": "HTTP_ERROR", "http_status": response.status_code},
                    "retrieval": None,
                    "judge_invoked": False,
                    "stream_error": response.read().decode(errors="replace")[:500],
                }
            for event in iter_sse(response):
                workflow_run_id = workflow_run_id or recursive_find(event, "workflow_run_id")
                event_name = event.get("event")
                title = node_title(event)
                outputs = node_outputs(event)
                if title in {"指标检索", "解析检索决策"}:
                    retrieval = parse_retrieval(outputs) or retrieval
                if title == "DeepSeek 指标裁判":
                    judge_invoked = True
                    judge_usage = (event.get("data") or {}).get("metadata")
                if event_name == "human_input_required":
                    form_token = recursive_find(event, "form_token")
                    terminal = {"status": "CLARIFY"}
                    if form_token:
                        human_input_cancel_error = cancel_human_input(
                            client, base_url, headers, str(form_token), user
                        )
                    break
                if event_name == "node_finished" and outputs:
                    parsed = parse_terminal_outputs(outputs)
                    if parsed:
                        terminal = parsed
                if event_name in {"workflow_finished", "error"}:
                    if event_name == "error":
                        stream_error = str((event.get("data") or {}).get("message") or event)
                        workflow_failed = True
                    elif str((event.get("data") or {}).get("status") or "").casefold() == "failed":
                        workflow_failed = True
                    break
    except httpx.TransportError as error:
        stream_error = f"{type(error).__name__}: {error}"
    if workflow_failed and not stream_error and workflow_run_id:
        stream_error = load_workflow_failure_detail(
            client, base_url, headers, str(workflow_run_id)
        )
    if workflow_failed:
        terminal = {}
    body = result_body_from_database(terminal) if terminal else {"status": "WORKFLOW_ERROR"}
    return {
        "body": body,
        "retrieval": retrieval,
        "judge_invoked": judge_invoked,
        "judge_usage": judge_usage,
        "workflow_run_id": workflow_run_id,
        "human_input_cancel_error": human_input_cancel_error,
        "stream_error": stream_error,
    }


def execute_case(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    case: dict[str, Any],
    analyst_token: str,
    restricted_token: str,
    infrastructure_retries: int = 1,
) -> dict[str, Any]:
    started = time.perf_counter()
    turns = case.get("turns") or [case["query"]]
    intermediate_errors: list[dict[str, Any]] = []
    turn_result: dict[str, Any] = {}
    workflow_attempts: list[dict[str, Any]] = []
    identity_token = restricted_token if case["category"] == "permission" else analyst_token
    for turn_index, query in enumerate(turns):
        for attempt_index in range(infrastructure_retries + 1):
            turn_result = run_turn(
                client,
                base_url,
                api_key,
                query,
                f"dify_preheat_{case['case_id']}",
                f"preheat-{case['case_id']}",
                identity_token,
            )
            workflow_attempts.append(
                {
                    "turn": turn_index + 1,
                    "attempt": attempt_index + 1,
                    "status": (turn_result.get("body") or {}).get("status"),
                    "workflow_run_id": turn_result.get("workflow_run_id"),
                    "retryable_infrastructure_failure": is_retryable_infrastructure_failure(
                        turn_result
                    ),
                    "stream_error": turn_result.get("stream_error"),
                }
            )
            if not is_retryable_infrastructure_failure(turn_result):
                break
            if attempt_index < infrastructure_retries:
                time.sleep(min(0.5 * (2**attempt_index), 2.0))
        if turn_index < len(turns) - 1 and turn_result["body"].get("status") != "SUCCESS":
            intermediate_errors.append(
                {
                    "layer": "multi_turn",
                    "expected": "SUCCESS",
                    "observed": turn_result["body"].get("status"),
                    "turn": turn_index + 1,
                }
            )
            break
    latency_ms = (time.perf_counter() - started) * 1000
    body = turn_result.get("body") or {"status": "WORKFLOW_ERROR"}
    result = evaluate_body(case, body, latency_ms)
    result["turn_count"] = len(turns)
    result["compiled"] = body.get("compiled") is not None
    result["executed"] = (body.get("execution") or {}).get("status") == "SUCCEEDED"
    result["repeat_group_id"] = case.get("repeat_group_id")
    result["observed_checksum"] = (
        checksum(normalized_rows(body, case))
        if case["expected_status"] == "SUCCESS" and body.get("status") == "SUCCESS"
        else None
    )
    expected_metric_id = (case.get("metric_ids") or [None])[0]
    selected_metric_id = (body.get("selected_metric") or {}).get("metric_id")
    candidate_metric_ids, retrieval_sources = candidate_details(turn_result.get("retrieval"))
    result.update(
        {
            "expected_metric_id": expected_metric_id,
            "selected_metric_id": selected_metric_id,
            "candidate_metric_ids": candidate_metric_ids,
            "expected_candidate_rank": (
                candidate_metric_ids.index(expected_metric_id) + 1
                if expected_metric_id in candidate_metric_ids
                else None
            ),
            "retrieval_sources": retrieval_sources,
            "dify_workflow_run_id": turn_result.get("workflow_run_id"),
            "dify_workflow_run_ids": [
                item["workflow_run_id"]
                for item in workflow_attempts
                if item.get("workflow_run_id")
            ],
            "infrastructure_retry_count": sum(
                item["attempt"] > 1 for item in workflow_attempts
            ),
            "workflow_attempts": workflow_attempts,
            "deepseek_judge_invoked": bool(turn_result.get("judge_invoked")),
            "deepseek_judge_usage": turn_result.get("judge_usage"),
        }
    )
    if intermediate_errors:
        result["errors"].extend(intermediate_errors)
    if turn_result.get("human_input_cancel_error"):
        result["errors"].append(
            {"layer": "cleanup", "observed": turn_result["human_input_cancel_error"]}
        )
    if turn_result.get("stream_error"):
        result["errors"].append({"layer": "workflow", "observed": turn_result["stream_error"]})
    if case.get("must_not_compile") and result["compiled"]:
        result["errors"].append({"layer": "safety", "expected": "not compiled", "observed": "compiled"})
    if case.get("must_not_execute") and result["executed"]:
        result["errors"].append({"layer": "safety", "expected": "not executed", "observed": "executed"})
    result["passed"] = not result["errors"]
    result["unsafe_executed"] = bool(case.get("must_not_execute") and result["executed"])
    return result


def save_checkpoint(
    path: Path,
    manifest: dict[str, Any],
    results: list[dict[str, Any]],
    capability_profile: dict[str, Any] | None = None,
    case_selection: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preserved: dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        for key in ("checkpoint_infrastructure_retry_events",):
            if key in existing:
                preserved[key] = existing[key]
    payload = {
        "split": SPLIT,
        "phase": "clean_preheat_dify_deepseek",
        "golden_sha256": manifest[f"{SPLIT}_sha256"],
        "product_code_sha256": product_code_sha256(),
        "semantic_assets_scope": EVALUATION_DOMAIN,
        "semantic_assets_sha256": semantic_assets_sha256(EVALUATION_DOMAIN),
        "updated_at": datetime.now(UTC).isoformat(),
        "completed_case_count": len(results),
        "results": results,
        **preserved,
    }
    if capability_profile:
        payload["capability_profile_id"] = capability_profile["profile_id"]
        payload["capability_profile_sha256"] = capability_profile["profile_sha256"]
    if case_selection:
        payload["case_selection_sha256"] = case_selection["selection_sha256"]
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def record_checkpoint_infrastructure_retry_event(
    path: Path,
    retry_ids: set[str],
    evidence: list[dict[str, Any]],
) -> None:
    if not retry_ids:
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("checkpoint_infrastructure_retry_events", []).append(
        {
            "recorded_at": datetime.now(UTC).isoformat(),
            "case_ids": sorted(retry_ids),
            "evidence": [
                item for item in evidence if item.get("case_id") in retry_ids
            ],
        }
    )
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def load_checkpoint(
    path: Path,
    manifest: dict[str, Any],
    capability_profile: dict[str, Any] | None = None,
    case_selection: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "split": SPLIT,
        "phase": "clean_preheat_dify_deepseek",
        "golden_sha256": manifest[f"{SPLIT}_sha256"],
        "product_code_sha256": product_code_sha256(),
        "semantic_assets_scope": EVALUATION_DOMAIN,
        "semantic_assets_sha256": semantic_assets_sha256(EVALUATION_DOMAIN),
    }
    if capability_profile:
        expected["capability_profile_id"] = capability_profile["profile_id"]
        expected["capability_profile_sha256"] = capability_profile["profile_sha256"]
    if case_selection:
        expected["case_selection_sha256"] = case_selection["selection_sha256"]
    if {key: payload.get(key) for key in expected} != expected:
        raise RuntimeError("checkpoint provenance mismatch")
    return payload.get("results") or []


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    first = report["first_query_quality"]
    def percentage(value: float | None) -> str:
        return "不适用" if value is None else f"{value:.2%}"

    return f"""# DataPath 纯预热 Dify/DeepSeek Development 评测

- 用例：{summary['cases']}
- 严格通过：{summary['passed']}（{summary['pass_rate']:.2%}）
- 可回答用例首次直接答对：{first['direct_correct']}/{first['answerable_cases']}（{percentage(first['direct_correct_rate'])}）
- 检索 Top1：{percentage(first['top1_accuracy'])}
- 检索 Recall@3：{percentage(first['recall_at_3'])}
- 危险执行：{summary['unsafe_execution_count']}
- Dify 工作流运行尝试：{report['dify_evidence']['workflow_run_count']} 次（基础设施自动重试 {report['dify_evidence'].get('infrastructure_retry_count', 0)} 次）
- DeepSeek 裁判触发：{report['dify_evidence']['judge_invocation_count']} 次
- P50 / P95：{summary['latency_p50_ms']} / {summary['latency_p95_ms']} ms

本轮使用定义预热资产；Feedback、Golden Question 均为 0。若报告包含能力配置，原始测试集保持封存不变，只对已发布且经 Oracle 验证的支持形态应用独立期望覆盖层。若报告包含用例筛选，筛选对象仅为指定基线报告中未通过且类别匹配的用例，基线文件与用例 ID 均有哈希绑定。
出现人工澄清时不选择候选，只记录首次查询失败并取消挂起流程。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-new-cases", type=int)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--infrastructure-retries",
        type=int,
        default=1,
        help="Retry each turn only for recognized transient transport/provider failures.",
    )
    parser.add_argument(
        "--run-label",
        default="",
        help="Store an independent checkpoint/report under reports/dify-preheat/<label>.",
    )
    parser.add_argument(
        "--capability-profile",
        default="",
        help="Apply a provenance-checked expectation overlay without editing the sealed test set.",
    )
    parser.add_argument(
        "--prioritize-capability-cases",
        action="store_true",
        help="Evaluate overlaid cases first for a meaningful capability smoke test.",
    )
    parser.add_argument(
        "--baseline-failures-report",
        type=Path,
        help="Evaluate only case IDs that failed in this provenance-checked Development report.",
    )
    parser.add_argument(
        "--case-categories",
        default="",
        help="Comma-separated category allowlist applied to baseline failures.",
    )
    parser.add_argument(
        "--retry-checkpoint-infrastructure-failures",
        action="store_true",
        help=(
            "Requeue only failed checkpoint entries whose persisted Dify run "
            "proves a recognized transient infrastructure failure."
        ),
    )
    args = parser.parse_args()
    load_local_env(LOCAL_ENV)
    base_url = os.environ.get("DIFY_API_BASE_URL", "http://localhost/v1").rstrip("/")
    api_key = os.environ.get("DIFY_API_KEY")
    if not api_key:
        raise RuntimeError("DIFY_API_KEY is required (use ignored .env.preheat.local)")
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    capability_profile = load_capability_profile(args.capability_profile, manifest)
    if args.run_label and not all(
        character.isalnum() or character in {"-", "_"}
        for character in args.run_label
    ):
        raise RuntimeError("run label may contain only letters, digits, '-' and '_'")
    run_reports = REPORTS / args.run_label if args.run_label else REPORTS
    checkpoint_path = run_reports / "checkpoints" / f"{SPLIT}.json"
    sealed_cases = json.loads((DATA / f"{SPLIT}.json").read_text(encoding="utf-8"))
    cases, overlay_counts = apply_capability_profile(sealed_cases, capability_profile)
    category_names = [item.strip() for item in args.case_categories.split(",") if item.strip()]
    cases, case_selection = select_failed_cases(
        cases, args.baseline_failures_report, category_names, manifest
    )
    results = load_checkpoint(
        checkpoint_path, manifest, capability_profile, case_selection
    )
    checkpoint_was_nonempty = bool(results)
    selected_case_ids = {case["case_id"] for case in cases}
    if any(result.get("case_id") not in selected_case_ids for result in results):
        raise RuntimeError("checkpoint contains cases outside the bound failed-case selection")
    if args.retry_checkpoint_infrastructure_failures:
        with httpx.Client(timeout=30.0, trust_env=False) as detail_client:
            retry_ids, retry_evidence = checkpoint_infrastructure_retry_ids(
                detail_client, base_url, api_key, results
            )
        results = [result for result in results if result.get("case_id") not in retry_ids]
        record_checkpoint_infrastructure_retry_event(
            checkpoint_path, retry_ids, retry_evidence
        )
        print(
            json.dumps(
                {
                    "checkpoint_infrastructure_retry_case_ids": sorted(retry_ids),
                    "inspected_failed_checkpoint_entries": retry_evidence,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    counts = verify_protocol(
        manifest,
        allow_existing_runs=checkpoint_was_nonempty,
        capability_profile=capability_profile,
    )
    completed = {result["case_id"] for result in results}
    remaining = [case for case in cases if case["case_id"] not in completed]
    if args.prioritize_capability_cases:
        if not capability_profile:
            raise RuntimeError("--prioritize-capability-cases requires --capability-profile")
        remaining.sort(key=lambda case: not bool(case.get("expectation_overlay")))
    if args.max_new_cases is not None:
        remaining = remaining[: args.max_new_cases]
    analyst_token = issue_demo_identity_token("production_analyst")
    restricted_token = issue_demo_identity_token("metric_admin")
    timeout = httpx.Timeout(args.timeout, connect=15.0)
    # Local Dify must not inherit a host-wide HTTP proxy; otherwise localhost can
    # be sent to the proxy and appear as an empty 502 before reaching NGINX.
    if args.workers < 1 or args.workers > 10:
        raise RuntimeError("--workers must be between 1 and 10")
    if args.infrastructure_retries < 0 or args.infrastructure_retries > 3:
        raise RuntimeError("--infrastructure-retries must be between 0 and 3")
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        def run_case(case: dict[str, Any]) -> dict[str, Any]:
            return execute_case(
                client,
                base_url,
                api_key,
                case,
                analyst_token,
                restricted_token,
                args.infrastructure_retries,
            )

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            for offset in range(0, len(remaining), args.batch_size):
                batch = remaining[offset : offset + args.batch_size]
                batch_results = list(executor.map(run_case, batch))
                results.extend(batch_results)
                save_checkpoint(
                    checkpoint_path, manifest, results, capability_profile, case_selection
                )
                unsafe_count = sum(item["unsafe_executed"] for item in results)
                print(
                    json.dumps(
                        {
                            "split": SPLIT,
                            "phase": "clean_preheat_dify_deepseek",
                            "completed": len(results),
                            "total": len(cases),
                            "passed_so_far": sum(item["passed"] for item in results),
                            "unsafe_so_far": unsafe_count,
                            "judge_invocations": sum(item["deepseek_judge_invoked"] for item in results),
                            "workers": args.workers,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                if unsafe_count:
                    raise RuntimeError("unsafe execution detected; evaluation stopped at batch boundary")
    if len(results) < len(cases):
        return 2
    report_manifest = {
        **manifest,
        "golden_set_id": manifest["benchmark_id"],
        "snapshot_id": "production-like-production-v1",
        "evidence_class": "clean_preheat_development",
        "claim_restriction": "Development split only; no Regression or Locked Blind claim.",
    }
    report = build_report(
        SPLIT, results, report_manifest, semantic_domain=EVALUATION_DOMAIN
    )
    checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    report["provenance"]["semantic_assets_scope"] = checkpoint_payload[
        "semantic_assets_scope"
    ]
    report["provenance"]["semantic_assets_sha256"] = checkpoint_payload[
        "semantic_assets_sha256"
    ]
    report["benchmark_id"] = manifest["benchmark_id"]
    report["phase"] = "clean_preheat_dify_deepseek"
    report["protocol"] = {
        "historical_bad_cases": 0,
        "historical_feedback": counts["feedback"],
        "historical_golden_questions": counts["golden_questions"],
        "preheat_aliases": counts["aliases"],
        "preheat_positive_examples": 72,
        "preheat_negative_examples": 54,
        "manual_candidate_selection": False,
        "sealed_test_set_modified": False,
    }
    if capability_profile:
        report["capability_profile"] = {
            "profile_id": capability_profile["profile_id"],
            "profile_sha256": capability_profile["profile_sha256"],
            "base_split_sha256": capability_profile["base_split_sha256"],
            "package_sha256": capability_profile["capability_package"]["sha256"],
            "overridden_case_count": sum(overlay_counts.values()),
            "overridden_cases_by_metric": overlay_counts,
            "oracle": capability_profile["oracle"],
            "source_restriction": capability_profile["source_restriction"],
        }
    if case_selection:
        report["case_selection"] = case_selection
    checkpoint_retry_events = checkpoint_payload.get(
        "checkpoint_infrastructure_retry_events", []
    )
    checkpoint_retry_count = sum(
        len(event.get("case_ids") or []) for event in checkpoint_retry_events
    )
    report["dify_evidence"] = {
        "workflow_run_count": sum(
            len(item.get("dify_workflow_run_ids") or ([item["dify_workflow_run_id"]] if item.get("dify_workflow_run_id") else []))
            for item in results
        ) + checkpoint_retry_count,
        "infrastructure_retry_count": sum(
            item.get("infrastructure_retry_count", 0) for item in results
        ) + checkpoint_retry_count,
        "checkpoint_infrastructure_retry_events": checkpoint_retry_events,
        "judge_invocation_count": sum(item.get("deepseek_judge_invoked", False) for item in results),
        "workflow_run_ids_stored": True,
        "api_key_stored": False,
    }
    run_reports.mkdir(parents=True, exist_ok=True)
    report_path = run_reports / f"{SPLIT}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_reports / f"{SPLIT}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["passed"] == report["summary"]["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
