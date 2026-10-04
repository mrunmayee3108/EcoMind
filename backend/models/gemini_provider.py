import time
from typing import Any, Dict, Optional
from google import genai
from .provider import ModelProvider, ProviderResponse, TokenUsage
from config.settings import settings

class GeminiProvider(ModelProvider):
    """Provider implementation for Google's Gemini models using the official google-genai SDK."""
    
    provider_name = "google"

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.GEMINI_DEFAULT_MODEL
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        """Lazy initialization of the Gemini client."""
        if self._client is None:
            api_key = settings.GOOGLE_API_KEY.strip() if settings.GOOGLE_API_KEY else None
            if not api_key:
                # Also check process environment if not in settings
                import os
                api_key = os.environ.get("GOOGLE_API_KEY")
            
            if not api_key:
                raise ValueError(
                    "Google API key not found. Please set GOOGLE_API_KEY in backend/.env"
                )
            self._client = genai.Client(api_key=api_key)
        return self._client

    def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate content from Gemini and extract authentic token metrics and latency."""
        target_model = kwargs.get("model", self.model_name)
        start_time = time.perf_counter()

        response = self.client.models.generate_content(
            model=target_model,
            contents=prompt,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Accurately extract token counts from official usage metadata
        usage_meta = getattr(response, "usage_metadata", None)
        token_usage = None
        if usage_meta:
            token_usage = TokenUsage(
                prompt_tokens=getattr(usage_meta, "prompt_token_count", None),
                completion_tokens=getattr(usage_meta, "candidates_token_count", None),
                total_tokens=getattr(usage_meta, "total_token_count", None),
                is_estimated=False
            )

        return ProviderResponse(
            content=response.text or "",
            model_name=target_model,
            provider_name=self.provider_name,
            latency_ms=latency_ms,
            usage=token_usage,
            raw_metadata={
                "finish_reason": str(response.candidates[0].finish_reason) if response.candidates else None
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "provider": self.provider_name,
            "type": "cloud-llm",
            "tier": "medium" if "flash" in self.model_name else "large",
            "is_local": False
        }
