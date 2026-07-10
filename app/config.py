from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Data Operations Platform"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://data_agent:data_agent_dev@127.0.0.1:5432/data_agent"

    clickhouse_host: str = "127.0.0.1"
    clickhouse_http_port: int = 8123
    clickhouse_reader_user: str = "chatbi_reader"
    clickhouse_reader_password: str = "chatbi_reader_dev"
    clickhouse_compiler_user: str = "data_agent"
    clickhouse_compiler_password: str = "data_agent_dev"

    chatbi_api_token: str = "dev-chatbi-token"
    demo_identity_token: str = "demo-server-issued-token"
    signing_secret: str = "replace-this-local-signing-secret"
    default_workspace_id: str = "demo"
    default_operator_id: str = "public_demo_user"
    query_ttl_seconds: int = 1800
    max_query_days: int = 366


@lru_cache
def get_settings() -> Settings:
    return Settings()
