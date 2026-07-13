from __future__ import annotations

import re
from calendar import monthrange
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ConversationContext
from app.schemas.chatbi import (
    ChatbiAskRequest,
    ChatbiAskResponse,
    ChatbiPipelineStep,
    CompileResponse,
    ContextLoadResponse,
    DslValidateResponse,
    ExecuteRequest,
    InterpretationGenerateRequest,
    MetricRetrieveRequest,
    PreprocessData,
    ProfileRequest,
    QueryDsl,
    ReflectionRequest,
)
from app.services.dsl_validator import validate_dsl
from app.services.interpretation_generator import generate_interpretation
from app.services.metric_retrieval import retrieve_metrics
from app.services.query_compiler import compile_query
from app.services.query_executor import execute_query
from app.services.query_understanding import get_query_understanding_provider
from app.services.reflection_validator import validate_interpretation
from app.services.result_profiler import profile_result
from app.services.signing import sign_value


Domain = Literal["sales"]


def _step(key: str, label: str, status: str, detail: str = "") -> ChatbiPipelineStep:
    return ChatbiPipelineStep(key=key, label=label, status=status, detail=detail)


def infer_domain(query: str, requested: str, prior_domain: str | None = None) -> Domain:
    return "sales"


def infer_dimension_mentions(query: str, domain: Domain) -> list[str]:
    mentions: list[str] = []
    if any(token in query for token in ("每月", "按月", "月度", "趋势", "近一年", "最近一年")):
        mentions.append("月份")
    if any(token in query for token in ("国家", "市场", "country")):
        mentions.append("国家")
    if any(token in query for token in ("商品", "产品")):
        mentions.append("真实商品")
    return mentions


def inherited_metric_name(last_query_context: dict[str, Any]) -> str:
    metrics = last_query_context.get("metrics") or []
    if not metrics:
        return ""
    metric = metrics[0]
    if isinstance(metric, dict):
        return str(metric.get("display_name") or metric.get("name") or "")
    return ""


def resolve_time_range(
    query: str,
    last_query_context: dict[str, Any],
    metric_id: str = "",
) -> dict[str, str]:
    def normalize_year(value: str) -> str:
        return value if len(value) == 4 else f"20{value}"

    year_pattern = r"(?<!\d)(20(?:0[9]|1[0-8]|2[0-6])|16|17|18)\s*年?"
    quarter_match = re.search(
        year_pattern + r"\s*第?([一二三四1234])\s*季度",
        query,
    )
    if quarter_match:
        year = normalize_year(quarter_match.group(1))
        quarter_text = quarter_match.group(2)
        quarter = {"一": 1, "二": 2, "三": 3, "四": 4}.get(
            quarter_text,
            int(quarter_text) if quarter_text.isdigit() else 1,
        )
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        end_day = monthrange(int(year), end_month)[1]
        return {
            "start": f"{year}-{start_month:02d}-01",
            "end": f"{year}-{end_month:02d}-{end_day:02d}",
        }

    first_months_match = re.search(
        year_pattern + r"\s*前\s*([一二三四五六七八九十\d]+)\s*个?月",
        query,
    )
    if first_months_match:
        year = normalize_year(first_months_match.group(1))
        month_text = first_months_match.group(2)
        month = {
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
        }.get(month_text, int(month_text) if month_text.isdigit() else 0)
        if 1 <= month <= 12:
            end_day = monthrange(int(year), month)[1]
            return {"start": f"{year}-01-01", "end": f"{year}-{month:02d}-{end_day:02d}"}

    if any(token in query for token in ("最近三个月", "近三个月", "过去三个月")):
        return {"start": "2018-07-01", "end": "2018-09-30"}
    if any(token in query for token in ("最近一年", "近一年", "过去一年")):
        return {"start": "2017-10-01", "end": "2018-09-30"}

    explicit_year = re.search(r"(?<!\d)(20(?:0[9]|1[0-8]|2[0-6]))\s*年?", query)
    if explicit_year:
        year = explicit_year.group(1)
        return {"start": f"{year}-01-01", "end": f"{year}-12-31"}
    short_year = re.search(r"(?<!\d)(16|17|18)\s*年", query)
    if short_year:
        year = f"20{short_year.group(1)}"
        return {"start": f"{year}-01-01", "end": f"{year}-12-31"}
    previous = last_query_context.get("time_range")
    if isinstance(previous, dict) and previous.get("start") and previous.get("end"):
        return {"start": str(previous["start"]), "end": str(previous["end"])}
    if metric_id.startswith("M_OLIST_"):
        return {"start": "2017-01-01", "end": "2017-12-31"}
    return {"start": "2017-01-01", "end": "2017-12-31"}


