# Cursor Bite — Translation Provider Base
# ============================================================
# Abstract base class for translation providers.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.models import TranslationResult


class BaseTranslationProvider(ABC):
    """Base class for translation providers.

    Implementations:
    - ArgosTranslationProvider: Uses Argos Translate (offline)
    - CloudTranslationProvider: Uses cloud API (future, optional)
    """

    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the translation engine is ready to use."""

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
            TranslationResult with the translated text.
        """

    @abstractmethod
    def detect_language(self, text: str) -> Optional[str]:
        """Detect the language of the given text.

        Args:
            text: Text to detect language of.

        Returns:
            Language code (ISO 639-1) or None if detection fails.
        """

    @abstractmethod
    def supported_languages(self) -> list[str]:
        """List of language codes this provider supports."""
