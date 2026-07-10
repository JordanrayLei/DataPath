from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Metric, QueryRun
from app.schemas.chatbi import (
    DataQualitySummary,
    ExecuteRequest,
    ExecuteResponse,
    ResultColumn,
)
from app.services.signing import verify_execution_token
from app.warehouse.clickhouse import ClickHouseClient


class ExecutionError(ValueError):
    pass


def infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "decimal"
    if isinstance(value, str):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return "date"
        if re.match(r"^\d{4}-\d{2}-\d{2}[ T]", value):
            return "datetime"
    return "string"


def build_columns(session: Session, run: QueryRun, rows: list[dict[str, Any]]) -> list[ResultColumn]:
    field_names = list(rows[0]) if rows else [
        item.get("alias") or item["dimension_id"] for item in run.dsl_json.get("dimensions", [])
    ] + [item.get("alias") or item["metric_id"] for item in run.dsl_json.get("metrics", [])]
    sample = rows[0] if rows else {}
    metric_ids = [item["metric_id"] for item in run.dsl_json.get("metrics", [])]
    units = {
        metric.id: metric.unit
        for metric in session.scalars(select(Metric).where(Metric.id.in_(metric_ids))).all()
    }
    aliases_to_metric = {
        item.get("alias") or item["metric_id"]: item["metric_id"]
        for item in run.dsl_json.get("metrics", [])
    }
    aliases_to_dimension = {
        item.get("alias") or item["dimension_id"]: item["dimension_id"]
        for item in run.dsl_json.get("dimensions", [])
    }
    columns = []
    for name in field_names:
        metric_id = aliases_to_metric.get(name)
        dimension_id = aliases_to_dimension.get(name)
        columns.append(
            ResultColumn(
                name=name,
                type=infer_type(sample.get(name)),
                unit=units.get(metric_id) if metric_id else None,
                metric_id=metric_id,
                dimension_id=dimension_id,
            )
        )
    return columns


def execute_query(
    session: Session,
    request: ExecuteRequest,
    idempotency_key: str,
    request_id: str,
    trace_id: str,
) -> ExecuteResponse:
    if idempotency_key != request.query_id:
        raise ExecutionError("Idempotency-Key must equal query_id")
    run = session.get(QueryRun, request.query_id)
    if run is None:
        raise ExecutionError("query_id does not exist")
    if run.workspace_id != request.workspace_id or run.operator_id != request.operator_id:
        raise ExecutionError("query context mismatch")

    if run.status == "SUCCEEDED" and run.result_json is not None:
        cached = {**run.result_json, "cached": True, "request_id": request_id, "trace_id": trace_id}
        return ExecuteResponse.model_validate(cached)
    if run.status != "READY":
        raise ExecutionError(f"query is not executable in status {run.status}")
    if run.expires_at < datetime.now(UTC):
        run.status = "EXPIRED"
        session.commit()
        raise ExecutionError("query execution token expired")
    if not request.execution_token:
        raise ExecutionError("execution token is required")
    if not verify_execution_token(
        request.execution_token,
        run.query_id,
        run.sql_fingerprint,
        str(int(run.expires_at.timestamp())),
        get_settings().signing_secret,
    ):
        raise ExecutionError("invalid execution token")

    run.status = "RUNNING"
    session.commit()
    started = time.perf_counter()
    try:
        client = ClickHouseClient(
            get_settings().clickhouse_host,
            get_settings().clickhouse_http_port,
            get_settings().clickhouse_reader_user,
            get_settings().clickhouse_reader_password,
        )
        rows = client.execute_json_rows(run.sql_text, run.sql_params)
        execution_ms = int((time.perf_counter() - started) * 1000)
        columns = build_columns(session, run, rows)
        response = ExecuteResponse(
            request_id=request_id,
            trace_id=trace_id,
            query_id=run.query_id,
            status="SUCCEEDED",
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_ms=execution_ms,
            cached=False,
            truncated=len(rows) >= int(run.dsl_json.get("limit", 5000)),
            result_ref=None,
            data_quality=DataQualitySummary(
                freshness="normal",
                data_updated_at=datetime.now(UTC),
                completeness=1.0,
                warnings=[],
            ),
            error=None,
        )
        stored = response.model_dump(mode="json")
        stored.pop("request_id", None)
        stored.pop("trace_id", None)
        run.result_json = stored
        run.status = "SUCCEEDED"
        run.executed_at = datetime.now(UTC)
        session.commit()
        return response
    except Exception as error:
        run.status = "FAILED"
        run.error_json = {"code": "WAREHOUSE_EXECUTION_FAILED", "message": str(error)}
        session.commit()
        raise
