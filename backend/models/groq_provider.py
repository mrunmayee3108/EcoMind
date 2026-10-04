import time
from typing import Any, Dict, Optional
from groq import Groq
from .provider import ModelProvider, ProviderResponse, TokenUsage
from config.settings import settings

class GroqProvider(ModelProvider):
    """Provider implementation for Groq models using the official groq SDK."""

    provider_name = "groq"

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.SMALL_MODEL
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        """Lazy initialization of the Groq client."""
        if self._client is None:
            api_key = settings.GROQ_API_KEY.strip() if settings.GROQ_API_KEY else None
            if not api_key:
                import os
                api_key = os.environ.get("GROQ_API_KEY")

            if not api_key:
                raise ValueError(
                    "Groq API key not found. Please set GROQ_API_KEY in backend/.env"
                )
            self._client = Groq(api_key=api_key)
        return self._client

    def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Generate content from Groq and extract authentic token metrics and latency."""
        target_model = kwargs.get("model", self.model_name)
        start_time = time.perf_counter()

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=target_model,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Extract authentic token counts from Groq usage metadata
        usage_meta = getattr(chat_completion, "usage", None)
        token_usage = None
        if usage_meta:
            token_usage = TokenUsage(
                prompt_tokens=getattr(usage_meta, "prompt_tokens", None),
                completion_tokens=getattr(usage_meta, "completion_tokens", None),
                total_tokens=getattr(usage_meta, "total_tokens", None),
                is_estimated=False
            )

        content = ""
        finish_reason = None
        if chat_completion.choices:
            choice = chat_completion.choices[0]
            if choice.message:
                content = choice.message.content or ""
            finish_reason = getattr(choice, "finish_reason", None)

        return ProviderResponse(
            content=content,
            model_name=target_model,
            provider_name=self.provider_name,
            latency_ms=latency_ms,
            usage=token_usage,
            raw_metadata={
                "finish_reason": finish_reason,
                "groq_model": getattr(chat_completion, "model", target_model)
            }
        )

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "provider": self.provider_name,
            "type": "cloud-groq-lpu",
            "is_local": False
        }
