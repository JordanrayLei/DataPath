from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import (
    ConversationContext,
    GoldenQuestion,
    Metric,
    MetricDraft,
    MetricVersion,
    UserFeedback,
)
from app.db.session import SessionLocal


def test_frontend_entry_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "DataPath" in response.text
    assert "可信 ChatBI Copilot" in response.text
    assert "ask-form" in response.text
    assert 'data-view="workspace"' in response.text
    assert 'data-view="catalog"' in response.text
    assert 'data-view="ops"' in response.text
    assert 'data-view="quality"' in response.text
    assert 'data-view="metric-admin"' in response.text
    assert 'data-view="join-graph"' in response.text
    assert 'data-view-panel="workspace"' in response.text
    assert "view-hidden" in response.text
    assert "metric-domain-filter" in response.text
    assert "metric-admin-form" in response.text
    assert "metric-admin-publish" in response.text
    assert "join-form" in response.text
    assert "evaluation-refresh" in response.text
    assert "evaluation-trend" in response.text
    assert "2018年前九个月每月Olist成交总额趋势" in response.text
    assert "2017年各客户州Olist购买客户数排名" in response.text
    assert "2017年各商品品类Olist客单价排名" in response.text
    assert "2011年每月真实净收入趋势" not in response.text


def test_metric_catalog_lists_and_describes_metric_contracts(client: TestClient) -> None:
    listed = client.get(
        "/api/chatbi/metrics/catalog",
        params={"workspace_id": "demo", "domain": "sales", "limit": 20},
    )
    assert listed.status_code == 200, listed.text
    list_body = listed.json()
    assert list_body["status"] == "SUCCESS"
    assert list_body["domain_counts"]["sales"] >= 12
    assert any(item["metric_id"] == "M_OLIST_ITEM_REVENUE" for item in list_body["items"])
    assert {
        "M_OLIST_TOTAL_ORDER_VALUE",
        "M_OLIST_AVERAGE_ORDER_VALUE",
        "M_OLIST_CUSTOMER_COUNT",
    }.issubset({item["metric_id"] for item in list_body["items"]})

    detail = client.get(
        "/api/chatbi/metrics/catalog/M_OLIST_ITEM_REVENUE",
        params={"workspace_id": "demo"},
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    metric = body["metric"]
    assert metric["metric_id"] == "M_OLIST_ITEM_REVENUE"
    assert metric["business_domain_id"] == "sales"
    assert metric["latest_version"] >= 1
    assert "SUM(" in metric["formula_text"]
    assert "data_warehouse.olist_order_items" in metric["lineage"]["tables"]
    assert "price" in metric["lineage"]["fields"]
    assert {"D_DATE", "D_MONTH", "D_OLIST_CATEGORY"}.issubset(
        {item["dimension_id"] for item in metric["dimensions"]}
    )
    assert metric["example_questions"]
    assert body["versions"][0]["version"] == metric["latest_version"]


def test_metric_draft_can_be_validated_and_published(client: TestClient) -> None:
    metric_id = "M_SALES_MANAGED_TEST"
    with SessionLocal() as session:
        existing = session.get(Metric, metric_id)
        if existing is not None:
            session.delete(existing)
            session.commit()

    try:
        options = client.get(
            "/api/chatbi/metrics/manage/options", params={"workspace_id": "demo"}
        )
        assert options.status_code == 200, options.text
        option_body = options.json()
        assert any(item["id"] == "SM_OLIST_ORDER_ITEMS" for item in option_body["semantic_models"])
        assert any(item["id"] == "D_MONTH" for item in option_body["dimensions"])

        draft_payload = {
            "workspace_id": "demo",
            "metric_id": metric_id,
            "business_domain_id": "sales",
            "name": "测试支付金额",
            "description": "用于验证指标创建和版本发布闭环。",
            "metric_type": "amount",
            "unit": "BRL",
            "owner": "data-platform",
            "aliases": ["测试收入"],
            "semantic_model_id": "SM_OLIST_ORDER_ITEMS",
            "expression": {"op": "sum", "field": "price"},
            "default_aggregation": "default",
            "time_dimension_id": "D_DATE",
            "dimension_ids": ["D_DATE", "D_MONTH", "D_OLIST_CATEGORY"],
        }
        saved = client.put(
            f"/api/chatbi/metrics/manage/drafts/{metric_id}", json=draft_payload
        )
        assert saved.status_code == 200, saved.text
        saved_body = saved.json()
        assert saved_body["status"] == "DRAFT"
        assert saved_body["draft"]["validation"]["valid"] is True
        assert saved_body["draft"]["next_version"] == 1

        drafts = client.get(
            "/api/chatbi/metrics/manage/drafts", params={"workspace_id": "demo"}
        )
        assert drafts.status_code == 200, drafts.text
        assert any(item["metric_id"] == metric_id for item in drafts.json()["items"])

        published = client.post(
            f"/api/chatbi/metrics/manage/drafts/{metric_id}/publish",
            json={"workspace_id": "demo"},
        )
        assert published.status_code == 200, published.text
        assert published.json()["version"] == 1

        detail = client.get(
            f"/api/chatbi/metrics/catalog/{metric_id}", params={"workspace_id": "demo"}
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["metric"]["latest_version"] == 1
        assert detail.json()["expression"] == {"op": "sum", "field": "price"}

        second_payload = {**draft_payload, "description": "第二个不可变发布版本。"}
        second_saved = client.put(
            f"/api/chatbi/metrics/manage/drafts/{metric_id}", json=second_payload
        )
        assert second_saved.status_code == 200, second_saved.text
        assert second_saved.json()["draft"]["next_version"] == 2
        second_published = client.post(
            f"/api/chatbi/metrics/manage/drafts/{metric_id}/publish",
            json={"workspace_id": "demo"},
        )
        assert second_published.status_code == 200, second_published.text
        assert second_published.json()["version"] == 2

        with SessionLocal() as session:
            versions = session.scalars(
                select(MetricVersion)
                .where(MetricVersion.metric_id == metric_id)
                .order_by(MetricVersion.version)
            ).all()
            assert [item.version for item in versions] == [1, 2]
            assert session.scalar(
                select(MetricDraft).where(MetricDraft.metric_id == metric_id)
            ) is None
    finally:
        with SessionLocal() as session:
            metric = session.get(Metric, metric_id)
            if metric is not None:
                session.delete(metric)
                session.commit()


def test_evaluation_dashboard_reads_latest_report(client: TestClient) -> None:
    response = client.get("/api/chatbi/evaluations/latest")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["report_name"] in {
        "chatbi-entrypoint-evaluation-live-8010",
        "chatbi-entrypoint-evaluation-latest",
    }
    assert body["summary"]["total"] >= 1
    assert body["summary"]["passed"] <= body["summary"]["total"]
    assert body["cases"]
    assert body["gates"]


def test_evaluation_dashboard_reads_trend_history(client: TestClient) -> None:
    response = client.get("/api/chatbi/evaluations/trends", params={"limit": 10})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["total"] >= 1
    assert body["items"]
    latest = body["latest"]
    assert latest["total"] >= 1
    assert 0 <= latest["pass_rate"] <= 1
    assert "avg_latency_ms" in latest
    assert isinstance(latest["failed_gates"], list)


def test_frontend_ask_runs_complete_chatbi_chain(client: TestClient) -> None:
    response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "2017年每月Olist销售额趋势",
            "workspace_id": "demo",
            "conversation_id": "test_frontend",
            "biz_domain": "auto",
            "timezone": "Asia/Shanghai",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["selected_metric"]["metric_id"] == "M_OLIST_ITEM_REVENUE"
    assert body["dsl"]["intent"] == "trend_query"
    assert body["dsl"]["dimensions"] == [{"dimension_id": "D_MONTH"}]
    assert body["compiled"]["status"] == "READY"
    assert "execution_token" in body["compiled"]
    assert "SELECT " not in response.text.upper()
    assert body["execution"]["status"] == "SUCCEEDED"
    assert body["execution"]["row_count"] == 12
    assert body["profile"]["chart_spec"]["type"] == "line"
    assert len(body["profile"]["evidence"]) >= 2
    assert body["interpretation"]["findings"]
    assert body["reflection"]["status"] == "PASS"
    assert body["steps"][-1]["key"] == "reflection"


def test_frontend_multiturn_context_inherits_and_overrides_query_conditions(
    client: TestClient,
) -> None:
    conversation_id = "test_multiturn_context"
    with SessionLocal() as session:
        session.query(ConversationContext).filter_by(
            workspace_id="demo", conversation_id=conversation_id
        ).delete()
        session.commit()

    def ask(query: str) -> dict:
        response = client.post(
            "/api/chatbi/ask",
            json={
                "query": query,
                "workspace_id": "demo",
                "conversation_id": conversation_id,
                "biz_domain": "auto",
                "timezone": "Asia/Shanghai",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "SUCCESS", body
        return body

    try:
        first = ask("2017年每月Olist销售额趋势")
        assert first["selected_metric"]["metric_id"] == "M_OLIST_ITEM_REVENUE"
        assert first["dsl"]["intent"] == "trend_query"
        assert first["dsl"]["dimensions"] == [{"dimension_id": "D_MONTH"}]

        region = ask("按商品品类拆解")
        assert region["selected_metric"]["metric_id"] == "M_OLIST_ITEM_REVENUE"
        assert region["dsl"]["intent"] == "aggregate_query"
        assert region["dsl"]["dimensions"] == [{"dimension_id": "D_OLIST_CATEGORY"}]
        assert region["execution"]["row_count"] > 1
        assert "已继承上一轮" in region["steps"][0]["detail"]

        recent = ask("只看最近三个月")
        assert recent["dsl"]["dimensions"] == [{"dimension_id": "D_OLIST_CATEGORY"}]
        assert recent["dsl"]["time_range"]["start"] == "2018-07-01"
        assert recent["dsl"]["time_range"]["end"] == "2018-09-30"

        switched_metric = ask("换成Olist订单量")
        assert switched_metric["selected_metric"]["metric_id"] == "M_OLIST_ORDER_COUNT"
        assert switched_metric["dsl"]["dimensions"] == [{"dimension_id": "D_OLIST_CATEGORY"}]
        assert switched_metric["dsl"]["time_range"]["start"] == "2018-07-01"

        channel = ask("再看卖家州")
        assert channel["selected_metric"]["metric_id"] == "M_OLIST_ORDER_COUNT"
        assert channel["dsl"]["dimensions"] == [{"dimension_id": "D_OLIST_SELLER_STATE"}]
        assert channel["dsl"]["time_range"]["start"] == "2018-07-01"
    finally:
        with SessionLocal() as session:
            session.query(ConversationContext).filter_by(
                workspace_id="demo", conversation_id=conversation_id
            ).delete()
            session.commit()


def test_frontend_ask_clarifies_ambiguous_metric(client: TestClient) -> None:
    response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "Olist经营情况",
            "workspace_id": "demo",
            "conversation_id": "test_frontend",
            "biz_domain": "sales",
            "timezone": "Asia/Shanghai",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CLARIFY"
    assert body["compiled"] is None
    candidates = body["retrieval"]["mentions"][0]["candidates"]
    assert len({item["metric_id"] for item in candidates}) >= 2


def test_frontend_feedback_is_stored_as_regression_candidate(client: TestClient) -> None:
    ask_response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "2017年每月Olist销售额趋势",
            "workspace_id": "demo",
            "conversation_id": "test_feedback",
            "biz_domain": "auto",
            "timezone": "Asia/Shanghai",
        },
    )
    assert ask_response.status_code == 200, ask_response.text
    ask_body = ask_response.json()
    query_id = ask_body["compiled"]["query_id"]

    feedback_response = client.post(
        "/api/chatbi/feedback",
        json={
            "workspace_id": "demo",
            "conversation_id": "test_feedback",
            "query_id": query_id,
            "user_query": ask_body["query"],
            "feedback_type": "INTERPRETATION_UNTRUSTED",
            "severity": "HIGH",
            "message": "解读没有解释异常月份的业务背景。",
            "expected_behavior": "希望提示需要补充活动日历。",
            "page_context": {
                "selected_metric": ask_body["selected_metric"],
                "reflection": ask_body["reflection"],
            },
        },
    )
    assert feedback_response.status_code == 200, feedback_response.text
    feedback_body = feedback_response.json()
    assert feedback_body["status"] == "ACCEPTED"
    assert feedback_body["query_id"] == query_id
    assert feedback_body["regression_candidate"] is True

    with SessionLocal() as session:
        stored = session.scalar(
            select(UserFeedback).where(UserFeedback.feedback_id == feedback_body["feedback_id"])
        )
        assert stored is not None
        assert stored.query_id == query_id
        assert stored.feedback_type == "INTERPRETATION_UNTRUSTED"
        assert stored.severity == "HIGH"
        assert stored.regression_candidate is True
        assert stored.snapshot_json["query_id"] == query_id


def test_frontend_feedback_board_lists_and_updates_status(client: TestClient) -> None:
    ask_response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "2017年各商品品类Olist销售额排名",
            "workspace_id": "demo",
            "conversation_id": "test_feedback_board",
            "biz_domain": "sales",
            "timezone": "Asia/Shanghai",
        },
    )
    assert ask_response.status_code == 200, ask_response.text
    ask_body = ask_response.json()
    query_id = ask_body["compiled"]["query_id"]

    feedback_response = client.post(
        "/api/chatbi/feedback",
        json={
            "workspace_id": "demo",
            "conversation_id": "test_feedback_board",
            "query_id": query_id,
            "user_query": ask_body["query"],
            "feedback_type": "CHART_WRONG",
            "severity": "MEDIUM",
            "message": "排行图希望展示占比。",
            "expected_behavior": "柱状图展示数值和占比。",
            "page_context": {"chart_type": ask_body["profile"]["chart_spec"]["type"]},
        },
    )
    assert feedback_response.status_code == 200, feedback_response.text
    feedback_id = feedback_response.json()["feedback_id"]

    listed = client.get("/api/chatbi/feedback", params={"workspace_id": "demo", "status": "OPEN"})
    assert listed.status_code == 200, listed.text
    list_body = listed.json()
    assert any(item["feedback_id"] == feedback_id for item in list_body["items"])
    assert list_body["status_counts"]["OPEN"] >= 1

    confirmed = client.patch(
        f"/api/chatbi/feedback/{feedback_id}/status",
        json={"status": "CONFIRMED"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["feedback"]["status"] == "CONFIRMED"

    fixed = client.patch(
        f"/api/chatbi/feedback/{feedback_id}/status",
        json={"status": "FIXED"},
    )
    assert fixed.status_code == 200, fixed.text
    assert fixed.json()["feedback"]["status"] == "FIXED"


def test_confirmed_badcase_can_become_golden_question_and_regression_case(
    client: TestClient,
) -> None:
    ask_response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "2017年各商品品类Olist销售额排名",
            "workspace_id": "demo",
            "conversation_id": "test_golden_question",
            "biz_domain": "sales",
            "timezone": "Asia/Shanghai",
        },
    )
    assert ask_response.status_code == 200, ask_response.text
    ask_body = ask_response.json()
    query_id = ask_body["compiled"]["query_id"]

    feedback_response = client.post(
        "/api/chatbi/feedback",
        json={
            "workspace_id": "demo",
            "conversation_id": "test_golden_question",
            "query_id": query_id,
            "user_query": ask_body["query"],
            "feedback_type": "INTERPRETATION_UNTRUSTED",
            "severity": "HIGH",
            "message": "希望回归评测持续覆盖地区 GMV 排名链路。",
            "expected_behavior": "后续每次发布都要稳定返回地区排名、柱状图和 Reflection PASS。",
            "page_context": {
                "chart_type": ask_body["profile"]["chart_spec"]["type"],
                "reflection": ask_body["reflection"],
            },
        },
    )
    assert feedback_response.status_code == 200, feedback_response.text
    feedback_id = feedback_response.json()["feedback_id"]

    confirmed = client.patch(
        f"/api/chatbi/feedback/{feedback_id}/status",
        json={"status": "CONFIRMED"},
    )
    assert confirmed.status_code == 200, confirmed.text

    created = client.post(
        f"/api/chatbi/golden-questions/from-feedback/{feedback_id}",
        json={"biz_domain": "sales", "expected_notes": "地区排名核心链路"},
    )
    assert created.status_code == 200, created.text
    created_body = created.json()
    assert created_body["created"] is True
    golden = created_body["golden_question"]
    expected_dimension = (
        ask_body["dsl"]["dimensions"][0]["dimension_id"]
        if ask_body["dsl"]["dimensions"]
        else None
    )
    assert golden["source_feedback_id"] == feedback_id
    assert golden["expected_metric_id"] == ask_body["selected_metric"]["metric_id"]
    assert golden["expected_intent"] == ask_body["dsl"]["intent"]
    assert golden["expected_dimension_id"] == expected_dimension
    assert golden["expected_chart_type"] == ask_body["profile"]["chart_spec"]["type"]
    assert golden["expected_row_count"] == ask_body["execution"]["row_count"]
    assert golden["expected_reflection_status"] == ask_body["reflection"]["status"]

    duplicate = client.post(
        f"/api/chatbi/golden-questions/from-feedback/{feedback_id}",
        json={"biz_domain": "sales"},
    )
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["created"] is False
    assert duplicate.json()["golden_question"]["golden_id"] == golden["golden_id"]

    listed = client.get("/api/chatbi/golden-questions", params={"workspace_id": "demo"})
    assert listed.status_code == 200, listed.text
    assert any(item["golden_id"] == golden["golden_id"] for item in listed.json()["items"])

    evaluated = client.post(
        "/api/chatbi/golden-questions/evaluate",
        json={"workspace_id": "demo", "status": "ACTIVE", "limit": 20},
    )
    assert evaluated.status_code == 200, evaluated.text
    evaluation_body = evaluated.json()
    assert any(item["golden_id"] == golden["golden_id"] and item["passed"] for item in evaluation_body["results"])

    with SessionLocal() as session:
        stored = session.scalar(
            select(GoldenQuestion).where(GoldenQuestion.golden_id == golden["golden_id"])
        )
        assert stored is not None
        assert stored.source_feedback_id == feedback_id
        assert stored.expected_chart_type == ask_body["profile"]["chart_spec"]["type"]
