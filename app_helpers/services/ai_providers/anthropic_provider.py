"""Anthropic-backed prayer generation provider."""

from __future__ import annotations

from typing import Any

import anthropic

from .base import PrayerGenerationError, PrayerGenerationProvider, PrayerGenerationResult
from .config import AIProviderConfig


class AnthropicPrayerProvider(PrayerGenerationProvider):
    """Prayer generation provider that uses Anthropic Claude models."""

    name = "anthropic"

    def __init__(self, config: AIProviderConfig) -> None:
        if not config.anthropic_api_key:
            raise PrayerGenerationError("Anthropic API key is missing.")
        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    def generate_prayer(
        self,
        prompt: str,
        *,
        system_prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
    ) -> PrayerGenerationResult:
        try:
            response = self._client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # pragma: no cover - underlying SDK raises various errors
            raise PrayerGenerationError(str(exc)) from exc

        text = _extract_text(response)
        return PrayerGenerationResult(
            text=text,
            raw_response=text,
            provider=self.name,
            metadata={"model": "claude-3-5-sonnet-20241022"},
        )


def _extract_text(response: Any) -> str:
    """Extract text content from an Anthropic response object."""
    content = getattr(response, "content", None) or []
    if content:
        first_item = content[0]
        text = getattr(first_item, "text", None)
        if text:
            return text.strip()
    # Fallback to string representation if structure unexpected
    return str(response).strip()
