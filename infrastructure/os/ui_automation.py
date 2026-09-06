# Cursor Bite — UI Automation (Future Provider)
# ============================================================
# Placeholder for Windows UI Automation integration.
#
# FUTURE: This module will use pywinauto or Windows UI Automation API
# to extract text and context from Windows applications.
#
# Currently a stub — the architecture supports adding this later
# as a ContextProvider implementation.

import logging
from typing import Optional

from domain.interfaces import ContextProvider, TextProvider
from domain.models import ContextSource, ProcessingResult
from utils.logger import get_logger

logger = get_logger("infrastructure.os.ui_automation")


class UIAutomationProvider(TextProvider):
    """Windows UI Automation provider (future implementation).

    This provider uses Windows UI Automation to extract text from
    UI elements under the cursor or in the foreground window.

    Currently a stub — implement when pywinauto/win32-ui-access
    integration is needed.
    """

    def name(self) -> str:
        return "Windows UI Automation"

    def source(self) -> ContextSource:
        return ContextSource.UI_AUTOMATION

    def is_available(self) -> bool:
        """Check if UI Automation is available.

        Currently always returns False (stub).
        """
        # Future: check if pywinauto or UIAutomationCore is available
        return False

    def extract(self) -> ProcessingResult:
        """Extract text from the UI element under the cursor.

        Currently returns a 'not implemented' result.
        """
        return ProcessingResult(
            success=False,
            error="UI Automation provider is not yet implemented.",
        )

    def extract_text(self) -> ProcessingResult:
        """Extract text only."""
        return self.extract()


# ── Placeholder note ───────────────────────────────────────────────

# To implement this in the future:
#
# 1. Install pywinauto:  pip install pywinauto
# 2. Use uiawrapper to find elements under cursor
# 3. Extract text from the focused/nearest element
# 4. Integrate as a ContextProvider in the pipeline
#
# Example (future):
#     from pywinauto import Desktop
#     desktop = Desktop()
#     element = desktop.from_point(x, y)
#     text = element.window_text()
