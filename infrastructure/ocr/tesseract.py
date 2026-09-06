# Cursor Bite — Tesseract OCR Provider
# ============================================================
# Uses Tesseract OCR engine via pytesseract.
# Free, offline, open-source.
#
# LAZY INITIALIZATION: No validation is performed on import.
# The first call to is_available() or recognize() triggers validation.

import logging
import os
import subprocess
from typing import Optional

from PIL import Image

from domain.models import OCRResult
from infrastructure.ocr.base import BaseOCRProvider
from utils.logger import get_logger

logger = get_logger("infrastructure.ocr.tesseract")


# ── Find Tesseract ─────────────────────────────────────────────────

DEFAULT_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Tesseract-OCR\tesseract.exe",
]


def find_tesseract() -> Optional[str]:
    """Find the Tesseract executable on the system.

    Returns:
        Path to tesseract.exe, or None if not found.
    """
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.debug("Tesseract found in PATH.")
            return "tesseract"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    for path in DEFAULT_TESSERACT_PATHS:
        if os.path.exists(path):
            logger.debug(f"Tesseract found at: {path}")
            return path

    env_path = os.environ.get("TESSERACT_PATH", "")
    if env_path and os.path.exists(env_path):
        logger.debug(f"Tesseract found via TESSERACT_PATH: {env_path}")
        return env_path

    return None


# ── Tesseract OCR Provider ─────────────────────────────────────────

class TesseractOCRProvider(BaseOCRProvider):
    """Tesseract OCR implementation with lazy initialization.

    No validation is performed on __init__. The first call to
    is_available() or recognize() triggers validation.
    """

    def __init__(self) -> None:
        self._tesseract_path: Optional[str] = None
        self._available: Optional[bool] = None

    # ── Lazy Validation ─────────────────────────────────────────

    def _ensure_ready(self) -> bool:
        """Lazy validation — called on first use."""
        if self._available is not None:
            return self._available

        self._tesseract_path = find_tesseract()
        if self._tesseract_path is None:
            self._available = False
            logger.info("Tesseract OCR not found on system.")
            return False

        try:
            result = subprocess.run(
                [self._tesseract_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self._available = True
                logger.info("Tesseract OCR is available.")
                return True
            else:
                self._available = False
                logger.warning("Tesseract returned an error.")
                return False
        except Exception as e:
            self._available = False
            logger.warning(f"Tesseract validation failed: {e}")
            return False

    # ── Interface Implementation ────────────────────────────────

    def name(self) -> str:
        return "Tesseract OCR"

    def is_available(self) -> bool:
        return self._ensure_ready()

    def recognize(self, image_bytes: bytes) -> OCRResult:
        """Recognize text from image bytes. Lazy initialization on first call."""
        if not self._ensure_ready():
            return OCRResult(
                success=False,
                error="Tesseract OCR is not available. Install Tesseract to use OCR.",
            )

        if not image_bytes:
            return OCRResult(success=False, error="No image data provided.")

        try:
            from io import BytesIO
            from PIL import Image as PILImage
            import pytesseract

            img = PILImage.open(BytesIO(image_bytes))

            if self._tesseract_path and self._tesseract_path != "tesseract":
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_path

            text = pytesseract.image_to_string(img)
            cleaned_text = self._clean_text(text)
            confidence = self._get_confidence(img)

            logger.info(f"OCR completed. Characters: {len(cleaned_text)}.")

            return OCRResult(
                success=True,
                data=cleaned_text,
                source_image_size=img.size,
                confidence=confidence,
            )
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return OCRResult(success=False, error=f"OCR failed: {str(e)}")

    def recognize_file(self, image_path: str) -> OCRResult:
        """Recognize text from an image file on disk."""
        if not self._ensure_ready():
            return OCRResult(
                success=False,
                error="Tesseract OCR is not available.",
            )

        if not image_path:
            return OCRResult(success=False, error="No image path provided.")

        try:
            from PIL import Image as PILImage

            img = PILImage.open(image_path)
            return self.recognize_image(img)
        except FileNotFoundError:
            return OCRResult(success=False, error=f"Image file not found: {image_path}")
        except Exception as e:
            logger.error(f"OCR from file failed: {e}")
            return OCRResult(success=False, error=f"OCR failed: {str(e)}")

    def recognize_image(self, image) -> OCRResult:
        """Recognize text from a PIL Image. Lazy initialization on first call."""
        if not self._ensure_ready():
            return OCRResult(
                success=False,
                error="Tesseract OCR is not available.",
            )

        try:
            import pytesseract

            if self._tesseract_path and self._tesseract_path != "tesseract":
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_path

            text = pytesseract.image_to_string(image)
            cleaned_text = self._clean_text(text)
            confidence = self._get_confidence(image)

            logger.info(f"OCR from image completed. Characters: {len(cleaned_text)}.")

            return OCRResult(
                success=True,
                data=cleaned_text,
                source_image_size=image.size,
                confidence=confidence,
            )
        except Exception as e:
            logger.error(f"OCR from image failed: {e}")
            return OCRResult(success=False, error=f"OCR failed: {str(e)}")

    # ── Helpers ─────────────────────────────────────────────────

    def invalidate(self) -> None:
        """Forget the cached availability check so the next call re-probes.

        Used by the Components dialog's "Re-check" button so a user who
        installs Tesseract while Cursor Bite is running does not have to
        restart the app.
        """
        self._available = None
        self._tesseract_path = None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean up OCR output text."""
        if not text:
            return ""
        import re

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            cleaned = re.sub(r"  +", " ", line).strip()
            if cleaned:
                cleaned_lines.append(cleaned)
        return "\n".join(cleaned_lines)

    @staticmethod
    def _get_confidence(image) -> float:
        """Get OCR confidence score (0.0 to 1.0)."""
        try:
            import pytesseract

            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = []
            for conf in data.get("conf", []):
                try:
                    c = float(conf)
                    if 0 < c < 100:
                        confidences.append(c)
                except (ValueError, TypeError):
                    pass
            if confidences:
                return sum(confidences) / len(confidences) / 100.0
            return 0.0
        except Exception:
            return 0.0


# ── Module-level instance (lazy — no validation on import) ────────

tesseract_ocr = TesseractOCRProvider()
"""Global Tesseract OCR provider instance. No validation on import."""
