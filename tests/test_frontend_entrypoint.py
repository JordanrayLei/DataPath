from __future__ import annotations


def test_frontend_exposes_current_production_examples(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "2024年每月订单量趋势" in response.text
    assert "2024年各区域支付实收金额排名" in response.text
    assert "2024年退款后净收入" in response.text
    assert "Olist" not in response.text


def test_metric_catalog_and_management_share_one_navigation_view(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'data-view="catalog"' not in response.text
    assert response.text.count('data-view="metric-admin"') == 1
    assert response.text.count('data-view-panel="metric-admin"') == 2
    assert "指标中心" in response.text
    assert "指标治理与发布" in response.text


def test_frontend_exposes_domain_first_governance_flow(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert html.count('data-view="business-domains"') == 1
    assert 'data-view-panel="business-domains"' in html
    assert "业务域完成度" in html
    assert "推荐下一步" in html
    assert "上线阻塞项" in html
    assert "业务域数据模型" in html
    assert html.index('data-view-panel="business-domains"') < html.index('id="scope-example-count"')
    metric_governance = html.index('data-subpanel="metric-governance"')
    assert html.index('id="scope-example-count"') < metric_governance
    assert 'id="metric-domain-context"' in html
    assert "请选择事实模型" not in html
    assert 'data-source-step="3"' in html
    assert 'data-source-step="4"' not in html
    assert "物理资产清单" in html
    assert "维护业务表语义" not in html
    assert 'id="asset-edit-dialog"' not in html
    assert "业务解释在各业务域内独立维护" in html
    assert "主键（逗号分隔）" not in html
    assert 'id="asset-edit-exposed-fields"' not in html
    assert 'id="asset-edit-time-field"' not in html
    assert "保存选择并发布模型" not in html
    assert 'id="domain-model-dialog"' in html
    assert "默认分析时间" in html
    assert 'id="domain-model-description"' in html
    assert 'id="domain-model-entity-type"' in html
    assert 'id="domain-model-grain"' in html
    assert 'id="domain-model-primary-keys"' in html
    assert 'id="domain-configure-tables"' not in html
    assert 'id="source-assets-refresh" class="compact-action"' in html
    assert 'id="scope-preview-run" class="compact-action"' in html
    metric_filter = html[
        html.index('id="metric-domain-filter"') : html.index('id="metric-type-filter"')
    ]
    assert '<option value="production_benchmark">全渠道零售运营</option>' not in metric_filter
    assert '<option value="BLOCKED">已阻断</option>' in html
    assert 'id="schema-impact-count"' in html
    assert 'id="schema-impact-summary"' in html
    assert 'id="schema-impact-list"' in html
    assert "删表、删字段和字段类型变化" in html
    assert "当前业务域开放字段" in html
    assert "保存草稿" in html
    assert "发布模型" in html

    script = client.get("/frontend/app.js").text
    assert "data-binding-field" not in script
    assert "/api/chatbi/governance/assets/" not in script
    assert "data-asset-edit-id" not in script
    assert "assetEditExposedFields" not in script
    assert "/table-selections" in script
    assert "/models/" in script
    assert "/governance/schema-impacts" in script
    assert "renderMetricDomainOptions" in script
    assert "visibility=governance" in script
    assert "异常治理中" in script
    assert "FROZEN EVIDENCE" not in script
    assert "loadEvaluationTrend" not in script
    assert 'data-evaluation-tab="history"' not in html
    assert "最近结果" not in html
    assert 'item.name !== "数据质量审计上下文"' in script


def test_schema_change_impact_endpoint_is_available(client) -> None:
    response = client.get(
        "/api/chatbi/governance/schema-impacts",
        params={"workspace_id": "demo", "event_status": "ALL"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert {"total", "open", "critical", "affected_models", "affected_metrics"} <= set(
        payload["summary"]
    )


def test_frontend_retries_core_catalog_and_source_loading_during_startup(client) -> None:
    response = client.get("/frontend/app.js")
    assert response.status_code == 200
    script = response.text
    assert "fetchWithStartupRetry" in script
    assert 'fetchWithStartupRetry(`/api/chatbi/metrics/catalog' in script
    assert 'fetchWithStartupRetry("/api/chatbi/governance/sources?workspace_id=demo")' in script
    assert "127.0.0.1:8000 已启动后重试" in script


def test_metric_catalog_lists_current_governed_domain(client, service_headers) -> None:
    response = client.get(
        "/api/chatbi/metrics/catalog",
        params={"workspace_id": "demo", "domain": "production_benchmark", "limit": 20},
        headers=service_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["domain_counts"]["production_benchmark"] >= 9
    ids = {item["metric_id"] for item in body["items"]}
    assert "M_PROD_ORDER_COUNT" in ids
    assert "M_PROD_PAYMENT_AMOUNT" in ids


def test_metric_detail_contains_current_lineage(client, service_headers) -> None:
    response = client.get(
        "/api/chatbi/metrics/catalog/M_PROD_ORDER_COUNT",
        params={"workspace_id": "demo"},
        headers=service_headers,
    )
    assert response.status_code == 200, response.text
    metric = response.json()["metric"]
    assert metric["business_domain_id"] == "production_benchmark"
    assert "production_benchmark.fct_orders" in metric["lineage"]["tables"]
    assert {"D_DATE", "D_MONTH", "D_PROD_REGION"}.issubset(
        {item["dimension_id"] for item in metric["dimensions"]}
    )


def test_dangerous_write_is_blocked_before_execution(client, service_headers) -> None:
    response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "删除订单表",
            "workspace_id": "demo",
            "conversation_id": "frontend-safety",
            "biz_domain": "production_benchmark",
            "timezone": "Asia/Shanghai",
        },
        headers=service_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "BLOCKED"
    assert body["execution"] is None