def build_preprocess(
    session: Session,
    query: str,
    domain: Domain,
    timezone: str,
    last_query_context: dict[str, Any],
) -> PreprocessData:
    inherited_metric = inherited_metric_name(last_query_context)
    understanding = get_query_understanding_provider().understand(
        session, query, domain, inherited_metric
    )
    explicit_metrics = understanding.metric_mentions
    explicit_dimensions = understanding.dimension_mentions or infer_dimension_mentions(query, domain)
    time_range = resolve_time_range(query, last_query_context)
    inherited = understanding.inherited_metric
    return PreprocessData(
        normalized_query=understanding.normalized_query,
        metric_mentions=explicit_metrics,
        dimension_mentions=explicit_dimensions,
        filter_mentions=understanding.filter_mentions or [],
        time_text=understanding.time_text or (
            "最近三个月"
            if any(token in query for token in ("最近三个月", "近三个月", "过去三个月"))
            else "最近一年"
            if any(token in query for token in ("最近一年", "近一年", "过去一年"))
            else ""
        ),
        time_start=understanding.time_start or time_range["start"],
        time_end=understanding.time_end or time_range["end"],
        comparison="",
        inherit_context=inherited or bool(last_query_context.get("dimensions")),
    )


def build_context(
    session: Session,
    request: ChatbiAskRequest,
    request_id: str,
    trace_id: str,
) -> ContextLoadResponse:
    settings = get_settings()
    context = session.scalar(
        select(ConversationContext).where(
            ConversationContext.workspace_id == request.workspace_id,
            ConversationContext.conversation_id == request.conversation_id,
        )
    )
    last_query_context = (
        context.last_query_context
        if context is not None
        else {"metrics": [], "dimensions": [], "filters": [], "time_range": None}
    )
    policy_value = f"{request.workspace_id}|{settings.default_operator_id}|public_viewer"
    return ContextLoadResponse(
        request_id=request_id,
        trace_id=trace_id,
        operator_id=settings.default_operator_id,
        allowed_domains=["sales", "advertising"],
        role_ids=["public_viewer"],
        row_policy_token=f"rpt.v1.{sign_value(policy_value, settings.signing_secret)}",
        last_query_context=last_query_context,
    )


def save_conversation_context(
    session: Session,
    payload: ChatbiAskRequest,
    operator_id: str,
    domain: Domain,
    selected_metric: dict[str, Any],
    dsl: QueryDsl,
) -> None:
    context = session.scalar(
        select(ConversationContext).where(
            ConversationContext.workspace_id == payload.workspace_id,
            ConversationContext.conversation_id == payload.conversation_id,
        )
    )
    snapshot = {
        "biz_domain": domain,
        "metrics": [
            {
                "metric_id": selected_metric.get("metric_id"),
                "metric_version": selected_metric.get("metric_version"),
                "display_name": selected_metric.get("display_name"),
            }
        ],
        "dimensions": [item.model_dump(mode="json") for item in dsl.dimensions],
        "filters": [item.model_dump(mode="json") for item in dsl.filters],
        "time_range": dsl.time_range.model_dump(mode="json"),
        "intent": dsl.intent,
    }
    if context is None:
        context = ConversationContext(
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            operator_id=operator_id,
            last_query_context=snapshot,
        )
        session.add(context)
    else:
        context.operator_id = operator_id
        context.last_query_context = snapshot
    session.commit()


