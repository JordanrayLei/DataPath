from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EvidenceRecord, Metric, QueryRun, ResultProfile
from app.schemas.chatbi import (
    AnomalyPoint,
    ChartSpec,
    DimensionContribution,
    Evidence,
    EvidenceComparison,
    HeadlineMetric,
    ProfileRequest,
    ProfileResponse,
    TimeRange,
    TrendSummary,
)
from app.services.query_compiler import sha256_json


PROFILE_VERSION = "1.0"
TIME_DIMENSIONS = {"D_DATE", "D_WEEK", "D_MONTH", "D_QUARTER"}


class ProfileError(ValueError):
    pass


def stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24].upper()
    return f"{prefix}{digest}"


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def rounded(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)


def format_value(value: float | int | str | None, unit: str) -> str:
    if value is None:
        return "空值"
    if isinstance(value, float):
        text = f"{value:,.4f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text}{unit}" if unit == "%" else f"{text} {unit}".strip()


def period_range(value: str, dimension_id: str, fallback: TimeRange) -> TimeRange:
    try:
        start = date.fromisoformat(value[:10])
    except ValueError:
        return fallback
    if dimension_id == "D_DATE":
        end = start
    elif dimension_id == "D_MONTH":
        next_month = date(start.year + (start.month == 12), 1 if start.month == 12 else start.month + 1, 1)
        end = next_month - timedelta(days=1)
    else:
        return fallback
    return TimeRange(start=start, end=end, timezone=fallback.timezone)


def direction(change: float, tolerance: float = 1e-9) -> str:
    if change > tolerance:
        return "up"
    if change < -tolerance:
        return "down"
    return "flat"


def build_evidence(
    *,
    profile_id: str,
    query_id: str,
    evidence_type: str,
    metric_id: str,
    metric_version: int,
    statement: str,
    value: float | int | str | None,
    unit: str,
    time_range: TimeRange,
    dimensions: dict[str, str | int | float | bool],
    calculation: str,
    row_refs: list[int],
    comparison: EvidenceComparison | None = None,
    discriminator: object = "",
) -> Evidence:
    evidence_id = stable_id(
        "E",
        profile_id,
        evidence_type,
        metric_id,
        discriminator,
    )
    return Evidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        statement=statement,
        metric_id=metric_id,
        metric_version=metric_version,
        value=value,
        unit=unit,
        time_range=time_range,
        dimensions=dimensions,
        comparison=comparison,
        query_id=query_id,
        calculation=calculation,
        row_refs=sorted(set(row_refs)),
    )


