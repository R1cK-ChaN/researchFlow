"""Service settings loaded from environment / .env via pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Inbound auth (optional). When set, callers must send
    # Authorization: Bearer <token>.
    api_token: str | None = Field(default=None, alias="RESEARCHFLOW_API_TOKEN")

    # Sibling services.
    macro_data_base_url: str | None = Field(default=None, alias="ANALYST_MACRO_DATA_BASE_URL")
    macro_data_api_token: str | None = Field(default=None, alias="ANALYST_MACRO_DATA_API_TOKEN")
    macro_data_timeout: float = Field(default=30.0, alias="ANALYST_MACRO_DATA_TIMEOUT")

    rag_base_url: str | None = Field(default=None, alias="ANALYST_RAG_BASE_URL")
    rag_api_token: str | None = Field(default=None, alias="ANALYST_RAG_API_TOKEN")
    rag_timeout: float = Field(default=30.0, alias="ANALYST_RAG_TIMEOUT")

    # OpenRouter (LLM provider).
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    generator_model: str = Field(
        default="anthropic/claude-sonnet-4.5", alias="OPENROUTER_GENERATOR_MODEL"
    )
    judge_model: str = Field(
        default="anthropic/claude-haiku-4.5", alias="OPENROUTER_JUDGE_MODEL"
    )

    # Paths — everything is relative to the process cwd.
    runs_dir: str = Field(default="eval/runs/live", alias="RESEARCHFLOW_RUNS_DIR")
    house_view_path: str = Field(default="config/house_view.yaml", alias="HOUSE_VIEW_PATH")
    topic_registry_path: str = Field(
        default="config/topics.yaml", alias="TOPIC_REGISTRY_PATH"
    )
    framework_dir: str = Field(default="config/frameworks", alias="FRAMEWORK_DIR")
    exemplar_dir: str = Field(default="config/exemplars", alias="EXEMPLAR_DIR")

    # Reporting.
    disclaimer_path: str | None = Field(default=None, alias="DISCLAIMER_PATH")
