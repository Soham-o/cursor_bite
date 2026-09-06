# Cursor Bite — Screen Capture
# ============================================================
# Uses mss for fast, low-level screen capture.
# Supports single and multi-monitor setups.
# All capture is done in memory — no screenshots are saved to disk
# unless explicitly configured (privacy requirement).

import logging
from typing import Optional, Tuple

import mss
import mss.tools
from PIL import Image

from utils.logger import get_logger

logger = get_logger("infrastructure.os.screen_capture")


class ScreenCapture:
    """Screen capture using mss (fast, cross-platform).

    Captures are performed in memory only. No files are written
    unless explicitly requested (which is disabled by default
    for privacy reasons).
    """

    def __init__(self) -> None:
        self._monitors: list[dict] = []
        self._primary_monitor: Optional[dict] = None

    def _refresh_monitors(self) -> None:
        """Detect available monitors."""
        with mss.mss() as sct:
            self._monitors = sct.monitors
            # monitors[0] is the full virtual screen
            # monitors[1:] are individual monitors
            self._primary_monitor = self._monitors[1] if len(self._monitors) > 1 else self._monitors[0]

    def _ensure_monitors(self) -> None:
        """Lazy monitor enumeration.

        Deliberately NOT called from __init__: the module-level singleton
        below is created at import time, and enumerating monitors touches
        the display. Startup must not initialize optional components.
        """
        if not self._monitors:
            self._refresh_monitors()

    # ── Properties ──────────────────────────────────────────────

    @property
    def monitor_count(self) -> int:
        """Number of monitors (including virtual screen)."""
        self._ensure_monitors()
        return len(self._monitors)

    @property
    def primary_monitor(self) -> dict:
        """Primary monitor info dict from mss."""
        self._ensure_monitors()
        return self._primary_monitor or self._monitors[0]

    @property
    def virtual_screen(self) -> dict:
        """Full virtual screen (all monitors combined)."""
        self._ensure_monitors()
        return self._monitors[0]

    # ── Capture Methods ─────────────────────────────────────────

    def capture_screen(self, monitor_index: int = 1) -> Optional[Image.Image]:
        """Capture an entire monitor.

        Args:
            monitor_index: Monitor index (1 = primary, 2 = secondary, etc.).
                           Use 0 for the full virtual screen.

        Returns:
            PIL Image of the captured screen, or None on failure.
        """
        try:
            self._ensure_monitors()

            if monitor_index >= len(self._monitors):
                logger.warning(f"Monitor index {monitor_index} out of range (max: {len(self._monitors) - 1})")
                monitor_index = 1

            monitor = self._monitors[monitor_index]
            with mss.mss() as sct:
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                logger.debug(f"Screen captured: monitor {monitor_index}, size {img.size}")
                return img
        except Exception as e:
            logger.error(f"Screen capture failed: {e}", exc_info=True)
            return None

    def capture_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        monitor_index: int = 0,
    ) -> Optional[Image.Image]:
        """Capture a specific region of the screen.

        Args:
            left: Left coordinate (relative to the monitor's top-left).
            top: Top coordinate.
            width: Region width.
            height: Region height.
            monitor_index: Which monitor the region is on (0 = virtual screen).

        Returns:
            PIL Image of the captured region, or None on failure.
        """
        try:
            self._ensure_monitors()
            monitor = self._monitors[monitor_index]
            # Adjust coordinates relative to the monitor
            monitor_left = monitor["left"]
            monitor_top = monitor["top"]

            region = {
                "left": monitor_left + left,
                "top": monitor_top + top,
                "width": width,
                "height": height,
            }

            with mss.mss() as sct:
                screenshot = sct.grab(region)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                logger.debug(f"Region captured: {width}x{height} at ({left}, {top})")
                return img
        except Exception as e:
            logger.error(f"Region capture failed: {e}", exc_info=True)
            return None

    def capture_virtual_screen(self) -> Optional[Image.Image]:
        """Capture the entire virtual screen (all monitors)."""
        return self.capture_screen(monitor_index=0)

    def capture_absolute_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> Optional[Image.Image]:
        """Capture a region given in absolute virtual-screen coordinates.

        Unlike capture_region(), no monitor offset is applied. Windows'
        virtual-screen coordinate space is the same one Qt reports for
        global positions, so a QRect straight out of the region selector
        can be passed here unmodified — including negative origins on
        multi-monitor setups where a display sits left of / above primary.

        Returns:
            PIL Image of the captured region, or None on failure.
        """
        if width <= 0 or height <= 0:
            logger.warning("Absolute region capture requested with empty size.")
            return None

        try:
            region = {"left": left, "top": top, "width": width, "height": height}
            with mss.mss() as sct:
                screenshot = sct.grab(region)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                logger.debug(f"Absolute region captured: {width}x{height} at ({left}, {top})")
                return img
        except Exception as e:
            logger.error(f"Absolute region capture failed: {e}", exc_info=True)
            return None

    # ── Byte Output (for OCR pipeline) ──────────────────────────

    def capture_absolute_region_to_bytes(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        format: str = "PNG",
    ) -> Optional[bytes]:
        """Capture an absolute-coordinate region and return image bytes.

        This is the entry point used by the Capture Text (OCR) action.
        Nothing is written to disk — the image only ever exists in memory.
        """
        img = self.capture_absolute_region(left, top, width, height)
        if img is None:
            return None
        return self._to_bytes(img, format)

    def capture_to_bytes(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        format: str = "PNG",
    ) -> Optional[bytes]:
        """Capture a region and return as bytes (PNG by default).

        Useful for passing to OCR engines without saving files.

        Args:
            left, top, width, height: Region to capture.
            format: Image format (PNG, JPEG, etc.).

        Returns:
            Bytes of the captured image, or None on failure.
        """
        img = self.capture_region(left, top, width, height)
        if img is None:
            return None
        return self._to_bytes(img, format)

    @staticmethod
    def _to_bytes(img: Image.Image, format: str = "PNG") -> Optional[bytes]:
        """Encode a PIL image to bytes in memory."""
        try:
            from io import BytesIO
            buffer = BytesIO()
            img.save(buffer, format=format)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Failed to convert capture to bytes: {e}")
            return None

    # ── DPI / Scaling ───────────────────────────────────────────

    def get_scaling_factor(self, monitor_index: int = 1) -> float:
        """Get the DPI scaling factor for a monitor.

        Returns:
            Scaling factor (1.0 = 100%, 1.5 = 150%, 2.0 = 200%).
        """
        try:
            import win32api
            import win32print

            hmonitor = win32api.MonitorFromWindow(
                0,  # HMONITOR_FROM_POINT
                2,  # MONITOR_DEFAULTTOPRIMARY
            )

            # Get DPI
            dpi_x = win32api.GetDeviceCaps(hmonitor, 88)  # LOGPIXELSX
            return dpi_x / 96.0  # 96 DPI is 100%
        except Exception as e:
            logger.debug(f"Could not get DPI scaling: {e}")
            return 1.0


# ── Module-level instance ──────────────────────────────────────────

screen_capture = ScreenCapture()
"""Global screen capture instance."""
