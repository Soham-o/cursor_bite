# Cursor Bite — Application Events
# ============================================================
# Event definitions for the application's event bus.
#
# The bus carries lifecycle and outcome events: the hotkey, the menu
# opening and closing, and whether an action completed. It deliberately
# does NOT carry the content of an action — payloads are action names,
# success flags, and counts, never the user's text.
#
# The hotkey is the one event with a real subscriber contract: the
# application emits HOTKEY_ACTIVATED and the controller acts on it, so
# there is exactly one path from keypress to menu.

import logging
from enum import Enum
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from utils.logger import get_logger

logger = get_logger("app.events")


# ── Event Types ────────────────────────────────────────────────────

class AppEvent(str, Enum):
    """Application-level event types."""

    HOTKEY_ACTIVATED = "hotkey_activated"
    """Global hotkey was pressed."""

    RADIAL_MENU_OPENED = "radial_menu_opened"
    """The radial menu was opened."""

    RADIAL_MENU_CLOSED = "radial_menu_closed"
    """The radial menu was closed."""

    ACTION_SELECTED = "action_selected"
    """User selected an action from the radial menu."""

    TEXT_EXTRACTED = "text_extracted"
    """Text was extracted from the current context."""

    TRANSLATION_COMPLETED = "translation_completed"
    """Translation finished (success or failure)."""

    OCR_COMPLETED = "ocr_completed"
    """OCR finished (success or failure)."""

    AI_COMPLETED = "ai_completed"
    """AI operation finished (success or failure)."""

    SEARCH_COMPLETED = "search_completed"
    """Search finished (success or failure)."""

    PRIVACY_BLOCKED = "privacy_blocked"
    """Privacy gateway blocked an operation."""

    SETTINGS_CHANGED = "settings_changed"
    """User changed settings."""

    COMPONENT_STATUS_CHANGED = "component_status_changed"
    """A component's availability status changed."""

    ERROR = "error"
    """An error occurred."""

    READY = "ready"
    """Application is fully initialized and ready."""


# ── Event Payload ──────────────────────────────────────────────────

class EventPayload:
    """Carries data with an event."""

    def __init__(
        self,
        event_type: AppEvent,
        data: Any = None,
        metadata: dict = None,
    ) -> None:
        self.event_type = event_type
        self.data = data
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"EventPayload({self.event_type.value}, data={type(self.data).__name__})"


# ── Event Bus ──────────────────────────────────────────────────────

class EventBus(QObject):
    """Central event bus for application-wide events.

    Uses PyQt signals for thread-safe event delivery.
    UI components connect to the bus to receive events.
    Background workers emit events when operations complete.
    """

    # ── Generic Signal ──────────────────────────────────────────

    event = pyqtSignal(AppEvent, object)
    """Emitted for any application event with its payload."""

    # ── Convenience Signals ─────────────────────────────────────

    hotkey_activated = pyqtSignal()
    radial_menu_opened = pyqtSignal()
    radial_menu_closed = pyqtSignal()
    action_selected = pyqtSignal(str)
    translation_done = pyqtSignal(str, str)
    ocr_done = pyqtSignal(str, float)
    ai_done = pyqtSignal(str, bool)
    search_done = pyqtSignal(list)
    error_occurred = pyqtSignal(str, str)
    ready = pyqtSignal()

    # ── Emission ────────────────────────────────────────────────

    def emit(self, event_type: AppEvent, data: Any = None, metadata: dict = None) -> None:
        """Emit an event with optional data.

        Args:
            event_type: The type of event.
            data: Optional data payload.
            metadata: Optional metadata dict.
        """
        payload = EventPayload(event_type, data, metadata)
        self.event.emit(event_type, payload)

        # Emit convenience signals for common events
        if event_type == AppEvent.HOTKEY_ACTIVATED:
            self.hotkey_activated.emit()
        elif event_type == AppEvent.RADIAL_MENU_OPENED:
            self.radial_menu_opened.emit()
        elif event_type == AppEvent.RADIAL_MENU_CLOSED:
            self.radial_menu_closed.emit()
        elif event_type == AppEvent.ACTION_SELECTED:
            self.action_selected.emit(str(data) if data else "")
        elif event_type == AppEvent.ERROR:
            self.error_occurred.emit(
                metadata.get("source", "unknown") if metadata else "unknown",
                str(data) if data else "Unknown error",
            )
        elif event_type == AppEvent.READY:
            self.ready.emit()

    def on_hotkey(self, callback) -> None:
        """Connect to hotkey activated event."""
        self.hotkey_activated.connect(callback)

    def on_action(self, callback) -> None:
        """Connect to action selected event."""
        self.action_selected.connect(callback)

    def on_error(self, callback) -> None:
        """Connect to error event."""
        self.error_occurred.connect(callback)

    def on_ready(self, callback) -> None:
        """Connect to ready event."""
        self.ready.connect(callback)


# ── Module-level Event Bus ─────────────────────────────────────────

event_bus = EventBus()
"""Global event bus instance."""
