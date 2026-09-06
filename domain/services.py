# Cursor Bite — Domain Services
# ============================================================
# High-level service orchestration. These services coordinate
# multiple providers to deliver end-to-end functionality.
#
# Milestone 1 Note:
#   These services are NOT used in Milestone 1. They exist for
#   future milestones (translation, OCR, AI, search).
#   The module is importable but performs no initialization.

from __future__ import annotations

from typing import Optional


from domain.interfaces import (
    AIProvider,
    OCRProvider,
    SearchProvider,
    TextProvider,
    TranslationProvider,
)
from domain.models import (
    AIResult,
    OCRResult,
    ProcessingResult,
    SearchResult,
    TranslationResult,
)


# ── Translation Service ────────────────────────────────────────────

class TranslationService:
    """Orchestrates translation with language detection and fallback.

    NOT used in Milestone 1. Exists for Milestone 2+.
    """

    def __init__(self, provider: TranslationProvider) -> None:
        self._provider = provider

    def translate_to_english(
        self,
        text: str,
        source_lang: Optional[str] = None,
        auto_detect: bool = True,
    ) -> TranslationResult:
        """Translate text to English.

        Args:
            text: Text to translate.
            source_lang: Known source language (optional).
            auto_detect: Whether to auto-detect if source_lang is unknown.

        Returns:
            TranslationResult with English translation.
        """
        if not text or not text.strip():
            return TranslationResult(
                success=False,
                error="No text to translate.",
                original_text=text,
                target_language="en",
            )

        detected_lang: Optional[str] = None
        if source_lang is None and auto_detect:
            try:
                detected_lang = self._provider.detect_language(text)
            except Exception:
                pass

        source = source_lang or detected_lang

        try:
            result = self._provider.translate(
                text=text,
                source_lang=source,
                target_lang="en",
            )
            result.source_language = source
            result.original_text = text
            return result
        except Exception as e:
            return TranslationResult(
                success=False,
                error=str(e),
                original_text=text,
                target_language="en",
                source_language=source,
            )

    def is_available(self) -> bool:
        return self._provider.is_available()


# ── OCR Service ────────────────────────────────────────────────────

class OCRService:
    """Orchestrates OCR with validation.

    NOT used in Milestone 1. Exists for Milestone 3+.
    """

    def __init__(self, provider: OCRProvider) -> None:
        self._provider = provider

    def extract_text(self, image_bytes: bytes) -> OCRResult:
        """Extract text from image bytes using OCR."""
        if not image_bytes:
            return OCRResult(
                success=False,
                error="No image data provided.",
            )
        try:
            return self._provider.recognize(image_bytes)
        except Exception as e:
            return OCRResult(
                success=False,
                error=str(e),
            )

    def is_available(self) -> bool:
        return self._provider.is_available()


# ── AI Service ─────────────────────────────────────────────────────

class AIService:
    """Orchestrates AI operations with common prompts.

    NOT used in Milestone 1. Exists for Milestone 4+.
    """

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    def explain(self, text: str, temperature: float = 0.7) -> AIResult:
        """Explain the given text in simple terms."""
        if not self._provider.is_available():
            return AIResult(
                success=False,
                error="AI provider is not available.",
            )
        if not text or not text.strip():
            return AIResult(
                success=False,
                error="No text to explain.",
            )

        system = "You are a helpful explainer. Explain the given text in simple, clear terms. Be concise."
        prompt = f"Please explain the following text in simple terms:\n\n{text}"

        try:
            return self._provider.generate(
                prompt=prompt,
                system_prompt=system,
                temperature=temperature,
            )
        except Exception as e:
            return AIResult(
                success=False,
                error=str(e),
            )

    def summarize(self, text: str, temperature: float = 0.5) -> AIResult:
        """Summarize the given text concisely."""
        if not self._provider.is_available():
            return AIResult(
                success=False,
                error="AI provider is not available.",
            )
        if not text or not text.strip():
            return AIResult(
                success=False,
                error="No text to summarize.",
            )

        system = "You are a helpful summarizer. Provide a concise summary of the given text. Be accurate and don't add information not in the original."
        prompt = f"Please summarize the following text:\n\n{text}"

        try:
            return self._provider.generate(
                prompt=prompt,
                system_prompt=system,
                temperature=temperature,
            )
        except Exception as e:
            return AIResult(
                success=False,
                error=str(e),
            )

    def rewrite(self, text: str, temperature: float = 0.7) -> AIResult:
        """Rewrite the given text to improve clarity."""
        if not self._provider.is_available():
            return AIResult(
                success=False,
                error="AI provider is not available.",
            )
        if not text or not text.strip():
            return AIResult(
                success=False,
                error="No text to rewrite.",
            )

        system = "You are a helpful writing assistant. Rewrite the given text to improve clarity, flow, and readability while preserving the original meaning."
        prompt = f"Please rewrite the following text to improve it:\n\n{text}"

        try:
            return self._provider.generate(
                prompt=prompt,
                system_prompt=system,
                temperature=temperature,
            )
        except Exception as e:
            return AIResult(
                success=False,
                error=str(e),
            )

    def ask(self, text: str, question: str, temperature: float = 0.7) -> AIResult:
        """Ask a question about the given text."""
        if not self._provider.is_available():
            return AIResult(
                success=False,
                error="AI provider is not available.",
            )
        if not text or not text.strip():
            return AIResult(
                success=False,
                error="No text to ask about.",
            )
        if not question or not question.strip():
            return AIResult(
                success=False,
                error="No question provided.",
            )

        system = "You are a helpful assistant. Answer the user's question based on the provided text. If the answer is not in the text, say so."
        prompt = f"Text:\n{text}\n\nQuestion: {question}"

        try:
            return self._provider.generate(
                prompt=prompt,
                system_prompt=system,
                temperature=temperature,
            )
        except Exception as e:
            return AIResult(
                success=False,
                error=str(e),
            )

    def is_available(self) -> bool:
        return self._provider.is_available()


# ── Search Service ─────────────────────────────────────────────────

class SearchService:
    """Orchestrates web search.

    NOT used in Milestone 1. Exists for Milestone 5+.
    """

    def __init__(self, provider: SearchProvider) -> None:
        self._provider = provider

    def search(self, query: str, max_results: int = 5) -> SearchResult:
        """Search the web for the given query."""
        if not query or not query.strip():
            return SearchResult(
                success=False,
                error="No search query provided.",
            )
        try:
            return self._provider.search(query, max_results=max_results)
        except Exception as e:
            return SearchResult(
                success=False,
                error=str(e),
                query=query,
            )

    def is_available(self) -> bool:
        return self._provider.is_available()


# ── Clipboard Service ──────────────────────────────────────────────

class ClipboardService:
    """Safe clipboard operations with save/restore pattern.

    NOT used in Milestone 1. Exists for Milestone 2+.
    """

    def __init__(self, provider: TextProvider) -> None:
        self._provider = provider

    def safe_extract(self) -> ProcessingResult:
        """Extract text using the safe clipboard pattern."""
        return self._provider.extract_text()

    def is_available(self) -> bool:
        return self._provider.is_available()
