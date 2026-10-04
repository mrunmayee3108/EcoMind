from typing import Dict, Tuple, Optional, Any
from .provider import ModelProvider, ProviderResponse
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .local_provider import LocalProvider
from config.settings import settings

class ProviderUnavailableError(Exception):
    """Raised when a configured provider is unreachable or lacks required credentials."""
    pass

class ModelDispatcher:
    """
    Provider-agnostic dispatcher that resolves logical model tiers
    ('small', 'medium', 'large') to configured providers and models,
    then executes inference.
    """

    def __init__(
        self,
        groq_provider: Optional[GroqProvider] = None,
        gemini_provider: Optional[GeminiProvider] = None,
        local_provider: Optional[LocalProvider] = None,
    ):
        self.groq_provider = groq_provider or GroqProvider()
        self.gemini_provider = gemini_provider or GeminiProvider()
        self.local_provider = local_provider or LocalProvider()

    def resolve_tier(self, tier: str) -> Tuple[str, str]:
        """
        Map a logical model tier to its configured (provider_name, model_name).
        Does NOT hardcode any specific provider into the router or tiers.
        """
        tier_clean = tier.lower().strip()
        if tier_clean == "small":
            return (settings.SMALL_PROVIDER.lower(), settings.SMALL_MODEL)
        elif tier_clean == "medium":
            return (settings.MEDIUM_PROVIDER.lower(), settings.MEDIUM_MODEL)
        elif tier_clean == "large":
            return (settings.LARGE_PROVIDER.lower(), settings.LARGE_MODEL)
        else:
            raise ValueError(
                f"Unknown logical tier '{tier}'. Supported tiers: 'small', 'medium', 'large'."
            )

    def get_provider(self, provider_name: str) -> ModelProvider:
        """Retrieve the provider instance by normalized name."""
        name = provider_name.lower().strip()
        if name == "groq":
            return self.groq_provider
        elif name in ("gemini", "google"):
            return self.gemini_provider
        elif name in ("ollama", "local"):
            return self.local_provider
        else:
            raise ProviderUnavailableError(
                f"Unsupported model provider '{provider_name}'. Supported providers: 'groq', 'gemini', 'ollama'."
            )

    def dispatch(self, tier: str, prompt: str, **kwargs) -> ProviderResponse:
        """
        Execute inference for a given logical tier.
        1. Resolves tier to (provider_name, model_name).
        2. Retrieves the provider.
        3. Executes the prompt on the configured model.
        """
        provider_name, model_name = self.resolve_tier(tier)
        provider = self.get_provider(provider_name)

        # For Ollama/local provider when explicitly selected as tier:
        # Do not silently fabricate mock responses unless allow_fallback is explicitly set
        if provider_name in ("ollama", "local") and "allow_fallback" not in kwargs:
            kwargs["allow_fallback"] = False

        try:
            return provider.generate(prompt, model=model_name, **kwargs)
        except ConnectionError as ce:
            raise ProviderUnavailableError(str(ce)) from ce
        except ValueError as ve:
            raise ProviderUnavailableError(str(ve)) from ve
        except Exception as e:
            raise RuntimeError(
                f"Inference failed on {provider_name} with model {model_name}: {str(e)}"
            ) from e

# Default system dispatcher instance
model_dispatcher = ModelDispatcher()
