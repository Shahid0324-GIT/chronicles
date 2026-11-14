from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.application.research_policy import ResearchPolicy


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[5] / ".env", ".env"), extra="ignore"
    )
    database_url: str = "postgresql+asyncpg://atlas:atlas_local@127.0.0.1:5432/universe_atlas"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3.5:4b"
    ollama_embedding_model: str = "embeddinggemma:latest"
    ai_provider_mode: Literal["local", "hybrid", "cloud"] = "hybrid"
    ai_max_concurrent_inferences: int = Field(default=1, ge=1, le=2)
    ai_cloud_content_allowed: bool = False
    ai_timeout_seconds: float = Field(default=120, gt=0, le=600)
    ai_max_attempts: int = Field(default=2, ge=1, le=3)
    groq_api_key_primary: SecretStr | None = Field(default=None, repr=False)
    groq_api_key_secondary: SecretStr | None = Field(default=None, repr=False)
    groq_model: str | None = None
    promotion_minimum_sources: int = Field(default=1, ge=1, le=5)
    promotion_strong_sources: int = Field(default=2, ge=2, le=5)
    agent_max_iterations: int = Field(default=3, ge=1, le=20)
    agent_max_search_queries: int = Field(default=10, ge=0, le=100)
    agent_max_sources: int = Field(default=20, ge=1, le=200)
    agent_max_model_calls: int = Field(default=48, ge=1, le=200)
    agent_stage_model_calls: dict[str, int] = Field(
        default_factory=lambda: {
            "planning": 3,
            "extraction": 8,
            "identity_resolution": 16,
            "relationship_analysis": 3,
            "verification": 24,
            "presentation": 16,
            "presentation_verification": 16,
        }
    )
    agent_max_job_seconds: int = Field(default=900, ge=10, le=3600)
    research_focused_policy: ResearchPolicy = Field(default_factory=ResearchPolicy)
    research_max_source_bytes: int = Field(default=500_000, ge=1024, le=2_000_000)
    research_max_source_chars: int = Field(default=12_000, ge=500, le=30_000)
    research_source_cache_hours: int = Field(default=24, ge=0, le=168)
    research_allowed_hosts: list[str] = [
        "www.tv-tokyo.co.jp",
        "re-zero-anime.jp",
        "www.gutenberg.org",
    ]
    searxng_base_url: str | None = None

    @field_validator("agent_stage_model_calls")
    @classmethod
    def valid_stage_budgets(cls, value: dict[str, int]) -> dict[str, int]:
        if set(value) - {
            "planning",
            "extraction",
            "identity_resolution",
            "relationship_analysis",
            "verification",
            "presentation",
            "presentation_verification",
        } or any(not 1 <= v <= 200 for v in value.values()):
            raise ValueError("Stage budgets require known inference tasks and limits from 1 to 200")
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def local_inference_only(cls, value: str) -> str:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or url.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Ollama must be a loopback HTTP(S) endpoint")
        return value.rstrip("/")

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
