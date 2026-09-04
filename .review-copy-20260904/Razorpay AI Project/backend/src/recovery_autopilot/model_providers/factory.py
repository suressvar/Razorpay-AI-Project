"""Factory for instantiating the configured model provider."""

from recovery_autopilot.config import Settings
from recovery_autopilot.config import settings as global_settings
from recovery_autopilot.model_providers.base import ModelProvider
from recovery_autopilot.model_providers.fake import FakeModelProvider
from recovery_autopilot.model_providers.gemini import GeminiProvider
from recovery_autopilot.model_providers.ollama import OllamaProvider


def get_model_provider(settings: Settings = global_settings) -> ModelProvider:
    """Create and return the active model provider according to configuration."""
    provider_type = settings.MODEL_PROVIDER.lower()

    if provider_type == "gemini":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
            temperature=settings.GEMINI_TEMPERATURE,
            timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
        )
    elif provider_type == "ollama":
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model_name=settings.OLLAMA_MODEL,
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        )
    else:  # "fake" or fallback
        return FakeModelProvider(
            provider_name="fake",
            model_identifier="heuristic-mock-v1",
        )
