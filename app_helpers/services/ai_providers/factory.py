"""Factory helpers for prayer generation providers."""

from __future__ import annotations

from functools import lru_cache

from .base import PrayerGenerationProvider
from .config import AIConfigurationError, get_ai_provider_config
from .anthropic_provider import AnthropicPrayerProvider
from .openai_provider import OpenAIPrayerProvider


@lru_cache(maxsize=1)
def get_prayer_generation_provider() -> PrayerGenerationProvider:
    """Return a singleton instance of the configured prayer generation provider."""

    config = get_ai_provider_config()

    if config.provider == "anthropic":
        return AnthropicPrayerProvider(config)

    if config.provider == "openai":
        return OpenAIPrayerProvider(config)

    raise AIConfigurationError(
        f"Unsupported AI provider '{config.provider}'."
    )
