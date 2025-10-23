import json
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    env: str = "dev"
    database_url: str
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-5-nano"  # Deprecated: use secondary_model moving forward.
    secondary_model: str = "gpt-5-nano"
    secondary_reasoning_easy: str = "minimal"
    secondary_reasoning_hard: str = "high"
    secondary_verbosity_easy: str = "low"
    secondary_verbosity_hard: str = "medium"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    primary_model: str = "deepseek-chat"
    primary_reasoning_easy: str = "minimal"
    primary_reasoning_hard: str = "high"
    embedding_model: str = "text-embedding-3-large"
    cohere_api_key: str | None = None
    cohere_base_url: str = "https://api.cohere.com/v1"
    rerank_provider: str = "cohere"
    rerank_model: str = "rerank-english-v3.0"
    bge_rerank_url: str = "http://localhost:11434/v1/rerank"
    routing_version: str = "routing_v1.0"
    prompt_version: str = "prompt_v1.0"
    response_schema_version: str = "response_v1.0"
    llm_max_concurrency: int = 4
    rerank_max_concurrency: int = 8
    request_timeout_seconds: float = 90.0
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_match_function: str = "match_chunks"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_csv(cls, v: Any) -> Any:
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                try:
                    loaded = json.loads(stripped)
                    if isinstance(loaded, list):
                        return loaded
                except json.JSONDecodeError:
                    pass
            return [s.strip() for s in stripped.split(",") if s.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=("settings_",),
    )


settings = Settings()
