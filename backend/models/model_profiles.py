from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any

class ModelTier(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

@dataclass
class ModelProfile:
    """Defines the specifications and operational profile of a supported model."""
    model_id: str
    provider: str
    tier: ModelTier
    context_window: int
    description: str
    is_local: bool
    pricing_input_per_1m_usd: Optional[float] = None
    pricing_output_per_1m_usd: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["tier"] = self.tier.value
        return data

# Standard supported profiles catalog across all providers
MODEL_CATALOG: Dict[str, ModelProfile] = {
    # --- Small Tier ---
    "local-small": ModelProfile(
        model_id="local-small",
        provider="local",
        tier=ModelTier.SMALL,
        context_window=4096,
        description="Local lightweight model (Ollama / offline CPU/GPU inference)",
        is_local=True,
        pricing_input_per_1m_usd=0.0,
        pricing_output_per_1m_usd=0.0,
    ),
    "gemini-2.5-flash-lite": ModelProfile(
        model_id="gemini-2.5-flash-lite",
        provider="google",
        tier=ModelTier.SMALL,
        context_window=1048576,
        description="Google Gemini 2.5 Flash-Lite (low latency cloud small model)",
        is_local=False,
        pricing_input_per_1m_usd=0.0375,
        pricing_output_per_1m_usd=0.15,
    ),
    "openai/gpt-oss-20b": ModelProfile(
        model_id="openai/gpt-oss-20b",
        provider="groq",
        tier=ModelTier.SMALL,
        context_window=131072,
        description="OpenAI GPT-OSS 20B on Groq LPUs (ultra-fast small inference)",
        is_local=False,
        pricing_input_per_1m_usd=0.05,
        pricing_output_per_1m_usd=0.10,
    ),
    "allam-2-7b": ModelProfile(
        model_id="allam-2-7b",
        provider="groq",
        tier=ModelTier.SMALL,
        context_window=8192,
        description="Allam-2 7B on Groq LPUs",
        is_local=False,
        pricing_input_per_1m_usd=0.05,
        pricing_output_per_1m_usd=0.10,
    ),
    "llama-3.1-8b-instant": ModelProfile(
        model_id="llama-3.1-8b-instant",
        provider="groq",
        tier=ModelTier.SMALL,
        context_window=131072,
        description="Meta Llama 3.1 8B Instant on Groq LPUs",
        is_local=False,
        pricing_input_per_1m_usd=0.05,
        pricing_output_per_1m_usd=0.08,
    ),

    # --- Medium Tier ---
    "gemini-flash-latest": ModelProfile(
        model_id="gemini-flash-latest",
        provider="google",
        tier=ModelTier.MEDIUM,
        context_window=1048576,
        description="Google Gemini Flash (latest active balanced model)",
        is_local=False,
        pricing_input_per_1m_usd=0.075,
        pricing_output_per_1m_usd=0.30,
    ),
    "gemini-2.5-flash": ModelProfile(
        model_id="gemini-2.5-flash",
        provider="google",
        tier=ModelTier.MEDIUM,
        context_window=1048576,
        description="Google Gemini 2.5 Flash",
        is_local=False,
        pricing_input_per_1m_usd=0.075,
        pricing_output_per_1m_usd=0.30,
    ),
    "qwen/qwen3.8-27b": ModelProfile(
        model_id="qwen/qwen3.8-27b",
        provider="groq",
        tier=ModelTier.MEDIUM,
        context_window=131072,
        description="Qwen 3.8 27B on Groq LPUs (balanced multilingual model)",
        is_local=False,
        pricing_input_per_1m_usd=0.20,
        pricing_output_per_1m_usd=0.60,
    ),

    # --- Large Tier ---
    "gemini-pro-latest": ModelProfile(
        model_id="gemini-pro-latest",
        provider="google",
        tier=ModelTier.LARGE,
        context_window=2097152,
        description="Google Gemini Pro (latest active frontier reasoning model)",
        is_local=False,
        pricing_input_per_1m_usd=1.25,
        pricing_output_per_1m_usd=5.00,
    ),
    "gemini-2.5-pro": ModelProfile(
        model_id="gemini-2.5-pro",
        provider="google",
        tier=ModelTier.LARGE,
        context_window=2097152,
        description="Google Gemini 2.5 Pro (advanced reasoning cloud model)",
        is_local=False,
        pricing_input_per_1m_usd=1.25,
        pricing_output_per_1m_usd=5.00,
    ),
    "openai/gpt-oss-120b": ModelProfile(
        model_id="openai/gpt-oss-120b",
        provider="groq",
        tier=ModelTier.LARGE,
        context_window=131072,
        description="OpenAI GPT-OSS 120B on Groq LPUs (high-capacity reasoning)",
        is_local=False,
        pricing_input_per_1m_usd=0.60,
        pricing_output_per_1m_usd=1.20,
    ),
    "llama-3.3-70b-versatile": ModelProfile(
        model_id="llama-3.3-70b-versatile",
        provider="groq",
        tier=ModelTier.LARGE,
        context_window=131072,
        description="Meta Llama 3.3 70B Versatile on Groq LPUs",
        is_local=False,
        pricing_input_per_1m_usd=0.59,
        pricing_output_per_1m_usd=0.79,
    ),
}

def get_model_profile(model_id: str) -> Optional[ModelProfile]:
    """Retrieve profile by model_id."""
    return MODEL_CATALOG.get(model_id)

def get_models_by_tier(tier: ModelTier) -> List[ModelProfile]:
    """Return all models belonging to a specific tier."""
    return [p for p in MODEL_CATALOG.values() if p.tier == tier]

def list_all_profiles() -> List[Dict[str, Any]]:
    """Return dictionary list of all configured model profiles."""
    return [p.to_dict() for p in MODEL_CATALOG.values()]
