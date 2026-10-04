from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class TokenUsage:
    """Accurately records token usage without fabricating values."""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    is_estimated: bool = False

@dataclass
class ProviderResponse:
    """Standardized response from any model provider."""
    content: str
    model_name: str
    provider_name: str
    latency_ms: float
    usage: Optional[TokenUsage] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.content

class ModelProvider(ABC):
    """Abstract base class for all execution providers (models)."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. google, local, mock)."""
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate a response for the given prompt with metadata and telemetry."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return the capabilities and metadata of this provider."""
        pass
