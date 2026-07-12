"""Evaluate the product-facing ChatBI entrypoint and write reports.

By default this script runs in-process with FastAPI TestClient, so it can be
used before starting a live server. Pass --base-url to evaluate a running
deployment, for example http://127.0.0.1:8000.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from time import perf_counter

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


@dataclass(frozen=True)
class EvalCase:
    name: str
    category: str
    query: str
    domain: str
    expected_status: str
    workspace_id: str = "demo"
    expected_chart: str | None = None
    expected_rows: int | None = None
    expected_metric: str | None = None
    expected_intent: str | None = None
    expected_dimension: str | None = None
    expected_candidates: frozenset[str] = frozenset()
    must_not_compile: bool = False


EVALUATION_CASES_PATH = PROJECT_ROOT / "data" / "evaluation" / "olist_business_cases.json"


def load_evaluation_cases() -> list[EvalCase]:
    definitions = json.loads(EVALUATION_CASES_PATH.read_text(encoding="utf-8"))
    return [
        EvalCase(
            **{
                **item,
                "expected_candidates": frozenset(item.get("expected_candidates", [])),
            }
        )
        for item in definitions
    ]


CASES = load_evaluation_cases()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Live server base URL, e.g. http://127.0.0.1:8000")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports"),
        help="Directory for JSON and Markdown reports. Default: reports",
    )
    parser.add_argument(
        "--report-name",
        default="chatbi-entrypoint-evaluation-latest",
        help="Report base filename without extension.",
    )
    parser.add_argument("--no-report", action="store_true", help="Print only; do not write report files.")
    return parser.parse_args()


def post_case_with_test_client(case: EvalCase) -> dict[str, Any]:
    warnings.filterwarnings(
        "ignore",
        message="Using `httpx` with `starlette.testclient` is deprecated.*",
        category=Warning,
    )
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/api/chatbi/ask",
            json={
                "query": case.query,
                "biz_domain": case.domain,
                "workspace_id": case.workspace_id,
                "conversation_id": f"eval_{case.name}_{uuid.uuid4().hex}",
                "timezone": "Asia/Shanghai",
            },
        )
        response.raise_for_status()
        return response.json()


def post_case_with_http(base_url: str, case: EvalCase) -> dict[str, Any]:
    with httpx.Client(timeout=60, trust_env=False) as client:
        response = client.post(
            f"{base_url.rstrip('/')}/api/chatbi/ask",
            json={
                "query": case.query,
                "biz_domain": case.domain,
                "workspace_id": case.workspace_id,
                "conversation_id": f"eval_{case.name}_{uuid.uuid4().hex}",
                "timezone": "Asia/Shanghai",
            },
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.is_error:
            return {
                **body,
                "status": body.get("status") or "HTTP_ERROR",
                "message": body.get("message") or f"HTTP {response.status_code}",
                "http_status": response.status_code,
            }
        return body


def assert_case(case: EvalCase, body: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if body.get("status") != case.expected_status:
        errors.append(f"status expected {case.expected_status}, got {body.get('status')}")
    if case.expected_metric and (body.get("selected_metric") or {}).get("metric_id") != case.expected_metric:
        errors.append(
            "metric expected "
            f"{case.expected_metric}, got {(body.get('selected_metric') or {}).get('metric_id')}"
        )
    if case.expected_chart and (body.get("profile") or {}).get("chart_spec", {}).get("type") != case.expected_chart:
        errors.append(
            "chart expected "
            f"{case.expected_chart}, got {(body.get('profile') or {}).get('chart_spec', {}).get('type')}"
        )
    if case.expected_rows is not None and (body.get("execution") or {}).get("row_count") != case.expected_rows:
        errors.append(
            f"row_count expected {case.expected_rows}, got {(body.get('execution') or {}).get('row_count')}"
        )
    if case.expected_intent and (body.get("dsl") or {}).get("intent") != case.expected_intent:
        errors.append(
            f"dsl intent expected {case.expected_intent}, got {(body.get('dsl') or {}).get('intent')}"
        )
    if case.expected_dimension:
        dimensions = {
            item.get("dimension_id")
            for item in (body.get("dsl", {}) or {}).get("dimensions", [])
        }
        if case.expected_dimension not in dimensions:
            errors.append(f"dimension expected {case.expected_dimension}, got {sorted(dimensions)}")
    if case.expected_candidates:
        candidates = {
            item.get("metric_id")
            for mention in (body.get("retrieval", {}) or {}).get("mentions", [])
            for item in mention.get("candidates", [])
        }
        if not case.expected_candidates.issubset(candidates):
            errors.append(
                f"candidate set expected {sorted(case.expected_candidates)}, got {sorted(candidates)}"
            )
    if case.expected_status == "SUCCESS":
        if (body.get("reflection") or {}).get("status") != "PASS":
            errors.append("reflection did not PASS")
        if not (body.get("profile") or {}).get("evidence"):
            errors.append("missing evidence")
        if "SELECT " in str(body).upper():
            errors.append("response leaked raw SQL")
    if case.must_not_compile and body.get("compiled") is not None:
        errors.append("this case should not compile a query")
    return errors


def case_result(case: EvalCase, body: dict[str, Any], latency_ms: int) -> dict[str, Any]:
    errors = assert_case(case, body)
    return {
        "name": case.name,
        "category": case.category,
        "query": case.query,
        "domain": case.domain,
        "workspace_id": case.workspace_id,
        "passed": not errors,
        "errors": errors,
        "latency_ms": latency_ms,
        "status": body.get("status"),
        "message": body.get("message"),
        "query_id": (body.get("compiled") or {}).get("query_id"),
        "selected_metric_id": (body.get("selected_metric") or {}).get("metric_id"),
        "dsl_intent": (body.get("dsl") or {}).get("intent"),
        "chart_type": (body.get("profile") or {}).get("chart_spec", {}).get("type"),
        "row_count": (body.get("execution") or {}).get("row_count"),
        "evidence_count": len((body.get("profile") or {}).get("evidence", []) or []),
        "reflection_status": (body.get("reflection") or {}).get("status"),
        "compiled": body.get("compiled") is not None,
        "raw_sql_leaked": "SELECT " in str(body).upper(),
    }


def unauthorized_body() -> dict[str, Any]:
    return {
        "workspace_id": "demo",
        "conversation_id": "auth_eval",
        "identity_token": "demo-server-issued-token",
    }


def feedback_body(query_id: str) -> dict[str, Any]:
    return {
        "workspace_id": "demo",
        "conversation_id": "eval_feedback",
        "query_id": query_id,
        "user_query": "2017年每月Olist销售额趋势",
        "feedback_type": "INTERPRETATION_UNTRUSTED",
        "severity": "MEDIUM",
        "message": "测评提交：希望该回答补充异常月份的业务背景。",
        "expected_behavior": "进入 Badcase 回归集候选，后续由产品确认。",
        "page_context": {"source": "evaluate_chatbi_entrypoint"},
    }


def check_internal_auth_with_test_client() -> dict[str, Any]:
    warnings.filterwarnings(
        "ignore",
        message="Using `httpx` with `starlette.testclient` is deprecated.*",
        category=Warning,
    )
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post("/api/chatbi/context/load", json=unauthorized_body())
        return {"status_code": response.status_code, "body": response.json()}


def check_metric_catalog_with_test_client() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        listed = client.get(
            "/api/chatbi/metrics/catalog",
            params={"workspace_id": "demo", "domain": "sales", "limit": 20},
        )
        detail = client.get(
            "/api/chatbi/metrics/catalog/M_OLIST_ITEM_REVENUE",
            params={"workspace_id": "demo"},
        )
        return {
            "listed": {"status_code": listed.status_code, "body": listed.json()},
            "detail": {"status_code": detail.status_code, "body": detail.json()},
        }


def check_multiturn_context_with_test_client() -> list[dict[str, Any]]:
    from fastapi.testclient import TestClient

    conversation_id = f"eval_multiturn_{uuid.uuid4().hex}"
    queries = [
        "2017年每月Olist销售额趋势",
        "按商品品类拆解",
        "只看最近三个月",
        "换成Olist订单量",
        "再看卖家州",
    ]
    with TestClient(app) as client:
        return [
            client.post(
                "/api/chatbi/ask",
                json={
                    "query": query,
                    "biz_domain": "auto",
                    "workspace_id": "demo",
                    "conversation_id": conversation_id,
                    "timezone": "Asia/Shanghai",
                },
            ).json()
            for query in queries
        ]


def check_feedback_submission_with_test_client(query_id: str) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post("/api/chatbi/feedback", json=feedback_body(query_id))
        return {"status_code": response.status_code, "body": response.json()}


def check_feedback_board_lifecycle_with_test_client(query_id: str) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        submitted = client.post("/api/chatbi/feedback", json=feedback_body(query_id))
        submitted_body = submitted.json()
        feedback_id = submitted_body.get("feedback_id")
        listed = client.get("/api/chatbi/feedback", params={"workspace_id": "demo", "status": "OPEN"})
        updated = client.patch(
            f"/api/chatbi/feedback/{feedback_id}/status",
            json={"status": "CONFIRMED"},
        ) if feedback_id else None
        return {
            "submitted": {"status_code": submitted.status_code, "body": submitted_body},
            "listed": {"status_code": listed.status_code, "body": listed.json()},
            "updated": {
                "status_code": updated.status_code if updated is not None else 0,
                "body": updated.json() if updated is not None else {},
            },
        }


def check_golden_question_lifecycle_with_test_client(query_id: str) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        submitted = client.post("/api/chatbi/feedback", json=feedback_body(query_id))
        submitted_body = submitted.json()
        feedback_id = submitted_body.get("feedback_id")
        confirmed = (
            client.patch(
                f"/api/chatbi/feedback/{feedback_id}/status",
                json={"status": "CONFIRMED"},
            )
            if feedback_id
            else None
        )
        created = (
            client.post(
                f"/api/chatbi/golden-questions/from-feedback/{feedback_id}",
                json={"biz_domain": "sales", "expected_notes": "Evaluation regression gate."},
            )
            if feedback_id
            else None
        )
        created_body = created.json() if created is not None else {}
        golden_id = created_body.get("golden_question", {}).get("golden_id")
        listed = client.get("/api/chatbi/golden-questions", params={"workspace_id": "demo"})
        evaluated = client.post(
            "/api/chatbi/golden-questions/evaluate",
            json={"workspace_id": "demo", "status": "ACTIVE", "limit": 20},
        )
        return {
            "submitted": {"status_code": submitted.status_code, "body": submitted_body},
            "confirmed": {
                "status_code": confirmed.status_code if confirmed is not None else 0,
                "body": confirmed.json() if confirmed is not None else {},
            },
            "created": {
                "status_code": created.status_code if created is not None else 0,
                "body": created_body,
            },
            "listed": {"status_code": listed.status_code, "body": listed.json()},
            "evaluated": {"status_code": evaluated.status_code, "body": evaluated.json()},
            "golden_id": golden_id,
        }


def check_internal_auth_with_http(base_url: str) -> dict[str, Any]:
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.post(
            f"{base_url.rstrip('/')}/api/chatbi/context/load",
            json=unauthorized_body(),
        )
        return {"status_code": response.status_code, "body": response.json()}


def check_metric_catalog_with_http(base_url: str) -> dict[str, Any]:
    with httpx.Client(timeout=30, trust_env=False) as client:
        listed = client.get(
            f"{base_url.rstrip('/')}/api/chatbi/metrics/catalog",
            params={"workspace_id": "demo", "domain": "sales", "limit": 20},
        )
        detail = client.get(
            f"{base_url.rstrip('/')}/api/chatbi/metrics/catalog/M_OLIST_ITEM_REVENUE",
            params={"workspace_id": "demo"},
        )
        return {
            "listed": {"status_code": listed.status_code, "body": listed.json()},
            "detail": {"status_code": detail.status_code, "body": detail.json()},
        }


def check_multiturn_context_with_http(base_url: str) -> list[dict[str, Any]]:
    conversation_id = f"eval_multiturn_{uuid.uuid4().hex}"
    queries = [
        "2017年每月Olist销售额趋势",
        "按商品品类拆解",
        "只看最近三个月",
        "换成Olist订单量",
        "再看卖家州",
    ]
    with httpx.Client(timeout=60, trust_env=False) as client:
        responses = []
        for query in queries:
            response = client.post(
                f"{base_url.rstrip('/')}/api/chatbi/ask",
                json={
                    "query": query,
                    "biz_domain": "auto",
                    "workspace_id": "demo",
                    "conversation_id": conversation_id,
                    "timezone": "Asia/Shanghai",
                },
            )
            responses.append(response.json())
        return responses


def check_feedback_submission_with_http(base_url: str, query_id: str) -> dict[str, Any]:
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.post(
            f"{base_url.rstrip('/')}/api/chatbi/feedback",
            json=feedback_body(query_id),
        )
        return {"status_code": response.status_code, "body": response.json()}


def check_feedback_board_lifecycle_with_http(base_url: str, query_id: str) -> dict[str, Any]:
    with httpx.Client(timeout=30, trust_env=False) as client:
        submitted = client.post(
            f"{base_url.rstrip('/')}/api/chatbi/feedback",
            json=feedback_body(query_id),
        )
        submitted_body = submitted.json()
        feedback_id = submitted_body.get("feedback_id")
        listed = client.get(
            f"{base_url.rstrip('/')}/api/chatbi/feedback",
            params={"workspace_id": "demo", "status": "OPEN"},
        )
        updated = (
            client.patch(
                f"{base_url.rstrip('/')}/api/chatbi/feedback/{feedback_id}/status",
                json={"status": "CONFIRMED"},
            )
            if feedback_id
            else None
        )
        return {
            "submitted": {"status_code": submitted.status_code, "body": submitted_body},
            "listed": {"status_code": listed.status_code, "body": listed.json()},
            "updated": {
                "status_code": updated.status_code if updated is not None else 0,
                "body": updated.json() if updated is not None else {},
            },
        }


def check_golden_question_lifecycle_with_http(base_url: str, query_id: str) -> dict[str, Any]:
    with httpx.Client(timeout=60, trust_env=False) as client:
        submitted = client.post(
            f"{base_url.rstrip('/')}/api/chatbi/feedback",
            json=feedback_body(query_id),
        )
        submitted_body = submitted.json()
        feedback_id = submitted_body.get("feedback_id")
        confirmed = (
            client.patch(
                f"{base_url.rstrip('/')}/api/chatbi/feedback/{feedback_id}/status",
                json={"status": "CONFIRMED"},
            )
            if feedback_id
            else None
        )
        created = (
            client.post(
                f"{base_url.rstrip('/')}/api/chatbi/golden-questions/from-feedback/{feedback_id}",
                json={"biz_domain": "sales", "expected_notes": "Evaluation regression gate."},
            )
            if feedback_id
            else None
        )
        created_body = created.json() if created is not None else {}
        golden_id = created_body.get("golden_question", {}).get("golden_id")
        listed = client.get(
            f"{base_url.rstrip('/')}/api/chatbi/golden-questions",
            params={"workspace_id": "demo"},
        )
        evaluated = client.post(
            f"{base_url.rstrip('/')}/api/chatbi/golden-questions/evaluate",
            json={"workspace_id": "demo", "status": "ACTIVE", "limit": 20},
        )
        return {
            "submitted": {"status_code": submitted.status_code, "body": submitted_body},
            "confirmed": {
                "status_code": confirmed.status_code if confirmed is not None else 0,
                "body": confirmed.json() if confirmed is not None else {},
            },
            "created": {
                "status_code": created.status_code if created is not None else 0,
                "body": created_body,
            },
            "listed": {"status_code": listed.status_code, "body": listed.json()},
            "evaluated": {"status_code": evaluated.status_code, "body": evaluated.json()},
            "golden_id": golden_id,
        }


def build_gate_results(base_url: str | None, case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    auth_result = check_internal_auth_with_http(base_url) if base_url else check_internal_auth_with_test_client()
    token_guard_passed = (
        auth_result["status_code"] == 401
        and auth_result.get("body", {}).get("code") == "INVALID_SERVICE_TOKEN"
    )
    gates = [
        {
            "name": "internal_service_token_guard",
            "passed": token_guard_passed,
            "detail": (
                "Internal endpoint rejected browser-style unauthenticated request."
                if token_guard_passed
                else f"Unexpected auth response: {auth_result}"
            ),
        }
    ]
    metric_catalog_result = (
        check_metric_catalog_with_http(base_url)
        if base_url
        else check_metric_catalog_with_test_client()
    )
    metric_items = metric_catalog_result["listed"]["body"].get("items", [])
    metric_detail = metric_catalog_result["detail"]["body"].get("metric", {})
    metric_dimensions = {
        item.get("dimension_id")
        for item in metric_detail.get("dimensions", [])
    }
    metric_catalog_passed = (
        metric_catalog_result["listed"]["status_code"] == 200
        and metric_catalog_result["detail"]["status_code"] == 200
        and any(item.get("metric_id") == "M_OLIST_ITEM_REVENUE" for item in metric_items)
        and metric_detail.get("metric_id") == "M_OLIST_ITEM_REVENUE"
        and "SUM(" in metric_detail.get("formula_text", "")
        and "data_warehouse.olist_order_items" in metric_detail.get("lineage", {}).get("tables", [])
        and {"D_DATE", "D_MONTH", "D_OLIST_CATEGORY"}.issubset(metric_dimensions)
    )
    gates.append(
        {
            "name": "metric_catalog_detail",
            "passed": metric_catalog_passed,
            "detail": (
                "Metric catalog listed M_OLIST_ITEM_REVENUE with formula, dimensions, and warehouse lineage."
                if metric_catalog_passed
                else f"Unexpected metric catalog response: {metric_catalog_result}"
            ),
        }
    )
    multiturn = (
        check_multiturn_context_with_http(base_url)
        if base_url
        else check_multiturn_context_with_test_client()
    )
    multiturn_passed = (
        len(multiturn) == 5
        and all(item.get("status") == "SUCCESS" for item in multiturn)
        and (multiturn[1].get("selected_metric") or {}).get("metric_id") == "M_OLIST_ITEM_REVENUE"
        and (multiturn[1].get("dsl") or {}).get("dimensions") == [{"dimension_id": "D_OLIST_CATEGORY"}]
        and (multiturn[2].get("dsl") or {}).get("time_range", {}).get("start") == "2018-07-01"
        and (multiturn[3].get("selected_metric") or {}).get("metric_id")
        == "M_OLIST_ORDER_COUNT"
        and (multiturn[4].get("dsl") or {}).get("dimensions")
        == [{"dimension_id": "D_OLIST_SELLER_STATE"}]
    )
    gates.append(
        {
            "name": "multiturn_context_inheritance",
            "passed": multiturn_passed,
            "detail": (
                "Metric, dimension, and time context were inherited and explicitly overridden across five turns."
                if multiturn_passed
                else f"Unexpected multiturn responses: {multiturn}"
            ),
        }
    )
    query_id = next(
        (
            item.get("query_id")
            for item in case_results
            if item.get("name") == "revenue_month_2017" and item.get("query_id")
        ),
        None,
    )
    if query_id:
        feedback_result = (
            check_feedback_submission_with_http(base_url, query_id)
            if base_url
            else check_feedback_submission_with_test_client(query_id)
        )
        feedback_body_result = feedback_result.get("body", {})
        feedback_passed = (
            feedback_result["status_code"] == 200
            and feedback_body_result.get("status") == "ACCEPTED"
            and feedback_body_result.get("regression_candidate") is True
            and feedback_body_result.get("query_id") == query_id
        )
        gates.append(
            {
                "name": "badcase_feedback_submission",
                "passed": feedback_passed,
                "detail": (
                    f"Feedback accepted as regression candidate for query_id={query_id}."
                    if feedback_passed
                    else f"Unexpected feedback response: {feedback_result}"
                ),
            }
        )
        board_result = (
            check_feedback_board_lifecycle_with_http(base_url, query_id)
            if base_url
            else check_feedback_board_lifecycle_with_test_client(query_id)
        )
        board_feedback_id = board_result["submitted"]["body"].get("feedback_id")
        listed_items = board_result["listed"]["body"].get("items", [])
        board_passed = (
            board_result["submitted"]["status_code"] == 200
            and board_result["listed"]["status_code"] == 200
            and any(item.get("feedback_id") == board_feedback_id for item in listed_items)
            and board_result["updated"]["status_code"] == 200
            and board_result["updated"]["body"].get("feedback", {}).get("status") == "CONFIRMED"
        )
        gates.append(
            {
                "name": "badcase_board_lifecycle",
                "passed": board_passed,
                "detail": (
                    f"Feedback {board_feedback_id} was listed and moved to CONFIRMED."
                    if board_passed
                    else f"Unexpected board lifecycle response: {board_result}"
                ),
            }
        )
        golden_result = (
            check_golden_question_lifecycle_with_http(base_url, query_id)
            if base_url
            else check_golden_question_lifecycle_with_test_client(query_id)
        )
        golden_id = golden_result.get("golden_id")
        golden_items = golden_result["listed"]["body"].get("items", [])
        eval_results = golden_result["evaluated"]["body"].get("results", [])
        golden_passed = (
            golden_result["submitted"]["status_code"] == 200
            and golden_result["confirmed"]["status_code"] == 200
            and golden_result["created"]["status_code"] == 200
            and golden_id
            and any(item.get("golden_id") == golden_id for item in golden_items)
            and golden_result["evaluated"]["status_code"] == 200
            and any(item.get("golden_id") == golden_id and item.get("passed") for item in eval_results)
        )
        gates.append(
            {
                "name": "golden_question_regression",
                "passed": bool(golden_passed),
                "detail": (
                    f"Golden question {golden_id} was created and passed regression evaluation."
                    if golden_passed
                    else f"Unexpected golden question lifecycle response: {golden_result}"
                ),
            }
        )
    else:
        gates.append(
            {
                "name": "badcase_feedback_submission",
                "passed": False,
                "detail": "No successful query_id was available for feedback submission.",
            }
        )
        gates.append(
            {
                "name": "badcase_board_lifecycle",
                "passed": False,
                "detail": "No successful query_id was available for dashboard lifecycle check.",
            }
        )
        gates.append(
            {
                "name": "golden_question_regression",
                "passed": False,
                "detail": "No successful query_id was available for golden question regression.",
            }
        )
    return gates


def run_evaluation(base_url: str | None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case in CASES:
        started = perf_counter()
        body = post_case_with_http(base_url, case) if base_url else post_case_with_test_client(case)
        latency_ms = int((perf_counter() - started) * 1000)
        results.append(case_result(case, body, latency_ms))

    gates = build_gate_results(base_url, results)
    passed_cases = sum(1 for item in results if item["passed"])
    passed_gates = sum(1 for item in gates if item["passed"])
    total = len(results) + len(gates)
    passed = passed_cases + passed_gates
    category_summary: dict[str, dict[str, Any]] = {}
    for item in results:
        category = item["category"]
        stats = category_summary.setdefault(category, {"passed": 0, "total": 0})
        stats["total"] += 1
        stats["passed"] += int(item["passed"])
    for stats in category_summary.values():
        stats["pass_rate"] = round(stats["passed"] / stats["total"], 4)
    latencies = sorted(item["latency_ms"] for item in results)
    p95_index = max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": base_url or "in-process TestClient",
        "summary": {
            "status": "PASS" if passed == total else "FAIL",
            "passed": passed,
            "total": total,
            "case_passed": passed_cases,
            "case_total": len(results),
            "gate_passed": passed_gates,
            "gate_total": len(gates),
            "pass_rate": round(passed / total, 4) if total else 0,
            "average_case_latency_ms": round(sum(latencies) / len(latencies), 2),
            "p95_case_latency_ms": latencies[p95_index],
        },
        "category_summary": category_summary,
        "cases": results,
        "gates": gates,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# ChatBI 产品入口测评报告",
        "",
        f"> 生成时间：{report['generated_at']}",
        f"> 目标：`{report['target']}`",
        "",
        "## 结论",
        "",
        f"- 总体状态：`{summary['status']}`",
        f"- 总通过：{summary['passed']}/{summary['total']}，通过率：{summary['pass_rate'] * 100:.2f}%",
        f"- 用例通过：{summary['case_passed']}/{summary['case_total']}",
        f"- 安全/可信门禁通过：{summary['gate_passed']}/{summary['gate_total']}",
        f"- 平均响应时间：{summary.get('average_case_latency_ms', 0)}ms",
        f"- P95响应时间：{summary.get('p95_case_latency_ms', 0)}ms",
        "",
        "## 分层结果",
        "",
        "| 类型 | 通过 | 总数 | 通过率 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, stats in report.get("category_summary", {}).items():
        lines.append(
            f"| {category} | {stats['passed']} | {stats['total']} | {stats['pass_rate'] * 100:.2f}% |"
        )
    lines.extend([
        "",
        "## 用例明细",
        "",
        "| 用例 | 结果 | 问题 | 状态 | 指标 | 意图 | 图表 | 行数 | Evidence | Reflection | 耗时 |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |",
    ])
    for item in report["cases"]:
        result = "PASS" if item["passed"] else "FAIL"
        lines.append(
            "| "
            + " | ".join(
                [
                    item["name"],
                    result,
                    item["query"],
                    str(item.get("status") or ""),
                    str(item.get("selected_metric_id") or ""),
                    str(item.get("dsl_intent") or ""),
                    str(item.get("chart_type") or ""),
                    str(item.get("row_count") or ""),
                    str(item.get("evidence_count") or ""),
                    str(item.get("reflection_status") or ""),
                    f"{item['latency_ms']}ms",
                ]
            )
            + " |"
        )
    lines.extend(["", "## 安全与可信门禁", ""])
    for gate in report["gates"]:
        result = "PASS" if gate["passed"] else "FAIL"
        lines.append(f"- `{gate['name']}`：{result}。{gate['detail']}")

    failures = [
        (item["name"], item["errors"])
        for item in report["cases"]
        if item["errors"]
    ]
    failed_gates = [gate for gate in report["gates"] if not gate["passed"]]
    lines.extend(["", "## 失败项", ""])
    if not failures and not failed_gates:
        lines.append("无。")
    for name, errors in failures:
        lines.append(f"- `{name}`")
        for error in errors:
            lines.append(f"  - {error}")
    for gate in failed_gates:
        lines.append(f"- `{gate['name']}`：{gate['detail']}")

    lines.extend(
        [
            "",
            "## 覆盖范围",
            "",
            "- 成功链路：自然语言到可信解读闭环。",
            "- 排行链路：非时间维度聚合与柱状图展示。",
            "- 歧义链路：指标口径不清时安全澄清，不执行查询。",
            "- 拒绝链路：未知指标不生成 DSL、不编译查询。",
            "- 权限链路：非 demo workspace 被拦截。",
            "- 安全门禁：内部服务接口仍要求 Bearer Token。",
            "- 指标口径门禁：指标目录能返回口径、公式、维度和数仓血缘。",
            "- 反馈门禁：成功查询可提交 Badcase 反馈，并进入回归集候选。",
            "- 看板门禁：Badcase 能在看板出现，并推进到 CONFIRMED 状态。",
            "- 黄金集门禁：已确认 Badcase 能沉淀为黄金问题，并通过回归评测。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], output_dir: Path, report_name: str) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{report_name}.json"
    md_path = output_dir / f"{report_name}.md"
    history_dir = output_dir / "evaluation-history"
    history_dir.mkdir(parents=True, exist_ok=True)

    generated_at = str(report.get("generated_at") or datetime.now(UTC).isoformat())
    safe_timestamp = re.sub(r"[^0-9A-Za-z]", "", generated_at)[:32]
    if not safe_timestamp:
        safe_timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    history_path = history_dir / f"{report_name}-{safe_timestamp}.json"
    report_with_name = {**report, "report_name": report_name}

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    history_path.write_text(json.dumps(report_with_name, ensure_ascii=False, indent=2), encoding="utf-8")
    return json_path, md_path, history_path


def main() -> None:
    args = parse_args()
    report = run_evaluation(args.base_url)
    for item in report["cases"]:
        result = "PASS" if item["passed"] else "FAIL"
        detail = item.get("query_id") or item.get("message")
        print(f"{result}: {item['name']} ({detail})")
        for error in item["errors"]:
            print(f"  - {error}")
    for gate in report["gates"]:
        result = "PASS" if gate["passed"] else "FAIL"
        print(f"{result}: {gate['name']} ({gate['detail']})")

    summary = report["summary"]
    print(f"\nSummary: {summary['passed']}/{summary['total']} checks passed")
    if not args.no_report:
        json_path, md_path, history_path = write_reports(report, Path(args.output_dir), args.report_name)
        print(f"JSON report: {json_path}")
        print(f"Markdown report: {md_path}")
        print(f"History report: {history_path}")
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