def build_query_dsl(
    query: str,
    domain: Domain,
    metric_id: str,
    metric_version: int,
    timezone: str,
    last_query_context: dict[str, Any],
) -> dict[str, Any]:
    lowered = query.lower()
    wants_ranking = any(token in lowered for token in ("排名", "排行", "排个名", "top"))
    wants_monthly = any(token in query for token in ("每月", "按月", "月度", "趋势"))
    explicit_dimensions: list[str] = []
    if wants_monthly:
        explicit_dimensions.append("D_MONTH")
    dimension_query = lowered
    if metric_id.startswith("M_OLIST_"):
        for metric_name in ("Olist商品销售额", "Olist运费", "Olist订单量"):
            dimension_query = dimension_query.replace(metric_name.casefold(), "")
        dimension_rules = [
            (("品类", "类目", "category"), "D_OLIST_CATEGORY"),
            (("客户州", "买家州", "客户地区", "买家地区"), "D_OLIST_CUSTOMER_STATE"),
            (("卖家州", "卖家地区"), "D_OLIST_SELLER_STATE"),
            (("订单状态", "交易状态"), "D_OLIST_ORDER_STATUS"),
        ]
    elif domain == "sales":
        dimension_rules = [
            (("地区", "区域", "大区", "各地"), "D_REGION"),
            (("渠道", "来源"), "D_SALES_CHANNEL"),
            (("品类", "类目"), "D_CATEGORY"),
            (("商品", "产品"), "D_PRODUCT"),
        ]
    else:
        dimension_rules = [
            (("平台", "渠道", "媒体"), "D_AD_PLATFORM"),
            (("计划", "campaign"), "D_CAMPAIGN"),
        ]
    for tokens, dimension_id in dimension_rules:
        if any(token in dimension_query for token in tokens):
            explicit_dimensions.append(dimension_id)

    reset_dimensions = any(token in query for token in ("整体", "汇总", "总计", "不拆分"))
    previous_dimensions = [] if reset_dimensions else last_query_context.get("dimensions") or []
    inherited_dimensions = [
        str(item.get("dimension_id") if isinstance(item, dict) else item)
        for item in previous_dimensions
    ]
    dimension_ids = list(dict.fromkeys(explicit_dimensions or inherited_dimensions))
    dimensions = [{"dimension_id": item} for item in dimension_ids if item]
    sort: list[dict[str, str]] = []
    explicit_dimension_change = bool(explicit_dimensions) or reset_dimensions
    previous_intent = str(last_query_context.get("intent") or "")
    intent: str = previous_intent if previous_intent and not explicit_dimension_change else "aggregate_query"

    if wants_ranking:
        intent = "ranking_query"
        if not dimensions:
            dimensions = [{"dimension_id": (
                "D_OLIST_CATEGORY" if metric_id.startswith("M_OLIST_") else "D_REGION"
            )}]
        sort = [{"field_id": metric_id, "direction": "desc"}]
    elif dimensions and dimensions[0]["dimension_id"] == "D_MONTH":
        intent = "trend_query"
        sort = [{"field_id": "D_MONTH", "direction": "asc"}]
    elif dimensions:
        intent = "aggregate_query"
        sort = [{"field_id": metric_id, "direction": "desc"}]
    else:
        intent = "aggregate_query"

    time_range = resolve_time_range(query, last_query_context, metric_id)

    filters: list[dict[str, Any]] = []

    is_multi_entity = metric_id.startswith("M_OLIST_")
    return {
        "dsl_version": "2.0" if is_multi_entity else "1.0",
        **({"query_mode": "multi_entity"} if is_multi_entity else {}),
        "intent": intent,
        "metrics": [
            {
                "metric_id": metric_id,
                "metric_version": metric_version,
                "aggregation": "default",
            }
        ],
        "dimensions": dimensions,
        "filters": filters,
        "time_range": {
            "start": time_range["start"],
            "end": time_range["end"],
            "timezone": timezone,
        },
        "sort": sort,
        "limit": 100,
    }


