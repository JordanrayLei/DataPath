"""Run the eight-endpoint ChatBI vertical slice against a live HTTP server."""

from __future__ import annotations

import argparse

import httpx

from app.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/chatbi")
    parser.add_argument("--token", default=get_settings().chatbi_api_token)
    parser.add_argument("--identity-token", default=get_settings().demo_identity_token)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Request-ID": "req_live_smoke",
        "X-Trace-ID": "trace_live_smoke",
    }
    with httpx.Client(timeout=30) as client:
        context = client.post(
            f"{args.base_url}/context/load",
            headers=headers,
            json={
                "workspace_id": "demo",
                "conversation_id": "conv_live_smoke",
                "identity_token": args.identity_token,
            },
        )
        context.raise_for_status()
        context_body = context.json()
        print("PASS: context/load")

        retrieval = client.post(
            f"{args.base_url}/metrics/retrieve",
            headers=headers,
            json={
                "query": "最近一年每月 GMV",
                "normalized_query": "最近一年每月 GMV",
                "workspace_id": "demo",
                "biz_domain": "sales",
                "operator_id": context_body["operator_id"],
                "context": context_body,
                "preprocess": {
                    "normalized_query": "最近一年每月 GMV",
                    "metric_mentions": ["GMV"],
                    "dimension_mentions": ["月份"],
                    "filter_mentions": [],
                    "time_text": "最近一年",
                    "time_start": "2025-07-01",
                    "time_end": "2026-06-30",
                    "comparison": "",
                    "inherit_context": False,
                },
            },
        )
        retrieval.raise_for_status()
        assert retrieval.json()["gate_status"] == "PASS"
        print("PASS: metrics/retrieve")

        dsl = {
            "dsl_version": "1.0",
            "intent": "trend_query",
            "metrics": [
                {
                    "metric_id": "M_SALES_GMV",
                    "metric_version": 1,
                    "aggregation": "default",
                }
            ],
            "dimensions": [{"dimension_id": "D_MONTH"}],
            "filters": [],
            "time_range": {
                "start": "2025-07-01",
                "end": "2026-06-30",
                "timezone": "Asia/Shanghai",
            },
            "sort": [{"field_id": "D_MONTH", "direction": "asc"}],
            "limit": 100,
        }
        validation = client.post(
            f"{args.base_url}/dsl/validate",
            headers=headers,
            json={
                "workspace_id": "demo",
                "operator_id": context_body["operator_id"],
                "row_policy_context": context_body,
                "dsl": dsl,
            },
        )
        validation.raise_for_status()
        assert validation.json()["status"] == "VALID"
        print("PASS: dsl/validate")

        compiled = client.post(
            f"{args.base_url}/query/compile",
            headers=headers,
            json={
                "workspace_id": "demo",
                "operator_id": context_body["operator_id"],
                "dsl": validation.json()["normalized_dsl"],
                "permission_context": context_body,
            },
        )
        compiled.raise_for_status()
        compiled_body = compiled.json()
        assert compiled_body["status"] == "READY"
        assert "SELECT " not in compiled.text.upper()
        print("PASS: query/compile (SQL not exposed)")

        execute_headers = {
            **headers,
            "Idempotency-Key": compiled_body["query_id"],
        }
        executed = client.post(
            f"{args.base_url}/query/execute",
            headers=execute_headers,
            json={
                "workspace_id": "demo",
                "operator_id": context_body["operator_id"],
                "query_id": compiled_body["query_id"],
                "execution_token": compiled_body["execution_token"],
                "compiled_query": {"sql": "DROP TABLE data_warehouse.dwd_sales_order_item"},
            },
        )
        executed.raise_for_status()
        executed_body = executed.json()
        assert executed_body["status"] == "SUCCEEDED"
        assert executed_body["row_count"] == 12
        print("PASS: query/execute (12 rows; request SQL ignored)")

        profiled = client.post(
            f"{args.base_url}/result/profile",
            headers=headers,
            json={
                "workspace_id": "demo",
                "query_id": compiled_body["query_id"],
                "execution_result": executed_body,
                "dsl": validation.json()["normalized_dsl"],
            },
        )
        profiled.raise_for_status()
        profile_body = profiled.json()
        assert profile_body["profile_version"] == "1.0"
        assert profile_body["chart_spec"]["type"] == "line"
        assert profile_body["evidence"]
        assert all(item["row_refs"] for item in profile_body["evidence"])
        print(
            "PASS: result/profile "
            f"({len(profile_body['evidence'])} evidence records; deterministic chart)"
        )

        generated = client.post(
            f"{args.base_url}/interpretation/generate",
            headers=headers,
            json={
                "workspace_id": "demo",
                "query_id": compiled_body["query_id"],
                "dsl": validation.json()["normalized_dsl"],
                "profile": profile_body,
            },
        )
        generated.raise_for_status()
        generated_body = generated.json()
        interpretation = generated_body["interpretation"]
        assert interpretation["findings"]
        assert interpretation["findings"][0]["evidence_ids"]
        print("PASS: interpretation/generate (deterministic Evidence-bound fallback)")

        reflected = client.post(
            f"{args.base_url}/reflection/validate",
            headers=headers,
            json={
                "workspace_id": "demo",
                "query_id": compiled_body["query_id"],
                "dsl": validation.json()["normalized_dsl"],
                "profile": profile_body,
                "interpretation": interpretation,
            },
        )
        reflected.raise_for_status()
        reflection_body = reflected.json()
        assert reflection_body["status"] == "PASS"
        assert reflection_body["issues"] == []
        print("PASS: reflection/validate (Evidence-bound interpretation)")


if __name__ == "__main__":
    main()
