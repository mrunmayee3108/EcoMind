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

    # Phase 5B Environmental Accounting Settings
    # Local grid emissions factor in gCO2e per kWh (e.g. 370.0 for US national average, or region-specific factor).
    # If None or <= 0, local GPU operational carbon is reported as UNAVAILABLE without fabrication.
    LOCAL_GRID_INTENSITY_GCO2E_PER_KWH: Optional[float] = None
    LOCAL_GRID_REGION: str = "DEFAULT"
    ENABLE_DYNAMIC_GRID_INTENSITY: bool = False
    GRID_INTENSITY_SOURCE_NAME: str = "ConfiguredStatic"

    # Cloud Energy & Environmental Estimation Settings
    # Optional estimator for cloud API calls (e.g. ML.ENERGY or EcoLogits).
    # When False (default), cloud physical energy remains strictly UNAVAILABLE.
    ENABLE_CLOUD_ENERGY_ESTIMATION: bool = False
    CLOUD_ESTIMATOR_PREFERENCE: str = "composite"

    # Source Freshness & Registry Settings
    SOURCE_STALE_THRESHOLD_DAYS: int = 90
    SOURCE_REVIEW_NEEDED_DAYS: int = 30
    SOURCE_AUTO_CHECK_ON_STARTUP: bool = True

    # Semantic Cache Settings (Phase 4 Precision-First & Lifecycle Controls)
    CACHE_ENABLED: bool = True
    CACHE_SIMILARITY_THRESHOLD: float = 0.90
    CACHE_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CACHE_DB_PATH: str = "database/semantic_cache.db"
    CACHE_INDEX_PATH: str = "database/semantic_cache.index"
    MAX_CACHE_ENTRIES: int = 1000
    CACHE_TTL_DAYS: Optional[int] = 30

    # Phase 6 Multi-Objective Routing Optimizer Settings
    ROUTER_WEIGHT_QUALITY: float = 0.40
    ROUTER_WEIGHT_LATENCY: float = 0.25
    ROUTER_WEIGHT_COST: float = 0.20
    ROUTER_WEIGHT_ENVIRONMENT: float = 0.15
    ROUTER_QUALITY_THRESHOLD_HIGH: float = 0.80
    ROUTER_QUALITY_THRESHOLD_MEDIUM: float = 0.65
    ROUTER_QUALITY_THRESHOLD_LOW: float = 0.50
    ROUTER_PARETO_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
