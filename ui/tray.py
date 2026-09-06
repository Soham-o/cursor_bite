# Cursor Bite — System Tray
# ============================================================
# System tray icon and menu for Cursor Bite.
#
# The app runs primarily as a tray application — no main window.
# The tray icon provides access to:
#   - Open (same as pressing the hotkey)
#   - Enable/disable toggle
#   - Settings
#   - Privacy dashboard
#   - Offline mode toggle
#   - About
#   - Check Components
#   - Exit
#
# This class only reports intent through signals — it opens no windows
# itself. app/application.py owns the dialogs, which keeps the tray
# free of any dependency on the pipeline or the optional components.

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import (
    QCursor,
    QIcon,
    QPainter,
    QPixmap,
    QColor,
    QFont,
)
from PyQt6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QWidget,
)

from utils.logger import get_logger

logger = get_logger("ui.tray")


# ── Tray Icon Painter ──────────────────────────────────────────────

class TrayIconPainter:
    """Paints a custom tray icon for Cursor Bite.

    Design (minimal, professional):
    - Dark circle background (#16161F)
    - Blue ring accent (#0066CC)
    - Inner dark circle (#0D0D14)
    - "CB" text in light blue (#00AAFF)
    - Small blue dot accent (bottom-right)
    """

    @staticmethod
    def create_icon(size: int = 64, dot_color: Optional[QColor] = None) -> QIcon:
        """Create a QIcon for the system tray.

        Args:
            size: Icon size in pixels (will be scaled by Qt as needed).
            dot_color: Color of the live status accent dot. Default is soft sky blue.

        Returns:
            QIcon for the tray icon.
        """
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        radius = size // 2 - 4
        center = QPoint(size // 2, size // 2)

        painter.setPen(Qt.PenStyle.NoPen)

        # Dark circle background
        painter.setBrush(QColor("#0F111D"))
        painter.drawEllipse(center, radius, radius)

        # Indigo accent ring (outermost)
        painter.setBrush(QColor("#6366F1"))
        painter.drawEllipse(center, radius - 2, radius - 2)

        # Inner dark circle
        inner_radius = radius - 8
        painter.setBrush(QColor("#08090E"))
        painter.drawEllipse(center, inner_radius, inner_radius)

        # "CB" text
        painter.setPen(QColor("#818CF8"))
        font = QFont("Segoe UI Variable Text", size // 4, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            QRect(0, 0, size, size),
            Qt.AlignmentFlag.AlignCenter,
            "CB",
        )

        # Live status accent glow dot
        dot_size = max(3, size // 9)
        dot_x = size - radius + 4
        dot_y = size - radius + 4
        painter.setBrush(dot_color if dot_color else QColor("#38BDF8"))
        painter.drawEllipse(QPoint(dot_x, dot_y), dot_size, dot_size)

        painter.end()

        return QIcon(pixmap)



# ── System Tray Manager ────────────────────────────────────────────

class SystemTray(QSystemTrayIcon):
    """System tray icon and menu for Cursor Bite.

    Provides the primary user interaction point when the app
    is running in the background.
    """

    # ── Signals ─────────────────────────────────────────────────

    toggled = pyqtSignal(bool)
    """Emitted when the enabled state changes."""

    open_requested = pyqtSignal()
    """Emitted when the user clicks Open — same intent as the hotkey."""

    settings_requested = pyqtSignal()
    """Emitted when the user clicks Settings."""

    privacy_requested = pyqtSignal()
    """Emitted when the user clicks Privacy."""

    offline_toggled = pyqtSignal(bool)
    """Emitted when offline mode is toggled."""

    about_requested = pyqtSignal()
    """Emitted when the user clicks About."""

    check_components = pyqtSignal()
    """Emitted when the user clicks Check Components."""

    exit_requested = pyqtSignal()
    """Emitted when the user clicks Exit."""

    # ── State ───────────────────────────────────────────────────

    _enabled: bool = True
    _offline_mode: bool = False

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the system tray icon and menu.

        Args:
            parent: Optional parent widget. Normally None — the tray
                outlives every window in the app.
        """
        super().__init__(parent)

        # Set icon and tooltip
        self.setIcon(TrayIconPainter.create_icon(64))
        self.setToolTip("Cursor Bite — Intelligence at your cursor")

        # Create the context menu and hand it to Qt. Without
        # setContextMenu() the native right-click on a tray icon does
        # nothing at all — the menu has to be registered, not just built.
        self._menu = self._create_menu()
        self.setContextMenu(self._menu)

        # Connect activation handler
        self.activated.connect(self._on_activated)

        logger.info("System tray initialized.")

    # ── Menu Creation ───────────────────────────────────────────

    def _create_menu(self) -> QMenu:
        """Create the tray context menu.

        Returns:
            QMenu with all tray options.
        """
        menu = QMenu()

        # ── Title (disabled, just for display) ─────────────────
        title_action = menu.addAction("Cursor Bite")
        title_action.setEnabled(False)
        title_action.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))

        menu.addSeparator()

        # ── Enable/disable toggle ──────────────────────────────
        self._enable_action = menu.addAction("\u2713 Enabled")
        self._enable_action.triggered.connect(self._on_toggle_enabled)
        self._update_enable_action_text()

        menu.addSeparator()

        # ── Main actions ───────────────────────────────────────
        open_action = menu.addAction("Open")
        open_action.triggered.connect(self.open_requested.emit)

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.settings_requested.emit)

        privacy_action = menu.addAction("Privacy")
        privacy_action.triggered.connect(self.privacy_requested.emit)

        # Offline mode toggle
        self._offline_action = menu.addAction("\u25CB Offline Mode")
        self._offline_action.triggered.connect(self._on_toggle_offline)
        self._update_offline_action_text()

        menu.addSeparator()

        # Check Components
        check_action = menu.addAction("Check Components")
        check_action.triggered.connect(self.check_components.emit)

        menu.addSeparator()

        # About
        about_action = menu.addAction("About")
        about_action.triggered.connect(self.about_requested.emit)

        menu.addSeparator()

        # Exit
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_requested.emit)

        return menu

    # ── Menu Text Updates ───────────────────────────────────────

    def _update_enable_action_text(self) -> None:
        """Update the enable/disable menu text to reflect current state."""
        if self._enabled:
            self._enable_action.setText("\u2713 Enabled")
        else:
            self._enable_action.setText("\u2717 Disabled")

    def _update_offline_action_text(self) -> None:
        """Update the offline mode menu text to reflect current state."""
        if self._offline_mode:
            self._offline_action.setText("\u2713 Offline Mode")
        else:
            self._offline_action.setText("\u25CB Offline Mode")

    # ── Activation Handler ──────────────────────────────────────

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (click).

        Right-click is handled natively by the registered context menu;
        this adds the same menu to a left click, which is what most
        people try first.
        """
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._menu.popup(QCursor.pos())

    # ── Menu Action Handlers ────────────────────────────────────

    def _on_toggle_enabled(self) -> None:
        """Toggle the enabled state."""
        self._enabled = not self._enabled
        self._update_enable_action_text()
        self.toggled.emit(self._enabled)
        logger.info(f"Cursor Bite {'enabled' if self._enabled else 'disabled'} from tray.")

    def _on_toggle_offline(self) -> None:
        """Toggle offline mode."""
        self._offline_mode = not self._offline_mode
        self._update_offline_action_text()
        self.offline_toggled.emit(self._offline_mode)
        logger.info(f"Offline mode {'enabled' if self._offline_mode else 'disabled'}.")

    # ── Public API ──────────────────────────────────────────────

    def set_enabled(self, enabled: bool) -> None:
        """Set the enabled state and update menu text."""
        self._enabled = enabled
        self._update_enable_action_text()

    def set_offline_mode(self, offline: bool) -> None:
        """Set offline mode state and update menu text."""
        self._offline_mode = offline
        self._update_offline_action_text()

    def show_notification(
        self,
        title: str,
        message: str,
        timeout_ms: int = 3000,
    ) -> None:
        """Show a tray notification balloon.

        Args:
            title: Notification title.
            message: Notification message body.
            timeout_ms: How long to display the notification in milliseconds.
        """
        if QApplication.instance() is None:
            logger.warning("Cannot show notification — no QApplication instance.")
            return

        self.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            timeout_ms,
        )
        logger.debug(f"Tray notification shown: {title}")

    def update_status_badge(
        self,
        dot_color: Optional[QColor] = None,
        tooltip: Optional[str] = None,
    ) -> None:
        """Update the tray icon status accent dot and tooltip."""
        self.setIcon(TrayIconPainter.create_icon(64, dot_color=dot_color))
        if tooltip:
            self.setToolTip(tooltip)

