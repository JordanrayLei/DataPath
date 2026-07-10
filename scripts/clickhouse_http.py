"""Small standard-library ClickHouse HTTP client used by local data scripts."""

from __future__ import annotations

import base64
import http.client
import time
from pathlib import Path
from urllib.parse import urlencode


class ClickHouseHttpClient:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8123,
        user: str = "data_agent",
        password: str = "data_agent_dev",
        timeout: int = 120,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        credential = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {credential}"}

    def _connection(self) -> http.client.HTTPConnection:
        return http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)

    @staticmethod
    def _raise_for_status(response: http.client.HTTPResponse, body: bytes) -> None:
        if 200 <= response.status < 300:
            return
        message = body.decode("utf-8", errors="replace")
        raise RuntimeError(f"ClickHouse HTTP {response.status}: {message}")

    def ping(self) -> bool:
        connection = self._connection()
        try:
            connection.request("GET", "/ping", headers=self.headers)
            response = connection.getresponse()
            body = response.read()
            return response.status == 200 and body.strip() == b"Ok."
        except OSError:
            return False
        finally:
            connection.close()

    def wait_until_ready(self, attempts: int = 30, interval_seconds: float = 2.0) -> None:
        for _ in range(attempts):
            if self.ping():
                return
            time.sleep(interval_seconds)
        raise TimeoutError(f"ClickHouse at {self.host}:{self.port} did not become ready")

    def execute(self, sql: str) -> str:
        payload = sql.encode("utf-8")
        headers = {
            **self.headers,
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Length": str(len(payload)),
        }
        connection = self._connection()
        try:
            connection.request("POST", "/", body=payload, headers=headers)
            response = connection.getresponse()
            body = response.read()
            self._raise_for_status(response, body)
            return body.decode("utf-8")
        finally:
            connection.close()

    def insert_csv_with_names(self, table: str, path: Path) -> None:
        query = f"INSERT INTO {table} FORMAT CSVWithNames"
        request_path = "/?" + urlencode(
            {
                "query": query,
                "input_format_csv_empty_as_default": 1,
            }
        )
        size = path.stat().st_size
        connection = self._connection()
        try:
            connection.putrequest("POST", request_path)
            for key, value in self.headers.items():
                connection.putheader(key, value)
            connection.putheader("Content-Type", "text/csv; charset=utf-8")
            connection.putheader("Content-Length", str(size))
            connection.endheaders()
            with path.open("rb") as file:
                while chunk := file.read(1024 * 1024):
                    connection.send(chunk)
            response = connection.getresponse()
            body = response.read()
            self._raise_for_status(response, body)
        finally:
            connection.close()


def split_sql_statements(text: str) -> list[str]:
    without_comments = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("--")
    )
    return [statement.strip() for statement in without_comments.split(";") if statement.strip()]

