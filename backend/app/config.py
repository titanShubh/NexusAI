"""Application configuration via pydantic-settings."""

import json
from functools import lru_cache
from typing import Any, Optional


from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.0

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://nexus:nexus_pass@localhost:5433/nexus"

    @field_validator("database_url", mode="before")
    @classmethod
    def sanitize_database_url(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6380/0"

    # ── Qdrant ───────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6334
    qdrant_api_key: Optional[str] = None

    # ── Cohere Reranker ──────────────────────────────────────────────────
    cohere_api_key: Optional[str] = None

    # ── JWT Auth ─────────────────────────────────────────────────────────
    jwt_secret: str = "nexus-development-secret-key-3928471"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # ── Observability ────────────────────────────────────────────────────
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://us.cloud.langfuse.com"

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        return v



@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (created once per process)."""
    return Settings()
