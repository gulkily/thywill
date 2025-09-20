"""Configuration helpers for selecting and validating AI providers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

SUPPORTED_PROVIDERS = {"anthropic", "openai"}
DEFAULT_PROVIDER = "anthropic"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class AIConfigurationError(RuntimeError):
    """Raised when AI provider configuration is invalid."""


@dataclass(frozen=True)
class AIProviderConfig:
    """Resolved configuration for AI providers."""

    provider: str
    anthropic_api_key: Optional[str]
    openai_api_key: Optional[str]
    openai_model: str
    openai_api_base: Optional[str]

    @property
    def using_anthropic(self) -> bool:
        return self.provider == "anthropic"

    @property
    def using_openai(self) -> bool:
        return self.provider == "openai"


def get_ai_provider_config() -> AIProviderConfig:
    """Return the resolved AI provider configuration from environment variables."""

    provider = os.getenv("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise AIConfigurationError(
            f"Unsupported AI provider '{provider}'. Supported providers: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
        )

    return AIProviderConfig(
        provider=provider,
        anthropic_api_key=_get_env("ANTHROPIC_API_KEY"),
        openai_api_key=_get_env("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip(),
        openai_api_base=_get_env("OPENAI_API_BASE"),
    )


def validate_ai_provider_config(raise_error: bool = True) -> Tuple[bool, Optional[str]]:
    """Validate provider configuration and optionally raise errors."""

    try:
        config = get_ai_provider_config()
    except AIConfigurationError as exc:
        if raise_error:
            raise
        return False, str(exc)

    if config.using_anthropic and not config.anthropic_api_key:
        message = "ANTHROPIC_API_KEY must be set when AI_PROVIDER=anthropic."
        if raise_error:
            raise AIConfigurationError(message)
        return False, message

    if config.using_openai and not config.openai_api_key:
        message = "OPENAI_API_KEY must be set when AI_PROVIDER=openai."
        if raise_error:
            raise AIConfigurationError(message)
        return False, message

    return True, None


def _get_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value:
        value = value.strip()
    return value or None
