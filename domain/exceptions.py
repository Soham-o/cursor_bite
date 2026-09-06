# Cursor Bite — Domain Exceptions
# ============================================================
# All custom exceptions used across the application.
# Each exception includes a clear, actionable message.

from __future__ import annotations


class CursorBiteError(Exception):
    """Base exception for all Cursor Bite errors."""

    pass


class ProviderUnavailableError(CursorBiteError):
    """Raised when a required provider is not available.

    Example: Tesseract not installed, Ollama not running.
    """

    def __init__(self, provider_name: str, detail: str = "") -> None:
        self.provider_name = provider_name
        msg = f"Provider '{provider_name}' is not available."
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


class TranslationError(CursorBiteError):
    """Raised when translation fails."""

    def __init__(self, detail: str = "Translation failed.") -> None:
        super().__init__(detail)


class LanguageDetectionError(CursorBiteError):
    """Raised when language detection fails."""

    def __init__(self, detail: str = "Could not detect language.") -> None:
        super().__init__(detail)


class OCRTesseractError(CursorBiteError):
    """Raised when OCR fails."""

    def __init__(self, detail: str = "OCR failed to extract text.") -> None:
        super().__init__(detail)


class AIProviderError(CursorBiteError):
    """Raised when AI generation fails."""

    def __init__(self, detail: str = "AI provider error.") -> None:
        super().__init__(detail)


class SearchError(CursorBiteError):
    """Raised when web search fails."""

    def __init__(self, detail: str = "Search failed.") -> None:
        super().__init__(detail)


class PrivacyViolationError(CursorBiteError):
    """Raised when the Privacy Gateway blocks an operation.

    This is NOT an unexpected error — it's an intentional block.
    The UI should present this to the user as a warning/block notice.
    """

    def __init__(self, reason: str, sensitive_type: str = "") -> None:
        self.reason = reason
        self.sensitive_type = sensitive_type
        msg = f"Privacy block: {reason}"
        if sensitive_type:
            msg += f" (detected: {sensitive_type})"
        super().__init__(msg)


class ClipboardError(CursorBiteError):
    """Raised when clipboard operations fail."""

    def __init__(self, detail: str = "Clipboard operation failed.") -> None:
        super().__init__(detail)


class HotkeyRegistrationError(CursorBiteError):
    """Raised when global hotkey registration fails."""

    def __init__(self, detail: str = "Failed to register hotkey.") -> None:
        super().__init__(detail)


class ScreenCaptureError(CursorBiteError):
    """Raised when screen capture fails."""

    def __init__(self, detail: str = "Screen capture failed.") -> None:
        super().__init__(detail)


class ConfigurationError(CursorBiteError):
    """Raised when configuration is invalid."""

    def __init__(self, detail: str = "Invalid configuration.") -> None:
        super().__init__(detail)


class NoTextSelectedError(CursorBiteError):
    """Raised when no text is selected and the action requires it."""

    def __init__(self, detail: str = "No text selected.") -> None:
        super().__init__(detail)
