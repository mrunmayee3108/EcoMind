from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    query: str = Field(..., description="User query or calculation expression.")
    preferred_route: Optional[str] = Field(
        default="auto",
        description="Optional execution path: 'auto', 'deterministic_tool', 'small_model', 'medium_model', 'large_model'"
    )

class TokenUsageSchema(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    is_estimated: bool = False

from telemetry.schemas import TelemetryRecord, TelemetrySummary

class ChatResponse(BaseModel):
    query: str
    answer: str
    route: str
    model: Optional[str] = None
    provider: str
    execution_time_ms: float
    token_usage: Optional[TokenUsageSchema] = None
    large_model_avoided: bool = False
    cache_status: Optional[str] = Field(default="not_checked", description="'not_checked', 'miss', 'hit'")
    cache_similarity: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    telemetry: Optional[TelemetryRecord] = None

class CacheStatsSchema(BaseModel):
    enabled: bool
    threshold: float
    embedding_model: str
    total_entries: int
    total_hits: int
    cache_hits: int = 0
    cache_misses: int = 0
    faiss_total_vectors: int
    avoided_model_calls: int
    avoided_tokens: int
    storage_size_bytes: int = 0
    storage_size_kb: float = 0.0
    max_entries: Optional[int] = None
    ttl_days: Optional[int] = None
    cache_db_path: Optional[str] = None
    cache_index_path: Optional[str] = None

class ToolInfoSchema(BaseModel):
    name: str
    description: str
    type: str
    calls_llm: bool

class ModelProfileSchema(BaseModel):
    model_id: str
    provider: str
    tier: str
    context_window: int
    description: str
    is_local: bool
    pricing_input_per_1m_usd: Optional[float] = None
    pricing_output_per_1m_usd: Optional[float] = None
