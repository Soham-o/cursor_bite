# Cursor Bite — Provider Interfaces
# ============================================================
# Abstract base classes defining the contracts for all provider
# implementations. This enables swapping implementations without
# changing application code.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.models import (  # noqa: E402
    AIResult,
    ContextSource,
    OCRResult,
    ProcessingResult,
    SearchResult,
    TranslationResult,
)


# ── Context Provider ───────────────────────────────────────────────

class ContextProvider(ABC):
    """Provides context (text/content) from various sources.

    Implementations:
    - SelectedTextProvider: reads selected text via clipboard
    - ClipboardProvider: reads clipboard directly
    - ScreenRegionProvider: captures screen region
    - OCRProvider: extracts text from images
    """

    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this provider."""

    @abstractmethod
    def source(self) -> ContextSource:
        """The ContextSource this provider handles."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (dependencies installed, etc.)."""

    @abstractmethod
    def extract(self) -> ProcessingResult:
        """Extract context from the source.

        Returns a ProcessingResult with the extracted text/data.
        Should be fast — for expensive operations, use a separate method.
        """


# ── Text Provider (specialized ContextProvider) ────────────────────

class TextProvider(ContextProvider, ABC):
    """A ContextProvider that specifically provides text."""

    @abstractmethod
    def extract_text(self) -> ProcessingResult:
        """Extract text only. Lighter than full extract()."""


# ── OCR Provider ───────────────────────────────────────────────────

class OCRProvider(ABC):
    """Extracts text from images using OCR."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if OCR engine is installed and working."""

    @abstractmethod
    def recognize(self, image_bytes: bytes) -> OCRResult:
        """Extract text from an image (bytes).

        Args:
            image_bytes: Raw image data (PNG, JPEG, etc.)

        Returns:
            OCRResult with extracted text and confidence.
        """

    @abstractmethod
    def recognize_file(self, image_path: str) -> OCRResult:
        """Extract text from an image file on disk."""


# ── Translation Provider ───────────────────────────────────────────

class TranslationProvider(ABC):
    """Translates text from one language to another."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if translation engine is ready."""

    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: str = "en",
    ) -> TranslationResult:
        """Translate text.

        Args:
            text: Text to translate.
            source_lang: Source language code (ISO 639-1). If None, auto-detect.
            target_lang: Target language code (ISO 639-1). Defaults to English.

        Returns:
            TranslationResult with translated text.
        """

    @abstractmethod
    def detect_language(self, text: str) -> Optional[str]:
        """Detect the language of the given text.

        Returns:
            Language code (ISO 639-1) or None if detection fails.
        """

    @abstractmethod
    def supported_languages(self) -> list[str]:
        """List of language codes this provider supports."""


# ── AI Provider ────────────────────────────────────────────────────

class AIProvider(ABC):
    """Provides AI capabilities (explain, summarize, rewrite, ask)."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the AI runtime is available."""

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

    @abstractmethod
    def list_models(self) -> list[str]:
        """List available models."""

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model name."""


# ── Search Provider ────────────────────────────────────────────────

class SearchProvider(ABC):
    """Provides web search capabilities."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if search is available (internet, API key, etc.)."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> SearchResult:
        """Search the web.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            SearchResult with list of results.
        """


# ── Text-to-Speech Provider ────────────────────────────────────────

class TTSProvider(ABC):
    """Provides text-to-speech capabilities."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if TTS is available."""

    @abstractmethod
    def speak(self, text: str, language: Optional[str] = None) -> bool:
        """Speak the given text aloud.

        Args:
            text: Text to speak.
            language: Optional language code for voice selection.

        Returns:
            True if speech was initiated successfully.
        """
