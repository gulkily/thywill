"""OpenAI-backed prayer generation provider."""

from __future__ import annotations

import importlib
from typing import Any, Optional

from .base import PrayerGenerationError, PrayerGenerationProvider, PrayerGenerationResult
from .config import AIProviderConfig, DEFAULT_OPENAI_MODEL


class OpenAIPrayerProvider(PrayerGenerationProvider):
    """Prayer generation provider that uses OpenAI models."""

    name = "openai"

    def __init__(self, config: AIProviderConfig) -> None:
        if not config.openai_api_key:
            raise PrayerGenerationError("OpenAI API key is missing.")

        try:
            openai_module = importlib.import_module("openai")
        except ModuleNotFoundError as exc:  # pragma: no cover - environment specific
            raise PrayerGenerationError(
                "OpenAI client not installed. Run 'pip install openai'."
            ) from exc

        client_kwargs = {
            "api_key": config.openai_api_key,
        }
        if config.openai_api_base:
            client_kwargs["base_url"] = config.openai_api_base

        self._client = openai_module.OpenAI(**client_kwargs)
        self._model = config.openai_model or DEFAULT_OPENAI_MODEL

    def generate_prayer(
        self,
        prompt: str,
        *,
        system_prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
    ) -> PrayerGenerationResult:
        try:
            response = self._client.responses.create(
                model=self._model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:  # pragma: no cover - SDK diversely errors
            raise PrayerGenerationError(str(exc)) from exc

        text = _extract_text(response)

        return PrayerGenerationResult(
            text=text,
            raw_response=text,
            provider=self.name,
            metadata={"model": self._model},
        )


def _extract_text(response: Any) -> str:
    """Extract the first textual response from an OpenAI response object."""
    output_text: Optional[str] = getattr(response, "output_text", None)
    if output_text:
        return output_text.strip()

    output = getattr(response, "output", None) or []
    for item in output:
        content = getattr(item, "content", None) or []
        for block in content:
            text = getattr(block, "text", None)
            if text:
                return text.strip()

    # Fall back to string representation if structure is unexpected
    return str(response).strip()
