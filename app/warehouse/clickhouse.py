from __future__ import annotations

import base64
import http.client
import json
from typing import Any
from urllib.parse import urlencode


class ClickHouseError(RuntimeError):
    pass


class ClickHouseClient:
    def __init__(self, host: str, port: int, user: str, password: str, timeout: int = 120):
        self.host = host
        self.port = port
        self.timeout = timeout
        credential = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.authorization = f"Basic {credential}"

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> str:
        query_params = {
            f"param_{key}": str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in (params or {}).items()
        }
        path = "/" if not query_params else f"/?{urlencode(query_params)}"
        payload = sql.encode("utf-8")
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            connection.request(
                "POST",
                path,
                body=payload,
                headers={
                    "Authorization": self.authorization,
                    "Content-Type": "text/plain; charset=utf-8",
                    "Content-Length": str(len(payload)),
                },
            )
            response = connection.getresponse()
            body = response.read()
            if not 200 <= response.status < 300:
                raise ClickHouseError(body.decode("utf-8", errors="replace"))
            return body.decode("utf-8")
        finally:
            connection.close()

    def execute_json_rows(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        query = sql.rstrip().rstrip(";") + " FORMAT JSONEachRow"
        output = self.execute(query, params)
        return [json.loads(line) for line in output.splitlines() if line.strip()]

    def estimate_table_rows(self, table: str) -> int:
        if not table.startswith("data_warehouse."):
            raise ValueError("table is outside the allowed warehouse database")
        database, table_name = table.split(".", maxsplit=1)
        output = self.execute(
            "SELECT coalesce(sum(rows), 0) FROM system.parts "
            "WHERE active AND database = {database:String} AND table = {table:String}",
            {"database": database, "table": table_name},
        )
        return int(output.strip() or 0)
