from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    # API Keys & URLs
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Provider-Agnostic Tier Configuration (Logical Tiers)
    SMALL_PROVIDER: str = "groq"
    SMALL_MODEL: str = "openai/gpt-oss-20b"

    MEDIUM_PROVIDER: str = "groq"
    MEDIUM_MODEL: str = "qwen/qwen3.8-27b"

    LARGE_PROVIDER: str = "groq"
    LARGE_MODEL: str = "openai/gpt-oss-120b"

    # Fallback & Legacy Aliases
    GEMINI_DEFAULT_MODEL: str = "gemini-flash-latest"
    DEFAULT_SMALL_MODEL: str = "local-small"
    DEFAULT_MEDIUM_MODEL: str = "gemini-flash-latest"
    DEFAULT_LARGE_MODEL: str = "gemini-pro-latest"
    LOCAL_PROVIDER_FALLBACK: bool = True

    # Semantic Cache Settings (Phase 4 Precision-First & Lifecycle Controls)
    CACHE_ENABLED: bool = True
    CACHE_SIMILARITY_THRESHOLD: float = 0.90
    CACHE_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CACHE_DB_PATH: str = "database/semantic_cache.db"
    CACHE_INDEX_PATH: str = "database/semantic_cache.index"
    MAX_CACHE_ENTRIES: int = 1000
    CACHE_TTL_DAYS: Optional[int] = 30

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
