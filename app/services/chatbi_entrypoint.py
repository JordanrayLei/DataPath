from __future__ import annotations

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
from app.services.metric_retrieval import (
    DEMO_RECENT_YEAR_END,
    DEMO_RECENT_YEAR_START,
    retrieve_metrics,
)
from app.services.query_compiler import compile_query
from app.services.query_executor import execute_query
from app.services.reflection_validator import validate_interpretation
from app.services.result_profiler import profile_result
from app.services.signing import sign_value


Domain = Literal["sales", "advertising"]


def _step(key: str, label: str, status: str, detail: str = "") -> ChatbiPipelineStep:
    return ChatbiPipelineStep(key=key, label=label, status=status, detail=detail)


def infer_domain(query: str, requested: str) -> Domain:
    if requested in {"sales", "advertising"}:
        return requested  # type: ignore[return-value]
    lowered = query.lower()
    ad_tokens = ("广告", "投放", "roas", "roi", "曝光", "点击", "消耗", "spend", "转化")
    return "advertising" if any(token in lowered for token in ad_tokens) else "sales"


def infer_metric_mentions(query: str, domain: Domain) -> list[str]:
    lowered = query.lower()
    if domain == "advertising":
        ordered = [
            (("roas", "投产比", "广告回报"), "ROAS"),
            (("roi", "投资回报"), "ROI"),
            (("广告消耗", "广告花费", "投放消耗", "投放成本", "spend"), "广告消耗"),
            (("点击率", "ctr"), "点击率"),
            (("点击",), "点击量"),
            (("曝光",), "曝光量"),
        ]
    else:
        ordered = [
            (("毛利率",), "毛利率"),
            (("毛利",), "毛利"),
            (("gmv", "成交额"), "GMV"),
            (("销售额", "已支付销售额"), "已支付销售额"),
            (("订单",), "支付订单量"),
            (("客单价",), "客单价"),
        ]
    for tokens, mention in ordered:
        if any(token in lowered or token in query for token in tokens):
            return [mention]
    return []


def infer_dimension_mentions(query: str, domain: Domain) -> list[str]:
    mentions: list[str] = []
    if any(token in query for token in ("每月", "按月", "月度", "趋势", "近一年", "最近一年")):
        mentions.append("月份")
    if domain == "sales" and any(token in query for token in ("地区", "区域", "大区", "各地")):
        mentions.append("地区")
    if domain == "advertising" and any(token in query for token in ("平台", "渠道", "媒体")):
        mentions.append("广告平台")
    return mentions


def build_preprocess(query: str, domain: Domain, timezone: str) -> PreprocessData:
    return PreprocessData(
        normalized_query=query.strip(),
        metric_mentions=infer_metric_mentions(query, domain),
        dimension_mentions=infer_dimension_mentions(query, domain),
        filter_mentions=[],
        time_text="最近一年" if any(token in query for token in ("最近一年", "近一年", "过去一年")) else "",
        time_start=DEMO_RECENT_YEAR_START,
        time_end=DEMO_RECENT_YEAR_END,
        comparison="",
        inherit_context=False,
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


def build_query_dsl(
    query: str,
    domain: Domain,
    metric_id: str,
    metric_version: int,
    timezone: str,
) -> dict[str, Any]:
    wants_ranking = any(token in query for token in ("排名", "排行", "top", "Top", "各地区", "各平台"))
    wants_monthly = any(token in query for token in ("每月", "按月", "月度", "趋势", "近一年", "最近一年", "过去一年"))
    dimensions: list[dict[str, str]] = []
    sort: list[dict[str, str]] = []
    intent: str = "aggregate_query"

    if wants_ranking:
        intent = "ranking_query"
        if domain == "advertising":
            dimensions = [{"dimension_id": "D_AD_PLATFORM"}]
        else:
            dimensions = [{"dimension_id": "D_REGION"}]
        sort = [{"field_id": metric_id, "direction": "desc"}]
    elif wants_monthly:
        intent = "trend_query"
        dimensions = [{"dimension_id": "D_MONTH"}]
        sort = [{"field_id": "D_MONTH", "direction": "asc"}]

    return {
        "dsl_version": "1.0",
        "intent": intent,
        "metrics": [
            {
                "metric_id": metric_id,
                "metric_version": metric_version,
                "aggregation": "default",
            }
        ],
        "dimensions": dimensions,
        "filters": [],
        "time_range": {
            "start": DEMO_RECENT_YEAR_START,
            "end": DEMO_RECENT_YEAR_END,
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
    steps.append(_step("context", "上下文加载", "PASS", "已加载公开演示身份和行权限"))

    retrieval_request = MetricRetrieveRequest(
        query=payload.query,
        normalized_query=payload.query.strip(),
        workspace_id=payload.workspace_id,
        biz_domain=domain,
        operator_id=context.operator_id,
        context=context_data,
        preprocess=build_preprocess(payload.query, domain, payload.timezone),
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
    steps.append(_step("interpretation", "业务解读", "PASS", "已生成 Evidence 约束解读"))

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
