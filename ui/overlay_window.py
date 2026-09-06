# Cursor Bite — Overlay Window
# ============================================================
# Base overlay window for Cursor Bite UI components.
#
# Characteristics:
#   - Frameless, transparent window
#   - Always on top
#   - Stays within screen bounds
#   - Positioned relative to cursor
#   - Closes on Escape (via application event filter)
#   - Closes on click outside (via application event filter)

import logging
from typing import Optional, Tuple

from PyQt6.QtCore import (
    Qt,
    QPoint,
    QSize,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPaintEvent,
    QMouseEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QSizePolicy,
    QWidget,
    QVBoxLayout,
)

from config.settings import settings
from ui.theme import CursorBiteColors, Sizing, get_font
from utils.logger import get_logger

logger = get_logger("ui.overlay_window")


# ── Overlay Window ─────────────────────────────────────────────────

class OverlayWindow(QWidget):
    """Base overlay window for Cursor Bite.

    A frameless, transparent, always-on-top window.
    Escape and click-outside are handled by the application-level
    event filters installed in Application.setup_event_filters().
    """

    # ── Signals ─────────────────────────────────────────────────

    closed = pyqtSignal()
    """Emitted when the overlay is closed."""

    # ── State ───────────────────────────────────────────────────

    _is_visible = False
    _is_closing = False
    _position = QPoint(0, 0)
    _click_outside_to_close = True

    def __init__(
        self,
        parent: QWidget = None,
        flags: Qt.WindowType = Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
        | Qt.WindowType.SplashScreen,
    ) -> None:
        super().__init__(parent, flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setWindowFlags(flags)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._show_animation: Optional[QPropertyAnimation] = None
        self._hide_animation: Optional[QPropertyAnimation] = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._apply_theme()

    # ── Theme ───────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        """Apply the Cursor Bite theme."""
        pass  # Subclasses override

    # ── Positioning ─────────────────────────────────────────────

    def position_at_cursor(
        self,
        cursor_pos: Optional[QPoint] = None,
        offset: Tuple[int, int] = (0, 0),
    ) -> None:
        """Position the overlay at the cursor position.

        Args:
            cursor_pos: Cursor position. Defaults to current cursor pos.
            offset: (x, y) offset from cursor.
        """
        if cursor_pos is None:
            from PyQt6.QtGui import QCursor
            cursor_pos = QCursor.pos()

        self._position = cursor_pos + QPoint(*offset)
        self.move(self._position)
        self._clamp_to_screen()

    def _clamp_to_screen(self) -> None:
        """Clamp the window position to stay within the visible screen."""
        screens = QApplication.screens()
        if not screens:
            return

        window_size = self.frameGeometry().size()
        window_x = self.x()
        window_y = self.y()

        # Find the screen nearest to the window
        target_screen = None
        for s in screens:
            geom = s.availableGeometry()
            center_x = window_x + window_size.width() // 2
            center_y = window_y + window_size.height() // 2
            if geom.contains(center_x, center_y):
                target_screen = s
                break

        if target_screen is None:
            # Use the screen nearest to the window center
            best_dist = float("inf")
            for s in screens:
                cx = s.availableGeometry().center().x()
                cy = s.availableGeometry().center().y()
                dist = (cx - window_x) ** 2 + (cy - window_y) ** 2
                if dist < best_dist:
                    best_dist = dist
                    target_screen = s

        if target_screen is not None:
            geom = target_screen.availableGeometry()
            clamped_x = max(
                geom.left(),
                min(window_x, geom.right() - window_size.width()),
            )
            clamped_y = max(
                geom.top(),
                min(window_y, geom.bottom() - window_size.height()),
            )
            if clamped_x != window_x or clamped_y != window_y:
                self.move(clamped_x, clamped_y)
                self._position = QPoint(clamped_x, clamped_y)

    def smart_position(
        self,
        cursor_pos: QPoint,
        window_size: QSize,
        margin: int = 10,
    ) -> QPoint:
        """Calculate a smart position near the cursor.

        Repositions to avoid screen edges, corners, and the taskbar.

        Args:
            cursor_pos: Current cursor position.
            window_size: Size of the window.
            margin: Minimum margin from edges.

        Returns:
            Calculated QPoint position.
        """
        screens = QApplication.screens()
        if not screens:
            return cursor_pos

        # Find the screen containing the cursor
        cursor_screen = None
        for screen in screens:
            if screen.availableGeometry().contains(cursor_pos):
                cursor_screen = screen
                break

        if cursor_screen is None and screens:
            cursor_screen = screens[0]

        if cursor_screen is None:
            return cursor_pos

        screen_geom = cursor_screen.availableGeometry()
        screen_left = screen_geom.left()
        screen_top = screen_geom.top()
        screen_right = screen_geom.right()
        screen_bottom = screen_geom.bottom()

        # Default: position above and to the right of cursor
        x = cursor_pos.x() + 15
        y = cursor_pos.y() - window_size.height() - 15

        # Adjust for left edge
        if x < screen_left + margin:
            x = cursor_pos.x() - window_size.width() - 15

        # Adjust for right edge
        if x + window_size.width() > screen_right - margin:
            x = screen_right - window_size.width() - margin

        # Center horizontally if still off-screen
        if x < screen_left + margin or x + window_size.width() > screen_right - margin:
            x = cursor_pos.x() - window_size.width() // 2
            x = max(screen_left + margin, min(x, screen_right - window_size.width() - margin))

        # Adjust for top edge
        if y < screen_top + margin:
            y = cursor_pos.y() + 15

        # Adjust for bottom edge
        if y + window_size.height() > screen_bottom - margin:
            y = screen_bottom - window_size.height() - margin

        # Center vertically if still off-screen
        if y < screen_top + margin or y + window_size.height() > screen_bottom - margin:
            y = cursor_pos.y() - window_size.height() // 2
            y = max(screen_top + margin, min(y, screen_bottom - window_size.height() - margin))

        return QPoint(x, y)

    # ── Visibility ──────────────────────────────────────────────

    def show_at_cursor(
        self,
        cursor_pos: Optional[QPoint] = None,
        animation: bool = True,
        reposition: bool = True,
    ) -> None:
        """Show the overlay.

        Args:
            cursor_pos: If provided and reposition=True, position at cursor first.
            animation: Whether to animate the appearance.
            reposition: If False, use the window's current position.
        """
        if reposition and cursor_pos is not None:
            self.position_at_cursor(cursor_pos)

        if animation and settings.general_animations:
            self._animated_show()
        else:
            self.setWindowOpacity(settings.ui_opacity)
            super().show()
            self._is_visible = True
            logger.debug("Overlay shown (no animation).")

    def _animated_show(self) -> None:
        """Show with fade-in animation."""
        self.setWindowOpacity(0.0)
        super().show()
        self._is_visible = True

        self._show_animation = QPropertyAnimation(self, b"windowOpacity")
        self._show_animation.setDuration(settings.ui_animation_speed)
        self._show_animation.setStartValue(0.0)
        self._show_animation.setEndValue(settings.ui_opacity)
        self._show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._show_animation.start()
        logger.debug("Overlay showing with animation.")

    def hide_with_animation(self) -> None:
        """Hide with fade-out animation."""
        if not self._is_visible or self._is_closing:
            return

        self._is_closing = True

        if settings.general_animations:
            self._hide_animation = QPropertyAnimation(self, b"windowOpacity")
            self._hide_animation.setDuration(max(50, settings.ui_animation_speed // 2))
            self._hide_animation.setStartValue(self.windowOpacity())
            self._hide_animation.setEndValue(0.0)
            self._hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
            self._hide_animation.finished.connect(self._on_hide_finished)
            self._hide_animation.start()
            logger.debug("Overlay hiding with animation.")
        else:
            self._on_hide_finished()

    def _on_hide_finished(self) -> None:
        """Called when hide animation completes."""
        super().hide()
        self._is_visible = False
        self._is_closing = False
        self.closed.emit()
        logger.debug("Overlay hidden.")

    def show(self) -> None:
        """Override show to track visibility."""
        self._is_visible = True
        super().show()

    def hide(self) -> None:
        """Override hide to track visibility."""
        self._is_visible = False
        super().hide()

    # ── Events ──────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the overlay background (transparent)."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        super().paintEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press — close if click-outside is enabled."""
        if self._click_outside_to_close:
            self.hide_with_animation()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        """Handle key presses — Escape closes the overlay.

        NOTE: This only fires if the window has keyboard focus.
        For reliable Escape handling regardless of focus, the
        Application.install_event_filters() method installs an
        app-level filter that catches Escape globally when the
        menu is open.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.hide_with_animation()
            event.accept()
        else:
            super().keyPressEvent(event)

    # ── Properties ──────────────────────────────────────────────

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @property
    def is_open(self) -> bool:
        """Whether the overlay is currently open and visible."""
        return self._is_visible and not self._is_closing
