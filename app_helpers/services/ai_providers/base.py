"""Base classes and types for AI prayer generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PrayerGenerationResult:
    """Normalized result of a prayer generation request."""

    text: str
    raw_response: str
    provider: str
    metadata: Optional[Dict[str, Any]] = None


class PrayerGenerationError(RuntimeError):
    """Raised when an AI provider fails to generate a prayer."""


class PrayerGenerationProvider(ABC):
    """Abstract base class for AI providers that generate prayers."""

    name: str

    @abstractmethod
    def generate_prayer(
        self,
        prompt: str,
        *,
        system_prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
    ) -> PrayerGenerationResult:
        """Generate a prayer from the given prompt."""

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.__class__.__name__}(name={self.name!r})"
