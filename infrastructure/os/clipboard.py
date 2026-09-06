# Cursor Bite — Safe Clipboard Service
# ============================================================
# Implements the clipboard-safe text extraction pattern:
#
#   1. Save existing clipboard content
#   2. Copy user's selection (done by caller)
#   3. Read the clipboard
#   4. Restore original clipboard content
#   5. NEVER maintain clipboard history
#
# IMPORTANT: This module does NOT access the clipboard on import.
# All clipboard operations are explicit method calls.

import logging
import time
from typing import Callable, Optional

import pyperclip

from utils.logger import get_logger

logger = get_logger("infrastructure.os.clipboard")


class SafeClipboard:
    """Safe clipboard operations with save/restore guarantee.

    The user's clipboard content is never lost during text extraction.
    """

    def __init__(self) -> None:
        self._saved_content: Optional[str] = None
        self._saved_content_set: bool = False

    # ── Save / Restore ──────────────────────────────────────────

    def save(self) -> bool:
        """Save the current clipboard content.

        Returns:
            True if clipboard was read successfully.
        """
        try:
            self._saved_content = pyperclip.paste()
            self._saved_content_set = True
            logger.debug("Clipboard content saved.")
            return True
        except Exception as e:
            logger.warning(f"Failed to save clipboard: {e}")
            self._saved_content = None
            self._saved_content_set = False
            return False

    def restore(self) -> bool:
        """Restore the previously saved clipboard content.

        ALWAYS call this after text extraction, even on failure.
        """
        if not self._saved_content_set:
            logger.debug("No clipboard content to restore.")
            return True

        try:
            pyperclip.copy(self._saved_content)
            logger.debug("Clipboard content restored.")
            return True
        except Exception as e:
            logger.error(f"Failed to restore clipboard: {e}")
            return False
        finally:
            self._saved_content = None
            self._saved_content_set = False

    def discard_saved(self) -> None:
        """Drop the saved clipboard content without writing it back.

        For callers that deliberately leave their copy on the clipboard
        (clipboard protection turned off). Still clears the in-memory copy
        so saved text is never retained after the operation.
        """
        self._saved_content = None
        self._saved_content_set = False
        logger.debug("Saved clipboard content discarded without restore.")

    @property
    def has_saved_content(self) -> bool:
        """Whether a save() is currently armed for restore."""
        return self._saved_content_set

    # ── Read / Write ────────────────────────────────────────────

    def read(self) -> Optional[str]:
        """Read current clipboard text.

        Returns:
            Clipboard text or None if reading fails.
        """
        try:
            text = pyperclip.paste()
            if text:
                logger.debug("Clipboard read: text available.")
            else:
                logger.debug("Clipboard is empty.")
            return text
        except Exception as e:
            logger.warning(f"Clipboard read failed: {e}")
            return None

    def write(self, text: str) -> bool:
        """Write text to clipboard.

        Args:
            text: Text to write.

        Returns:
            True if write succeeded.
        """
        try:
            pyperclip.copy(text)
            logger.debug("Clipboard write: text written.")
            return True
        except Exception as e:
            logger.error(f"Clipboard write failed: {e}")
            return False

    # ── Safe Extraction Workflow ─────────────────────────────────

    def safe_extract(
        self,
        copy_selection_fn: Optional[Callable] = None,
    ) -> Optional[str]:
        """Perform a safe clipboard extraction workflow.

        1. Save existing clipboard
        2. Optionally copy selection
        3. Read clipboard
        4. Restore original clipboard (always)

        Args:
            copy_selection_fn: Optional callable to copy the selection.

        Returns:
            Extracted text, or None if no text was available.
        """
        self.save()

        try:
            if copy_selection_fn is not None:
                try:
                    copy_selection_fn()
                    time.sleep(0.1)
                except Exception as e:
                    logger.warning(f"Copy selection failed: {e}")

            text = self.read()
            if text:
                return text
            return None
        finally:
            self.restore()


# ── Module-level instance ──────────────────────────────────────────

clipboard = SafeClipboard()
"""Global safe clipboard instance."""


# ── Copy Selection Helper ─────────────────────────────────────────

def simulate_copy_selection(target_hwnd: Optional[int] = None) -> None:
    """Simulate Ctrl+C to copy the current selection.

    Args:
        target_hwnd: Optional HWND of the window to target. If provided and
            not already foreground, attempts to restore foreground focus first.
    """
    try:
        import win32api
        import win32con
        import win32gui

        if target_hwnd:
            try:
                curr_hwnd = win32gui.GetForegroundWindow()
                if curr_hwnd != target_hwnd:
                    win32gui.SetForegroundWindow(target_hwnd)
                    time.sleep(0.04)
            except Exception as e:
                logger.debug(f"Could not restore target window {target_hwnd}: {e}")

        # If user activated via Ctrl+Alt+B, ensure Alt and Windows keys are physically released
        # so Windows does not receive Ctrl+Alt+C instead of Ctrl+C
        for vk in (win32con.VK_MENU, win32con.VK_LMENU, win32con.VK_RMENU, win32con.VK_LWIN, win32con.VK_RWIN):
            try:
                if win32api.GetAsyncKeyState(vk) & 0x8000:
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                pass

        time.sleep(0.02)

        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord("C"), 0, 0, 0)
            win32api.keybd_event(ord("C"), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            logger.debug("Simulated Ctrl+C for selection copy.")
    except Exception as e:
        logger.warning(f"Failed to simulate copy: {e}")
