# Cursor Bite — Selected Text Provider
# ============================================================
# The concrete TextProvider the pipeline runs on: reads whatever
# the user currently has selected in the foreground application.
#
# There is no cross-application "get selection" API on Windows that
# works without accessibility hooks, so this uses the clipboard-safe
# pattern:
#
#   1. Snapshot the clipboard (so we can tell selection from leftovers)
#   2. Arm a restore
#   3. Send Ctrl+C to the foreground window
#   4. Poll the clipboard until it changes (or we give up)
#   5. Restore the original clipboard — ALWAYS, in a finally block
#
# WHY THE SNAPSHOT COMPARISON MATTERS:
#   If the user has nothing selected, Ctrl+C is a no-op and the
#   clipboard still holds whatever was there before. Reading it blindly
#   would silently process unrelated content — possibly something the
#   user copied from a password manager. So we compare against the
#   snapshot and report the true source (selection vs. clipboard) on
#   the result, letting the UI say which one it used.
#
# IMPORTANT: This module does NOT touch the clipboard on import.
#
# THREAD SAFETY: extract_text() is guarded by a lock. The controller can
# legitimately trigger two extractions close together — an opportunistic
# capture kicked off the moment the menu opens, and a second one if the
# user picks an action before the first has resolved — and both go
# through the single module-level `clipboard` snapshot/restore slot.
# Without serializing them, two concurrent save() calls would silently
# race and could hand one caller back the other's snapshot instead of
# the user's real clipboard.

import threading
import time
from typing import Optional

from config.settings import settings
from domain.interfaces import TextProvider
from domain.models import ContextSource, ProcessingResult
from infrastructure.os.clipboard import clipboard, simulate_copy_selection
from utils.logger import get_logger

logger = get_logger("infrastructure.os.selected_text")


# ── Timing ─────────────────────────────────────────────────────────

_COPY_POLL_INTERVAL = 0.04
"""Seconds between clipboard polls after sending Ctrl+C."""

_COPY_POLL_ATTEMPTS = 12
"""Max polls (~480ms total). Slow apps (Office, Electron, Chrome) need the headroom."""


# ── Selected Text Provider ─────────────────────────────────────────

class SelectedTextProvider(TextProvider):
    """Reads the user's current selection via the clipboard-safe pattern.

    Availability is unconditional on Windows — there is no optional
    dependency to probe beyond pyperclip, which is a hard requirement of
    the module. Nothing is validated or accessed until extract() is called.
    """

    def __init__(
        self,
        allow_clipboard_fallback: bool = True,
    ) -> None:
        """Args:
            allow_clipboard_fallback: When no selection is detected, fall
                back to the existing clipboard contents. The fallback is
                always reported in the result metadata so the UI can label
                it. Set False for a selection-only provider.
        """
        self._allow_clipboard_fallback = allow_clipboard_fallback
        self._lock = threading.Lock()

    # ── Interface Implementation ────────────────────────────────

    def name(self) -> str:
        return "Selected Text (Clipboard-Safe)"

    def source(self) -> ContextSource:
        return ContextSource.SELECTED_TEXT

    def is_available(self) -> bool:
        return True

    def extract(self, target_hwnd: Optional[int] = None) -> ProcessingResult:
        """Extract the current selection. Same as extract_text()."""
        return self.extract_text(target_hwnd=target_hwnd)

    def extract_text(self, target_hwnd: Optional[int] = None) -> ProcessingResult:
        """Copy the selection and return it, restoring the clipboard.

        Args:
            target_hwnd: Optional HWND of window containing the selection.

        Returns:
            ProcessingResult whose metadata carries:
              - "context_source": "selected_text" or "clipboard"
              - "clipboard_restored": whether the original was written back
        """
        with self._lock:
            return self._extract_text_locked(target_hwnd=target_hwnd)

    def _extract_text_locked(self, target_hwnd: Optional[int] = None) -> ProcessingResult:
        """The actual extraction. Always called with `self._lock` held."""
        protect = settings.privacy_clipboard_protection

        # Snapshot first so we can distinguish a fresh copy from leftovers.
        before = clipboard.read()

        if protect:
            clipboard.save()

        restored = False
        try:
            if target_hwnd is not None:
                try:
                    simulate_copy_selection(target_hwnd=target_hwnd)
                except TypeError:
                    simulate_copy_selection()
            else:
                simulate_copy_selection()
            after = self._await_clipboard_change(before)

            if after is not None:
                logger.info("Selection captured from foreground window.")
                return ProcessingResult(
                    success=True,
                    data=after.strip(),
                    metadata={
                        "context_source": ContextSource.SELECTED_TEXT.value,
                        "clipboard_protected": protect,
                    },
                )

            # Ctrl+C produced nothing new — no selection in the active window.
            if self._allow_clipboard_fallback and before and before.strip():
                logger.info("No selection detected — falling back to clipboard contents.")
                return ProcessingResult(
                    success=True,
                    data=before.strip(),
                    metadata={
                        "context_source": ContextSource.CLIPBOARD.value,
                        "clipboard_protected": protect,
                    },
                )

            logger.info("No selection and no usable clipboard content.")
            return ProcessingResult(
                success=False,
                error="Nothing selected. Select some text, then press the hotkey.",
                metadata={"context_source": ContextSource.SELECTED_TEXT.value},
            )

        except Exception as e:
            logger.warning(f"Selection extraction failed: {type(e).__name__}")
            return ProcessingResult(
                success=False,
                error="Could not read the current selection.",
            )
        finally:
            # The restore must happen on every path, including exceptions.
            if protect:
                restored = clipboard.restore()
                if not restored:
                    logger.warning("Clipboard restore failed after extraction.")
            else:
                # Protection off: the copy deliberately stays on the
                # clipboard, but the in-memory snapshot is still dropped.
                clipboard.discard_saved()

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _await_clipboard_change(before: Optional[str]) -> Optional[str]:
        """Poll the clipboard until it differs from `before`.

        Returns:
            The new clipboard text, or None if it never changed or the
            new content is blank.
        """
        for _ in range(_COPY_POLL_ATTEMPTS):
            time.sleep(_COPY_POLL_INTERVAL)
            current = clipboard.read()
            if current and current != before and current.strip():
                return current
        return None


# ── Module-level instance (no clipboard access on import) ─────────

selected_text_provider = SelectedTextProvider()
"""Global selected-text provider instance. Touches nothing until used."""
