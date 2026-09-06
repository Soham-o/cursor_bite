# Cursor Bite — AI Provider Base
# ============================================================
# Abstract base class for AI providers (local LLM inference).

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

from domain.models import AIResult


class BaseAIProvider(ABC):
    """Base class for AI providers.

    Implementations:
    - OllamaAIProvider: Uses Ollama local LLM runtime
    - LlamaCppProvider: Uses llama.cpp (future)
    """

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the AI runtime is available and responsive."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AIResult:
        """Generate a response from the AI model.

        Args:
            prompt: The user's prompt/text.
            system_prompt: Optional system instruction.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in response.

        Returns:
            AIResult with the generated text.
        """

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AIResult:
        """Generate a response, progressively invoking on_token(token) as tokens arrive.

        Default implementation falls back to non-streaming generate().
        """
        result = self.generate(prompt, system_prompt, temperature, max_tokens)
        if result.success and result.data and on_token:
            on_token(result.data)
        return result

    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models."""

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model name."""