def profile_result(
    session: Session,
    payload: ProfileRequest,
    request_id: str,
    trace_id: str,
) -> ProfileResponse:
    run = session.get(QueryRun, payload.query_id)
    if run is None:
        raise ProfileError("query_id does not exist")
    if run.workspace_id != payload.workspace_id:
        raise ProfileError("query workspace mismatch")
    if run.status != "SUCCEEDED" or run.result_json is None:
        raise ProfileError("query has no successful server-side result")
    if payload.execution_result.query_id != payload.query_id:
        raise ProfileError("execution result query_id mismatch")
    request_dsl = payload.dsl.model_dump(mode="json", exclude_none=True)
    if sha256_json(request_dsl) != run.dsl_hash:
        raise ProfileError("profile DSL does not match the compiled query")

    existing = session.scalar(
        select(ResultProfile).where(ResultProfile.query_id == payload.query_id)
    )
    if existing is not None:
        return ProfileResponse.model_validate(
            {**existing.profile_json, "request_id": request_id, "trace_id": trace_id}
        )

    stored_result = run.result_json
    rows: list[dict[str, Any]] = stored_result.get("rows", [])
    dsl = payload.dsl
    profile_id = stable_id("P", payload.query_id, PROFILE_VERSION)
    fallback_range = dsl.time_range

    metric_ids = [item.metric_id for item in dsl.metrics]
    metrics = {
        item.id: item
        for item in session.scalars(select(Metric).where(Metric.id.in_(metric_ids))).all()
    }
    metric_aliases = {
        item.metric_id: item.alias or item.metric_id for item in dsl.metrics
    }
    metric_versions = {item.metric_id: item.metric_version for item in dsl.metrics}
    dimension_aliases = {
        item.dimension_id: item.alias or item.dimension_id for item in dsl.dimensions
    }
    alias_to_dimension = {alias: dimension_id for dimension_id, alias in dimension_aliases.items()}
    time_dimension_id = next(
        (item.dimension_id for item in dsl.dimensions if item.dimension_id in TIME_DIMENSIONS),
        None,
    )
    time_alias = dimension_aliases.get(time_dimension_id) if time_dimension_id else None
    non_time_dimensions = [
        item.dimension_id for item in dsl.dimensions if item.dimension_id not in TIME_DIMENSIONS
    ]

    evidence: list[Evidence] = []
    headlines: list[HeadlineMetric] = []
    trends: list[TrendSummary] = []
    anomalies: list[AnomalyPoint] = []
    contributions: list[DimensionContribution] = []
    caveats: list[str] = []

    if stored_result.get("truncated"):
        caveats.append("查询结果已截断，画像仅基于返回范围。")
    data_quality = stored_result.get("data_quality", {})
    if float(data_quality.get("completeness", 1.0)) < 0.98:
        caveats.append("数据完整度低于 98%，结论可能受缺失数据影响。")
    caveats.extend(data_quality.get("warnings", []))

    indexed_rows = list(enumerate(rows))
    for metric_id in metric_ids:
        metric = metrics[metric_id]
        metric_alias = metric_aliases[metric_id]
        values = [
            (index, numeric, row)
            for index, row in indexed_rows
            if (numeric := number(row.get(metric_alias))) is not None
        ]
        if not values:
            caveats.append(f"指标“{metric.name}”没有可用于画像的数值。")
            continue

        is_additive = metric.metric_type in {"amount", "count"}
        grouped_time: dict[str, list[tuple[int, float, dict[str, Any]]]] = defaultdict(list)
        if time_alias:
            for item in values:
                grouped_time[str(item[2].get(time_alias, ""))].append(item)

        series: list[tuple[str, float, list[int]]] = []
        if grouped_time:
            for time_value, items in sorted(grouped_time.items()):
                if is_additive:
                    aggregated = sum(item[1] for item in items)
                elif len(items) == 1:
                    aggregated = items[0][1]
                else:
                    caveat = f"比率指标“{metric.name}”存在多维度分组，未做跨组加权汇总。"
                    if caveat not in caveats:
                        caveats.append(caveat)
                    continue
                series.append((time_value, aggregated, [item[0] for item in items]))

        if series:
            latest_time, latest_value, latest_refs = series[-1]
            scope = "latest_period"
            headline_range = period_range(latest_time, time_dimension_id or "", fallback_range)
            headline_dimensions: dict[str, str | int | float | bool] = {
                time_dimension_id or "time": latest_time
            }
            headline_calculation = "latest time bucket; additive metrics summed within bucket"
        elif len(values) == 1:
            latest_value = values[0][1]
            latest_refs = [values[0][0]]
            scope = "single_result"
            headline_range = fallback_range
            headline_dimensions = {
                dimension_id: values[0][2].get(alias)
                for dimension_id, alias in dimension_aliases.items()
                if values[0][2].get(alias) is not None
            }
            headline_calculation = "single returned row"
        elif is_additive:
            latest_value = sum(item[1] for item in values)
            latest_refs = [item[0] for item in values]
            scope = "full_range"
            headline_range = fallback_range
            headline_dimensions = {}
            headline_calculation = "sum of returned dimension rows"
        else:
            latest_value = values[0][1]
            latest_refs = [values[0][0]]
            scope = "single_result"
            headline_range = fallback_range
            headline_dimensions = {}
            caveats.append(f"比率指标“{metric.name}”未跨维度汇总，Headline 使用首条结果。")
            headline_calculation = "first row; ratio aggregation unavailable"

        headline_value = rounded(latest_value)
        headline_statement = (
            f"{metric.name}在{headline_range.start.isoformat()}至"
            f"{headline_range.end.isoformat()}为{format_value(headline_value, metric.unit)}。"
        )
        headline_evidence = build_evidence(
            profile_id=profile_id,
            query_id=run.query_id,
            evidence_type="headline",
            metric_id=metric_id,
            metric_version=metric_versions[metric_id],
            statement=headline_statement,
            value=headline_value,
            unit=metric.unit,
            time_range=headline_range,
            dimensions=headline_dimensions,
            calculation=headline_calculation,
            row_refs=latest_refs,
        )
        evidence.append(headline_evidence)
        headlines.append(
            HeadlineMetric(
                metric_id=metric_id,
                metric_version=metric_versions[metric_id],
                display_name=metric.name,
                value=headline_value,
                unit=metric.unit,
                scope=scope,
                dimensions=headline_dimensions,
                evidence_id=headline_evidence.evidence_id,
            )
        )

        if len(series) >= 2:
            first_time, first_value, first_refs = series[0]
            last_time, last_value, last_refs = series[-1]
            change = last_value - first_value
            change_rate = None if first_value == 0 else change / abs(first_value) * 100
            trend_statement = (
                f"{metric.name}从{first_time}的{format_value(rounded(first_value), metric.unit)}"
                f"变为{last_time}的{format_value(rounded(last_value), metric.unit)}，"
                f"变化{format_value(rounded(change), metric.unit)}。"
            )
            trend_evidence = build_evidence(
                profile_id=profile_id,
                query_id=run.query_id,
                evidence_type="trend",
                metric_id=metric_id,
                metric_version=metric_versions[metric_id],
                statement=trend_statement,
                value=rounded(last_value),
                unit=metric.unit,
                time_range=fallback_range,
                dimensions={},
                calculation="last time bucket minus first time bucket",
                row_refs=first_refs + last_refs,
                comparison=EvidenceComparison(
                    method="first_vs_last",
                    baseline_value=rounded(first_value),
                    absolute_change=rounded(change),
                    change_rate=rounded(change_rate),
                ),
            )
            evidence.append(trend_evidence)
            trends.append(
                TrendSummary(
                    metric_id=metric_id,
                    metric_version=metric_versions[metric_id],
                    start_value=round(first_value, 4),
                    end_value=round(last_value, 4),
                    absolute_change=round(change, 4),
                    change_rate=rounded(change_rate),
                    direction=direction(change),
                    point_count=len(series),
                    evidence_id=trend_evidence.evidence_id,
                )
            )

            series_values = [item[1] for item in series]
            mean = sum(series_values) / len(series_values)
            variance = sum((item - mean) ** 2 for item in series_values) / len(series_values)
            standard_deviation = math.sqrt(variance)
            if standard_deviation > 0:
                scored = [
                    (abs((item[1] - mean) / standard_deviation), item)
                    for item in series
                    if abs((item[1] - mean) / standard_deviation) >= 2.0
                ]
                for _, (time_value, anomaly_value, row_refs) in sorted(scored, reverse=True)[:5]:
                    z_score = (anomaly_value - mean) / standard_deviation
                    anomaly_statement = (
                        f"{time_value}的{metric.name}为"
                        f"{format_value(rounded(anomaly_value), metric.unit)}，"
                        f"相对该序列均值的 z-score 为{z_score:.2f}。"
                    )
                    anomaly_evidence = build_evidence(
                        profile_id=profile_id,
                        query_id=run.query_id,
                        evidence_type="anomaly",
                        metric_id=metric_id,
                        metric_version=metric_versions[metric_id],
                        statement=anomaly_statement,
                        value=rounded(anomaly_value),
                        unit=metric.unit,
                        time_range=period_range(time_value, time_dimension_id or "", fallback_range),
                        dimensions={time_dimension_id or "time": time_value},
                        calculation="population z-score across time buckets; threshold abs(z) >= 2.0",
                        row_refs=row_refs,
                        comparison=EvidenceComparison(
                            method="population_z_score",
                            baseline_value=rounded(mean),
                            z_score=round(z_score, 4),
                        ),
                        discriminator=time_value,
                    )
                    evidence.append(anomaly_evidence)
                    anomalies.append(
                        AnomalyPoint(
                            metric_id=metric_id,
                            metric_version=metric_versions[metric_id],
                            time_value=time_value,
                            value=round(anomaly_value, 4),
                            z_score=round(z_score, 4),
                            direction="high" if z_score > 0 else "low",
                            dimensions={time_dimension_id or "time": time_value},
                            evidence_id=anomaly_evidence.evidence_id,
                        )
                    )

        if is_additive:
            contribution_rows = indexed_rows
            contribution_range = fallback_range
            if time_alias and grouped_time:
                latest_time = sorted(grouped_time)[-1]
                contribution_rows = [
                    (index, row)
                    for index, row in indexed_rows
                    if str(row.get(time_alias, "")) == latest_time
                ]
                contribution_range = period_range(
                    latest_time, time_dimension_id or "", fallback_range
                )
            for dimension_id in non_time_dimensions:
                dimension_alias = dimension_aliases[dimension_id]
                grouped: dict[str | int | float | bool, list[tuple[int, float]]] = defaultdict(list)
                for index, row in contribution_rows:
                    metric_value = number(row.get(metric_alias))
                    dimension_value = row.get(dimension_alias)
                    if metric_value is not None and dimension_value is not None:
                        grouped[dimension_value].append((index, metric_value))
                totals = [
                    (dimension_value, sum(item[1] for item in items), [item[0] for item in items])
                    for dimension_value, items in grouped.items()
                ]
                total_value = sum(item[1] for item in totals)
                for rank, (dimension_value, value, row_refs) in enumerate(
                    sorted(totals, key=lambda item: (-item[1], str(item[0])))[:5],
                    start=1,
                ):
                    share = 0.0 if total_value == 0 else value / total_value
                    statement = (
                        f"{dimension_value}的{metric.name}为"
                        f"{format_value(rounded(value), metric.unit)}，"
                        f"占当前比较范围的{share * 100:.2f}%。"
                    )
                    contribution_evidence = build_evidence(
                        profile_id=profile_id,
                        query_id=run.query_id,
                        evidence_type="contribution",
                        metric_id=metric_id,
                        metric_version=metric_versions[metric_id],
                        statement=statement,
                        value=rounded(value),
                        unit=metric.unit,
                        time_range=contribution_range,
                        dimensions={dimension_id: dimension_value},
                        calculation="dimension value sum divided by selected-scope total",
                        row_refs=row_refs,
                        comparison=EvidenceComparison(
                            method="share_of_selected_scope",
                            share=round(share, 6),
                        ),
                        discriminator=f"{dimension_id}:{dimension_value}",
                    )
                    evidence.append(contribution_evidence)
                    contributions.append(
                        DimensionContribution(
                            metric_id=metric_id,
                            metric_version=metric_versions[metric_id],
                            dimension_id=dimension_id,
                            dimension_value=dimension_value,
                            value=round(value, 4),
                            share=round(share, 6),
                            rank=rank,
                            evidence_id=contribution_evidence.evidence_id,
                        )
                    )

    metric_output_aliases = [metric_aliases[item] for item in metric_ids]
    if not rows:
        chart_spec = ChartSpec(type="table", x="", y=metric_output_aliases, title="空查询结果")
        caveats.append("查询没有返回数据，未生成趋势、异常和贡献度结论。")
    elif time_alias:
        series_alias = dimension_aliases.get(non_time_dimensions[0]) if non_time_dimensions else None
        chart_spec = ChartSpec(
            type="line",
            x=time_alias,
            y=metric_output_aliases[0] if len(metric_output_aliases) == 1 else metric_output_aliases,
            series=series_alias,
            title=" / ".join(metrics[item].name for item in metric_ids) + "趋势",
        )
    elif dsl.dimensions:
        chart_spec = ChartSpec(
            type="bar" if len(dsl.dimensions) == 1 else "grouped_bar",
            x=dimension_aliases[dsl.dimensions[0].dimension_id],
            y=metric_output_aliases[0] if len(metric_output_aliases) == 1 else metric_output_aliases,
            series=(
                dimension_aliases[dsl.dimensions[1].dimension_id]
                if len(dsl.dimensions) > 1
                else None
            ),
            title=" / ".join(metrics[item].name for item in metric_ids) + "维度分析",
        )
    else:
        chart_spec = ChartSpec(
            type="metric",
            x=metric_output_aliases[0],
            y=metric_output_aliases,
            title=" / ".join(metrics[item].name for item in metric_ids),
        )

    evidence = evidence[:100]
    response = ProfileResponse(
        request_id=request_id,
        trace_id=trace_id,
        profile_id=profile_id,
        profile_version="1.0",
        query_id=run.query_id,
        headline_metrics=headlines,
        trend_summary=trends,
        anomalies=anomalies,
        dimension_contributions=contributions,
        chart_spec=chart_spec,
        evidence=evidence,
        caveats=list(dict.fromkeys(caveats)),
    )
    stored_profile = response.model_dump(mode="json")
    stored_profile.pop("request_id", None)
    stored_profile.pop("trace_id", None)
    session.add(
        ResultProfile(
            profile_id=profile_id,
            query_id=run.query_id,
            profile_version=PROFILE_VERSION,
            profile_json=stored_profile,
        )
    )
    session.flush()
    for item in evidence:
        item_data = item.model_dump(mode="json")
        session.add(
            EvidenceRecord(
                evidence_id=item.evidence_id,
                profile_id=profile_id,
                query_id=run.query_id,
                evidence_type=item.evidence_type,
                metric_id=item.metric_id,
                metric_version=item.metric_version,
                statement=item.statement,
                value_json={"value": item_data["value"]},
                unit=item.unit,
                time_range=item_data["time_range"],
                dimensions=item_data["dimensions"],
                comparison_json=item_data.get("comparison"),
                calculation=item.calculation,
                row_refs=item.row_refs,
            )
        )
    session.commit()
    return response
