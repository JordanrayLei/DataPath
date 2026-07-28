from app.schemas.chatbi import MetricDraftUpsertRequest
from app.services.metric_catalog import semantic_readiness
from app.services.metric_management import validate_definition
from app.db.session import SessionLocal


def test_semantic_readiness_requires_a_complete_governed_package() -> None:
    incomplete = semantic_readiness(
        description="短定义",
        owner="data-platform",
        aliases=["收入"],
        positive_examples=[],
        negative_examples=[],
    )
    ready = semantic_readiness(
        description="统计支付成功且实际到账的金额，不包含待支付、失败支付和已经退款的金额，并按业务日期归属。",
        owner="data-platform",
        aliases=["到账金额", "收款金额", "成功支付金额", "已收金额", "实际支付金额"],
        positive_examples=[
            "今年到账金额是多少",
            "每月收款金额趋势",
            "各地区成功支付金额",
            "最近一年已收金额",
            "实际支付金额同比",
        ],
        negative_examples=["订单原始金额", "应收金额", "退款金额"],
    )

    assert incomplete["score"] < 50
    assert incomplete["status"] == "INCOMPLETE"
    assert incomplete["gaps"]
    assert ready["score"] == 100
    assert ready["status"] == "READY"
    assert ready["gaps"] == []
    assert ready["advisory_only"] is True


def test_semantic_readiness_deduplicates_examples_for_scoring() -> None:
    result = semantic_readiness(
        description="一段足够长的业务定义，用来明确统计对象、时间口径、包含项以及需要排除的数据范围。",
        owner="owner",
        aliases=["同一个别名"] * 10,
        positive_examples=["同一个问法"] * 10,
        negative_examples=["同一个负例"] * 10,
    )

    assert result["components"]["aliases"] == 5
    assert result["components"]["positive_examples"] == 5
    assert result["components"]["negative_examples"] == 7


def test_draft_validation_reports_cross_metric_alias_conflicts() -> None:
    payload = MetricDraftUpsertRequest(
        workspace_id="demo",
        metric_id="M_SEMANTIC_CONFLICT_TEST",
        business_domain_id="production_benchmark",
        name="语义冲突测试指标",
        description="用于验证指标名称和别名发生跨指标重复时能够在保存草稿之前给出明确的冲突信息。",
        metric_type="amount",
        unit="CNY",
        owner="data-platform",
        aliases=["订单量"],
        positive_examples=["查询语义冲突测试指标"],
        negative_examples=["退款金额"],
        semantic_model_id="SM_PROD_ORDERS",
        expression={"op": "sum", "field": "gross_amount"},
        default_aggregation="default",
        time_dimension_id="D_DATE",
        dimension_ids=["D_DATE", "D_MONTH", "D_PROD_REGION"],
    )

    with SessionLocal() as session:
        validation = validate_definition(session, payload)

    assert validation["valid"] is True
    assert validation["alias_conflicts"]
    assert validation["alias_conflicts"][0]["other_metric_id"] == "M_PROD_ORDER_COUNT"