def summarize_answer(
    interpretation: dict[str, Any],
    reflection: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    lines = [f"## {interpretation.get('title', '查询结果解读')}"]
    findings = interpretation.get("findings", [])
    if findings:
        lines.append("")
        lines.append("### 关键发现")
        for finding in findings:
            evidence_ids = "、".join(finding.get("evidence_ids", []))
            suffix = f"（证据：{evidence_ids}）" if evidence_ids else ""
            lines.append(f"- {finding.get('text', '')}{suffix}")
    caveats = interpretation.get("caveats", []) or profile.get("caveats", [])
    if caveats:
        lines.append("")
        lines.append("### 口径与限制")
        for caveat in caveats:
            lines.append(f"- {caveat}")
    next_actions = interpretation.get("next_actions", [])
    if next_actions:
        lines.append("")
        lines.append("### 建议下一步")
        for action in next_actions:
            lines.append(f"- {action}")
    lines.append("")
    lines.append(f"Reflection 状态：{reflection.get('status', 'UNKNOWN')}")
    return "\n".join(lines)


def _base_response(
    payload: ChatbiAskRequest,
    request_id: str,
    trace_id: str,
    domain: Domain,
    steps: list[ChatbiPipelineStep],
    status: str,
    message: str,
    **extra: Any,
) -> ChatbiAskResponse:
    return ChatbiAskResponse(
        request_id=request_id,
        trace_id=trace_id,
        status=status,
        message=message,
        query=payload.query,
        workspace_id=payload.workspace_id,
        conversation_id=payload.conversation_id,
        biz_domain=domain,
        steps=steps,
        **extra,
    )


def answer_chatbi_question(
    session: Session,
    payload: ChatbiAskRequest,
    request_id: str,
    trace_id: str,
) -> ChatbiAskResponse:
    settings = get_settings()
    domain = infer_domain(payload.query, payload.biz_domain)
    steps: list[ChatbiPipelineStep] = []

    if payload.workspace_id != settings.default_workspace_id:
        steps.append(_step("context", "上下文加载", "BLOCKED", "工作空间不可访问"))
        return _base_response(
            payload,
            request_id,
            trace_id,
            domain,
            steps,
            "BLOCKED",
            "当前演示环境只开放 demo 工作空间。",
        )

    context = build_context(session, payload, request_id, trace_id)
    context_data = context.model_dump(mode="json")
    last_query_context = context.last_query_context or {}
    domain = infer_domain(
        payload.query,
        payload.biz_domain,
        str(last_query_context.get("biz_domain") or ""),
    )
    inherited_parts = []
    if last_query_context.get("metrics"):
        inherited_parts.append("指标")
    if last_query_context.get("dimensions"):
        inherited_parts.append("维度")
    if last_query_context.get("time_range"):
        inherited_parts.append("时间")
    context_detail = (
        f"已继承上一轮的{'、'.join(inherited_parts)}条件"
        if inherited_parts
        else "已加载公开演示身份和行权限"
    )
    steps.append(_step("context", "上下文加载", "PASS", context_detail))

    retrieval_request = MetricRetrieveRequest(
        query=payload.query,
        normalized_query=payload.query.strip(),
        workspace_id=payload.workspace_id,
        biz_domain=domain,
        operator_id=context.operator_id,
        context=context_data,
        preprocess=build_preprocess(
            session, payload.query, domain, payload.timezone, last_query_context
        ),
    )
    retrieval = retrieve_metrics(session, retrieval_request, request_id, trace_id)
    retrieval_data = retrieval.model_dump(mode="json")
    selected = next(
        (
            candidate
            for mention in retrieval.mentions
            for candidate in mention.candidates
            if candidate.metric_id == mention.selected_metric_id
            and candidate.metric_version == mention.selected_metric_version
        ),
        None,
    )
    if retrieval.gate_status in {"CLARIFY", "REJECT"} or selected is None:
        status = "CLARIFY" if retrieval.gate_status == "CLARIFY" else "REJECT"
        steps.append(
            _step(
                "metrics",
                "指标检索",
                status,
                retrieval.clarification_message or "未找到可安全执行的指标。",
            )
        )
        return _base_response(
            payload,
            request_id,
            trace_id,
            domain,
            steps,
            status,
            retrieval.clarification_message or "没有找到可执行指标，请换一种问法。",
            operator_id=context.operator_id,
            retrieval=retrieval_data,
        )
    steps.append(
        _step(
            "metrics",
            "指标检索",
            "PASS",
            f"命中 {selected.display_name}，置信度 {selected.probability:.2f}",
        )
    )

    raw_dsl = build_query_dsl(
        payload.query,
        domain,
        selected.metric_id,
        selected.metric_version,
        payload.timezone,
        last_query_context,
    )
    query_mode = raw_dsl.get("query_mode", "single_model")
    steps.append(
        _step(
            "route",
            "查询分流",
            "PASS",
            "进入多实体Join规划链路" if query_mode == "multi_entity" else "进入单模型指标查询链路",
        )
    )
    validation = validate_dsl(session, raw_dsl, context_data, request_id, trace_id)
    validation_data = validation.model_dump(mode="json")
    if validation.status != "VALID" or validation.normalized_dsl is None:
        steps.append(_step("dsl", "DSL 校验", "BLOCKED", validation.message))
        return _base_response(
            payload,
            request_id,
            trace_id,
            domain,
            steps,
            "BLOCKED",
            validation.message,
            operator_id=context.operator_id,
            selected_metric=selected.model_dump(mode="json"),
            retrieval=retrieval_data,
            dsl=raw_dsl,
            validation=validation_data,
        )
    steps.append(_step("dsl", "DSL 校验", "PASS", "Query DSL 结构和权限校验通过"))

    dsl = QueryDsl.model_validate(validation.normalized_dsl)
    compiled: CompileResponse = compile_query(
        session,
        dsl,
        payload.workspace_id,
        context.operator_id,
        request_id,
        trace_id,
    )
    compiled_data = compiled.model_dump(mode="json")
    steps.append(
        _step(
            "compile",
            "SQL 编译与安全校验",
            "PASS",
            f"已生成 query_id={compiled.query_id}，SQL 未暴露给前端",
        )
    )

    executed = execute_query(
        session,
        ExecuteRequest(
            workspace_id=payload.workspace_id,
            operator_id=context.operator_id,
            query_id=compiled.query_id,
            execution_token=compiled.execution_token,
        ),
        compiled.query_id,
        request_id,
        trace_id,
    )
    execution_data = executed.model_dump(mode="json")
    steps.append(_step("execute", "数仓执行", "PASS", f"返回 {executed.row_count} 行"))

    profiled = profile_result(
        session,
        ProfileRequest(
            workspace_id=payload.workspace_id,
            query_id=compiled.query_id,
            execution_result=executed,
            dsl=dsl,
        ),
        request_id,
        trace_id,
    )
    profile_data = profiled.model_dump(mode="json")
    steps.append(_step("profile", "结果画像", "PASS", f"生成 {len(profiled.evidence)} 条 Evidence"))

    generated = generate_interpretation(
        session,
        InterpretationGenerateRequest(
            workspace_id=payload.workspace_id,
            query_id=compiled.query_id,
            dsl=dsl,
            profile=profiled,
        ),
        request_id,
        trace_id,
    )
    interpretation_data = generated.interpretation.model_dump(mode="json")
    steps.append(_step("interpretation", "业务解读", "PASS", "已生成基于查询结果的业务结论"))

    reflected = validate_interpretation(
        session,
        ReflectionRequest(
            workspace_id=payload.workspace_id,
            query_id=compiled.query_id,
            dsl=dsl,
            profile=profiled,
            interpretation=generated.interpretation,
        ),
        request_id,
        trace_id,
    )
    reflection_data = reflected.model_dump(mode="json")
    reflection_status = "PASS" if reflected.status == "PASS" else "BLOCKED"
    steps.append(
        _step(
            "reflection",
            "Reflection 校验",
            reflection_status,
            "解读通过校验" if reflected.status == "PASS" else reflected.revision_instruction,
        )
    )

    answer_markdown = summarize_answer(interpretation_data, reflection_data, profile_data)
    save_conversation_context(
        session,
        payload,
        context.operator_id,
        domain,
        selected.model_dump(mode="json"),
        dsl,
    )
    return _base_response(
        payload,
        request_id,
        trace_id,
        domain,
        steps,
        "SUCCESS" if reflected.status == "PASS" else "BLOCKED",
        "查询完成，结果已通过 Reflection 校验。" if reflected.status == "PASS" else "查询完成，但解读未通过校验。",
        operator_id=context.operator_id,
        selected_metric=selected.model_dump(mode="json"),
        retrieval=retrieval_data,
        dsl=validation.normalized_dsl,
        validation=validation_data,
        compiled=compiled_data,
        execution=execution_data,
        profile=profile_data,
        interpretation=interpretation_data,
        reflection=reflection_data,
        answer_markdown=answer_markdown,
    )
