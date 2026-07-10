from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    EvidenceRecord,
    QueryRun,
    ReflectionValidation,
    ResultProfile,
)
from app.schemas.chatbi import (
    ReflectionIssue,
    ReflectionRequest,
    ReflectionResponse,
)
from app.services.query_compiler import sha256_json


BLOCK_CODES = {
    "UNKNOWN_EVIDENCE_ID",
    "NUMERIC_MISMATCH",
    "METRIC_VERSION_MISMATCH",
    "SENSITIVE_DATA_EXPOSURE",
}
DATE_TOKEN = re.compile(r"(?<!\d)(\d{4})-(\d{2})(?:-(\d{2}))?(?!\d)")
NUMBER_TOKEN = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d[\d,]*(?:\.\d+)?\s*%?")
CAUSAL_TOKEN = re.compile(
    r"导致|造成|归因于|引发|驱动|因为.{0,30}所以|带来.{0,20}(?:增长|下降|提升|减少)"
)
SENSITIVE_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    re.compile(r"\bselect\b[\s\S]{0,200}\bfrom\b", re.IGNORECASE),
    re.compile(r"password|access[_ -]?token|api[_ -]?key|密钥|密码", re.IGNORECASE),
)
CRITICAL_CAVEAT_KEYWORDS = ("截断", "完整", "延迟", "空值", "缺失", "比率")


