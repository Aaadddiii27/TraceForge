"""
Application configuration loaded from environment variables.

All settings have sensible defaults for local development.
Production deployments must override SECRET_KEY and database credentials.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class PayloadLogLevel(str, Enum):
    NONE = "none"
    METADATA_ONLY = "metadata_only"
    FULL = "full"


class ModelProvider(str, Enum):
    MOCK = "mock"
    OPENAI = "openai"
    GEMINI = "gemini"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: Environment = Environment.DEVELOPMENT
    app_name: str = "AI Runtime Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # ── Security ──────────────────────────────────────────────────────────────
    enable_auth: bool = False
    secret_key: str = "insecure-dev-key-change-in-production"
    access_token_expire_minutes: int = 60

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://ai_runtime_user:localdevpassword@localhost:5432/ai_runtime"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # Sync URL for Alembic (derived)
    database_url_sync: str = ""

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Execution Engine ──────────────────────────────────────────────────────
    default_task_timeout_seconds: int = 30
    max_retry_attempts: int = 3
    retry_backoff_seconds: float = 1.0
    max_concurrent_tasks: int = 10

    # ── Tool Timeouts ─────────────────────────────────────────────────────────
    calculator_timeout_seconds: int = 5
    text_processor_timeout_seconds: int = 10
    knowledge_base_timeout_seconds: int = 10
    mock_tool_timeout_seconds: int = 2

    # ── Payload Logging ───────────────────────────────────────────────────────
    payload_log_level: PayloadLogLevel = PayloadLogLevel.METADATA_ONLY
    execution_retention_days: int = 30

    # ── OpenTelemetry ─────────────────────────────────────────────────────────
    otel_enabled: bool = False
    otel_service_name: str = "ai-runtime-backend"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_export_to_collector: bool = False

    # ── Prometheus ────────────────────────────────────────────────────────────
    prometheus_enabled: bool = True

    # ── Model Providers ───────────────────────────────────────────────────────
    default_model_provider: ModelProvider = ModelProvider.MOCK
    openai_api_key: str = ""
    openai_default_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1000
    gemini_api_key: str = ""
    gemini_default_model: str = "gemini-1.5-flash"
    gemini_max_tokens: int = 1000

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper

    @model_validator(mode="after")
    def derive_sync_url(self) -> "Settings":
        """Derive a psycopg2-compatible sync URL from the async URL for Alembic."""
        if not self.database_url_sync:
            self.database_url_sync = self.database_url.replace(
                "postgresql+asyncpg://", "postgresql+psycopg2://"
            ).replace(
                "postgresql://", "postgresql+psycopg2://"
            )
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        return self.app_env == Environment.TEST

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    def safe_dict(self) -> dict[str, Any]:
        """Return settings dict with secrets redacted."""
        data = self.model_dump()
        secret_fields = {"secret_key", "openai_api_key", "gemini_api_key", "database_url", "database_url_sync"}
        return {k: ("***REDACTED***" if k in secret_fields and v else v) for k, v in data.items()}


# Singleton — import this everywhere
settings = Settings()
