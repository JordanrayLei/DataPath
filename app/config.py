from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DataPath"
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
    query_understanding_provider: str = "metric_center"
    query_understanding_url: str = ""
    query_understanding_token: str = ""
    query_understanding_timeout_seconds: int = 15
    embedding_provider: str = "dashscope"
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v3"
    embedding_dimensions: int = 1024
    embedding_timeout_seconds: int = 30
    embedding_batch_size: int = 10
    dashscope_api_key: str = ""
    vector_search_limit: int = 5
    vector_similarity_threshold: float = 0.45
    vector_min_positive_similarity: float = 0.70
    vector_scope_negative_threshold: float = 0.64
    vector_scope_margin: float = 0.06
    reranker_enabled: bool = True
    reranker_base_url: str = "https://dashscope.aliyuncs.com/compatible-api/v1"
    reranker_model: str = "qwen3-rerank"
    reranker_timeout_seconds: int = 30
    reranker_candidate_limit: int = 5
    reranker_weight: float = 0.30


@lru_cache
def get_settings() -> Settings:
    return Settings()
