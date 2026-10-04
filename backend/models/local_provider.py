import time
import httpx
from typing import Any, Dict, Optional
from .provider import ModelProvider, ProviderResponse, TokenUsage
from config.settings import settings

class LocalProvider(ModelProvider):
    """Provider implementation for local models (via Ollama or local offline fallback)."""
    
    provider_name = "local"

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.DEFAULT_SMALL_MODEL
        self.base_url = settings.OLLAMA_BASE_URL

    def _try_ollama_generate(self, prompt: str, **kwargs) -> Optional[ProviderResponse]:
        """Attempt to call local Ollama server if running."""
        try:
            target_model = kwargs.get("model", self.model_name)
            if target_model == "local-small":
                target_model = "qwen2.5:0.5b"

            from telemetry.gpu import GpuEnergyMonitor
            gpu_monitor = GpuEnergyMonitor()
            gpu_monitor.start()
            start_time = time.perf_counter()
            try:
                with httpx.Client(timeout=0.4) as client:
                    res = client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": target_model,
                            "prompt": prompt,
                            "stream": False
                        }
                    )
            finally:
                gpu_monitor.stop()

            if res.status_code == 200:
                data = res.json()
                latency_ms = (time.perf_counter() - start_time) * 1000
                prompt_tokens = data.get("prompt_eval_count")
                eval_tokens = data.get("eval_count")
                total_tokens = (prompt_tokens or 0) + (eval_tokens or 0) if prompt_tokens or eval_tokens else None
                gpu_telemetry = gpu_monitor.get_telemetry()
                
                raw_metadata = {
                    "backend": "ollama",
                    "ollama_model": data.get("model", target_model),
                    "total_duration_ns": data.get("total_duration")
                }
                if gpu_telemetry.provenance.value == "MEASURED":
                    raw_metadata["gpu_telemetry"] = gpu_telemetry.model_dump()

                return ProviderResponse(
                    content=data.get("response", ""),
                    model_name=target_model,
                    provider_name=self.provider_name,
                    latency_ms=latency_ms,
                    usage=TokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=eval_tokens,
                        total_tokens=total_tokens,
                        is_estimated=False
                    ),
                    raw_metadata=raw_metadata
                )
        except Exception:
            return None
        return None

    def _fallback_generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """Lightweight offline local fallback for development/testing when no local model daemon is active."""
        start_time = time.perf_counter()
        target_model = kwargs.get("model", self.model_name)
        
        clean_prompt = prompt.strip()
        response_text = f"[Local Model ({target_model})]: Processed query '{clean_prompt[:60]}...' locally."
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        prompt_words = len(clean_prompt.split())
        resp_words = len(response_text.split())
        est_prompt_tokens = max(1, int(prompt_words * 1.3))
        est_resp_tokens = max(1, int(resp_words * 1.3))

        return ProviderResponse(
            content=response_text,
            model_name=target_model,
            provider_name=self.provider_name,
            latency_ms=latency_ms,
            usage=TokenUsage(
                prompt_tokens=est_prompt_tokens,
                completion_tokens=est_resp_tokens,
                total_tokens=est_prompt_tokens + est_resp_tokens,
                is_estimated=True
            ),
            raw_metadata={
                "backend": "local_offline_fallback",
                "notice": "Ollama/local model daemon not reachable; offline development fallback used.",
                "is_mock": True
            }
        )

    def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        """
        Generate response, trying Ollama first.
        If Ollama is unavailable and allow_fallback is False, raises ConnectionError
        so callers receive a clear provider-unavailable error rather than silent fabrication.
        """
        ollama_resp = self._try_ollama_generate(prompt, **kwargs)
        if ollama_resp is not None:
            return ollama_resp
        
        # allow_fallback defaults to settings.LOCAL_PROVIDER_FALLBACK, but can be explicitly disabled
        allow_fallback = kwargs.get("allow_fallback", settings.LOCAL_PROVIDER_FALLBACK)
        if allow_fallback:
            return self._fallback_generate(prompt, **kwargs)
        
        raise ConnectionError(
            f"Local model provider unable to reach Ollama daemon at {self.base_url}. "
            "Please ensure Ollama is running or configure another provider (such as Groq or Gemini)."
        )

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "provider": self.provider_name,
            "type": "local-llm",
            "tier": "small",
            "is_local": True
        }