class ReflectionError(ValueError):
    pass


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _close(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= max(0.01, abs(expected) * 0.001)


def _supported_numbers(records: Iterable[EvidenceRecord]) -> tuple[list[float], list[float]]:
    ordinary: list[float] = []
    percentages: list[float] = []
    for record in records:
        value = _number((record.value_json or {}).get("value"))
        if value is not None:
            ordinary.append(value)
            if record.unit == "%":
                percentages.append(value)
        comparison = record.comparison_json or {}
        for key in ("baseline_value", "absolute_change", "z_score"):
            value = _number(comparison.get(key))
            if value is not None:
                ordinary.append(value)
        change_rate = _number(comparison.get("change_rate"))
        if change_rate is not None:
            percentages.append(change_rate)
        share = _number(comparison.get("share"))
        if share is not None:
            percentages.append(share * 100)
    return ordinary, percentages


def _numeric_mismatch(text: str, records: list[EvidenceRecord]) -> str | None:
    # Dates describe evidence scope and are checked separately.
    without_dates = DATE_TOKEN.sub("", text)
    tokens = [item.group(0).strip() for item in NUMBER_TOKEN.finditer(without_dates)]
    if not tokens or any(text == record.statement for record in records):
        return None
    ordinary, percentages = _supported_numbers(records)
    for token in tokens:
        is_percentage = token.endswith("%")
        actual = _number(token.rstrip("%").strip())
        candidates = percentages if is_percentage else ordinary
        if actual is not None and not any(_close(actual, expected) for expected in candidates):
            return token
    return None


def _date_in_range(token: re.Match[str], records: list[EvidenceRecord]) -> bool:
    year, month, day = token.groups()
    token_start = date(int(year), int(month), int(day or 1))
    for record in records:
        try:
            start = date.fromisoformat(record.time_range["start"])
            end = date.fromisoformat(record.time_range["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if day:
            if start <= token_start <= end:
                return True
        elif (start.year, start.month) <= (token_start.year, token_start.month) <= (
            end.year,
            end.month,
        ):
            return True
    return False


def _unit_mismatch(text: str, records: list[EvidenceRecord]) -> str | None:
    units = {record.unit.lower() for record in records}
    _, percentages = _supported_numbers(records)
    if "%" in text and not percentages and "%" not in units:
        return "文本使用百分比，但所引证据不支持百分比口径。"
    if re.search(r"(?:元|\bCNY\b)", text, re.IGNORECASE) and not any(
        unit == "cny" or "元" in unit for unit in units
    ):
        return "文本使用金额单位，但所引证据不是金额口径。"
    return None


def _revision_instruction(issues: list[ReflectionIssue]) -> str:
    if not issues:
        return ""
    actions: list[str] = []
    for issue in issues:
        location = "整体回答" if issue.finding_index is None else f"第 {issue.finding_index + 1} 条发现"
        action = f"{location}：{issue.message}"
        if action not in actions:
            actions.append(action)
    return "请仅依据已验证 Evidence 修订以下问题：" + "；".join(actions)


def _saved_response(
    saved: ReflectionValidation, request_id: str, trace_id: str
) -> ReflectionResponse:
    return ReflectionResponse(
        request_id=request_id,
        trace_id=trace_id,
        status=saved.status,
        issues=[ReflectionIssue.model_validate(item) for item in saved.issues_json],
        revision_instruction=saved.revision_instruction,
    )


def validate_interpretation(
    session: Session,
    payload: ReflectionRequest,
    request_id: str,
    trace_id: str,
) -> ReflectionResponse:
    run = session.scalar(select(QueryRun).where(QueryRun.query_id == payload.query_id))
    if run is None:
        raise ReflectionError("query_id does not exist")
    if run.workspace_id != payload.workspace_id:
        raise ReflectionError("query does not belong to workspace")
    if run.status != "SUCCEEDED":
        raise ReflectionError("query has not succeeded")
    if sha256_json(payload.dsl.model_dump(mode="json", exclude_none=True)) != run.dsl_hash:
        raise ReflectionError("DSL does not match the compiled query")

    stored_profile = session.scalar(
        select(ResultProfile).where(ResultProfile.query_id == payload.query_id)
    )
    if stored_profile is None:
        raise ReflectionError("query has no stored profile")
    if (
        payload.profile.profile_id != stored_profile.profile_id
        or payload.profile.query_id != payload.query_id
    ):
        raise ReflectionError("profile does not match query")

    interpretation_data = payload.interpretation.model_dump(mode="json")
    interpretation_hash = sha256_json(interpretation_data)
    existing = session.scalar(
        select(ReflectionValidation).where(
            ReflectionValidation.query_id == payload.query_id,
            ReflectionValidation.interpretation_hash == interpretation_hash,
        )
    )
    if existing is not None:
        return _saved_response(existing, request_id, trace_id)

    evidence_records = session.scalars(
        select(EvidenceRecord).where(
            EvidenceRecord.query_id == payload.query_id,
            EvidenceRecord.profile_id == stored_profile.profile_id,
        )
    ).all()
    evidence_by_id = {record.evidence_id: record for record in evidence_records}
    issues: list[ReflectionIssue] = []

    if not payload.interpretation.findings:
        issues.append(
            ReflectionIssue(
                code="UNSUPPORTED_CLAIM",
                message="回答没有可核验的发现，请至少输出一条绑定 Evidence 的发现。",
                finding_index=None,
            )
        )

    for index, finding in enumerate(payload.interpretation.findings):
        unknown_ids = [item for item in finding.evidence_ids if item not in evidence_by_id]
        if unknown_ids:
            issues.append(
                ReflectionIssue(
                    code="UNKNOWN_EVIDENCE_ID",
                    message=f"引用了未知 Evidence ID：{', '.join(unknown_ids)}。",
                    finding_index=index,
                )
            )
        cited = [evidence_by_id[item] for item in finding.evidence_ids if item in evidence_by_id]
        if not cited:
            continue

        for record in cited:
            expected_version = (run.metric_versions or {}).get(record.metric_id)
            if expected_version is None or int(expected_version) != record.metric_version:
                issues.append(
                    ReflectionIssue(
                        code="METRIC_VERSION_MISMATCH",
                        message=f"Evidence {record.evidence_id} 的指标版本与查询快照不一致。",
                        finding_index=index,
                    )
                )

        bad_number = _numeric_mismatch(finding.text, cited)
        if bad_number is not None:
            issues.append(
                ReflectionIssue(
                    code="NUMERIC_MISMATCH",
                    message=f"数字 {bad_number} 无法由所引 Evidence 验证。",
                    finding_index=index,
                )
            )

        unit_message = _unit_mismatch(finding.text, cited)
        if unit_message:
            issues.append(
                ReflectionIssue(
                    code="UNIT_MISMATCH",
                    message=unit_message,
                    finding_index=index,
                )
            )

        invalid_dates = [
            item.group(0)
            for item in DATE_TOKEN.finditer(finding.text)
            if not _date_in_range(item, cited)
        ]
        if invalid_dates:
            issues.append(
                ReflectionIssue(
                    code="TIME_RANGE_MISMATCH",
                    message=f"时间 {', '.join(invalid_dates)} 超出所引 Evidence 范围。",
                    finding_index=index,
                )
            )

        if CAUSAL_TOKEN.search(finding.text):
            issues.append(
                ReflectionIssue(
                    code="UNSUPPORTED_CAUSAL_CLAIM",
                    message="当前 Evidence 只能支持相关性或描述性结论，不能支持因果归因。",
                    finding_index=index,
                )
            )

        if any(pattern.search(finding.text) for pattern in SENSITIVE_PATTERNS):
            issues.append(
                ReflectionIssue(
                    code="SENSITIVE_DATA_EXPOSURE",
                    message="发现疑似个人信息、凭据或原始 SQL，禁止输出。",
                    finding_index=index,
                )
            )

    full_text = "\n".join(
        [
            payload.interpretation.title,
            *payload.interpretation.caveats,
            *payload.interpretation.next_actions,
        ]
    )
    if any(pattern.search(full_text) for pattern in SENSITIVE_PATTERNS):
        issues.append(
            ReflectionIssue(
                code="SENSITIVE_DATA_EXPOSURE",
                message="标题、限制说明或下一步中包含疑似敏感信息。",
                finding_index=None,
            )
        )

    server_caveats = stored_profile.profile_json.get("caveats", [])
    supplied_caveats = "\n".join(payload.interpretation.caveats)
    missing_keywords = [
        keyword
        for keyword in CRITICAL_CAVEAT_KEYWORDS
        if any(keyword in caveat for caveat in server_caveats)
        and keyword not in supplied_caveats
    ]
    if missing_keywords:
        issues.append(
            ReflectionIssue(
                code="MISSING_DATA_QUALITY_CAVEAT",
                message=f"缺少服务端数据限制说明：{', '.join(missing_keywords)}。",
                finding_index=None,
            )
        )

    issue_codes = {item.code for item in issues}
    decision = "BLOCK" if issue_codes & BLOCK_CODES else "REVISE" if issues else "PASS"
    revision_instruction = _revision_instruction(issues)
    response = ReflectionResponse(
        request_id=request_id,
        trace_id=trace_id,
        status=decision,
        issues=issues,
        revision_instruction=revision_instruction,
    )
    session.add(
        ReflectionValidation(
            reflection_id=(
                "rf_"
                + sha256_json(
                    {
                        "query_id": payload.query_id,
                        "interpretation_hash": interpretation_hash,
                    }
                ).removeprefix("sha256:")[:24]
            ),
            query_id=payload.query_id,
            profile_id=stored_profile.profile_id,
            interpretation_hash=interpretation_hash,
            status=decision,
            issues_json=[item.model_dump(mode="json") for item in issues],
            revision_instruction=revision_instruction,
        )
    )
    session.commit()
    return response
