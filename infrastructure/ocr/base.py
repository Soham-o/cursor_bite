# Cursor Bite — OCR Provider Base
# ============================================================
# Abstract base class for OCR providers.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.models import OCRResult


class BaseOCRProvider(ABC):
    """Base class for OCR (Optical Character Recognition) providers.

    Implementations:
    - TesseractOCRProvider: Uses Tesseract OCR engine
    - PaddleOCRProvider: Uses PaddleOCR (future)
    """

    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the OCR engine."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the OCR engine is installed and functional."""

    @abstractmethod
    def recognize(self, image_bytes: bytes) -> OCRResult:
        """Recognize text in an image.

        Args:
            image_bytes: Raw image data (PNG, JPEG, etc.)

        Returns:
            OCRResult with extracted text and confidence score.
        """

    @abstractmethod
    def recognize_image(self, image) -> OCRResult:
        """Recognize text from a PIL Image object.

        Args:
            image: PIL Image object.

        Returns:
            OCRResult with extracted text.
        """
