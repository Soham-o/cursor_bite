# Cursor Bite — Cursor Position Detection
# ============================================================
# Detects the current mouse cursor position on screen.
# Returns QPoint for compatibility with PyQt6 geometry operations.
# Supports multi-monitor setups and virtual screen coordinates.

import logging
from typing import Tuple

import win32api
from PyQt6.QtCore import QPoint

from utils.logger import get_logger

logger = get_logger("infrastructure.os.cursor")


# ── Virtual Screen Geometry ────────────────────────────────────────

def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """Get the bounds of the entire virtual screen (all monitors).

    Returns:
        Tuple of (left, top, width, height) in pixels.
    """
    left = win32api.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
    top = win32api.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN
    width = win32api.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    height = win32api.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return (left, top, width, height)


def get_monitor_count() -> int:
    """Get the number of connected monitors."""
    return win32api.GetSystemMetrics(80)  # SM_CMONITORS


# ── Cursor Position ────────────────────────────────────────────────

def get_cursor_position() -> QPoint:
    """Get the current cursor position in virtual screen coordinates.

    Returns:
        QPoint with x, y pixel coordinates relative to the virtual
        screen origin (all monitors combined).
    """
    try:
        from PyQt6.QtGui import QCursor
        return QCursor.pos()
    except Exception:
        pass

    try:
        x, y = win32api.GetCursorPos()
        return QPoint(x, y)
    except Exception as e:
        logger.debug(f"win32api cursor lookup failed: {e}")
        bounds = get_virtual_screen_bounds()
        return QPoint(
            bounds[0] + bounds[2] // 2,
            bounds[1] + bounds[3] // 2,
        )


def get_cursor_position_tuple() -> Tuple[int, int]:
    """Get the current cursor position as a plain tuple.

    Returns:
        Tuple of (x, y) pixel coordinates.
    """
    pos = get_cursor_position()
    return (pos.x(), pos.y())


# ── Screen Edge Detection ──────────────────────────────────────────

def is_cursor_near_edge(
    margin: int = 50,
) -> dict:
    """Check if the cursor is near screen edges.

    Args:
        margin: Pixels from edge to consider "near".

    Returns:
        Dict with boolean flags for each edge and corner.
    """
    pos = get_cursor_position()
    x, y = pos.x(), pos.y()
    left, top, width, height = get_virtual_screen_bounds()

    right_edge = left + width
    bottom_edge = top + height

    return {
        "left": x < left + margin,
        "right": x > right_edge - margin,
        "top": y < top + margin,
        "bottom": y > bottom_edge - margin,
        "corner_tl": x < left + margin and y < top + margin,
        "corner_tr": x > right_edge - margin and y < top + margin,
        "corner_bl": x < left + margin and y > bottom_edge - margin,
        "corner_br": x > right_edge - margin and y > bottom_edge - margin,
    }
