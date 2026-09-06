# Cursor Bite — Activation Toast
# ============================================================
# Minimal, non-intrusive floating pill that briefly appears when
# Cursor Bite is activated via the global hotkey (e.g. Ctrl+Alt+B).
#
# Design:
#   - Obsidian acrylic pill (14px radius, subtle glowing violet border)
#   - Bottom-right corner of the active screen
#   - Does NOT steal focus or interrupt workflow
#   - Auto-fades out after ~1.2s

from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QLinearGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from ui.theme import CursorBiteColors, get_font, get_mono_font
from utils.logger import get_logger

logger = get_logger("ui.activation_toast")

_WIDTH = 210
_HEIGHT = 36
_RADIUS = 14


class ActivationToast(QWidget):
    """Brief, elegant HUD notification confirming Cursor Bite activation."""

    _instance: Optional["ActivationToast"] = None

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(_WIDTH, _HEIGHT)

        self._hotkey_text = "Ctrl+Alt+B"
        self._fade_anim: Optional[QPropertyAnimation] = None

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._start_fade_out)

    @classmethod
    def show_toast(cls, hotkey_text: str = "Ctrl+Alt+B") -> None:
        """Show or refresh the activation toast."""
        try:
            if cls._instance is None:
                cls._instance = ActivationToast()
            cls._instance.display(hotkey_text)
        except Exception as e:
            logger.debug(f"Could not show activation toast: {e}")

    def display(self, hotkey_text: str) -> None:
        """Position toast at bottom-right of current screen and animate."""
        self._hotkey_text = hotkey_text
        self._dismiss_timer.stop()
        if self._fade_anim is not None:
            self._fade_anim.stop()

        # Position at bottom-right of current active monitor
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            margin_right = 24
            margin_bottom = 24
            x = geo.right() - _WIDTH - margin_right
            y = geo.bottom() - _HEIGHT - margin_bottom
            self.move(x, y)

        self.setWindowOpacity(0.0)
        self.show()

        # Fade in
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(120)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(0.96)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_in.start()
        self._fade_anim = fade_in

        # Schedule fade out after 1.1s
        self._dismiss_timer.start(1100)

    def _start_fade_out(self) -> None:
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(220)
        fade_out.setStartValue(self.windowOpacity())
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InQuad)
        fade_out.finished.connect(self.hide)
        fade_out.start()
        self._fade_anim = fade_out

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(
            float(rect.x()), float(rect.y()),
            float(rect.width()), float(rect.height()),
            _RADIUS, _RADIUS,
        )

        # Deep obsidian fill with slight translucency
        p.fillPath(path, QColor(11, 13, 20, 240))

        # Soft glowing violet-indigo border
        border_pen = QPen(QColor(99, 102, 241, 100), 1.2)
        p.setPen(border_pen)
        p.drawPath(path)

        # ── Draw Content ────────────────────────────────────────
        # 1. Accent Dot / Lightning Icon
        dot_rect = QRectF(12, 11, 14, 14)
        p.setFont(QFont("Segoe UI Emoji", 10))
        p.setPen(QPen(CursorBiteColors.ACCENT_PRIMARY))
        p.drawText(dot_rect, Qt.AlignmentFlag.AlignCenter, "⚡")

        # 2. Product Name
        p.setFont(get_font(10, bold=True))
        p.setPen(QPen(QColor("#F8FAFC")))
        title_rect = QRectF(30, 8, 80, 20)
        p.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "Cursor Bite")

        # 3. Separator bullet
        p.setPen(QPen(QColor(148, 163, 184, 120)))
        sep_rect = QRectF(108, 8, 12, 20)
        p.drawText(sep_rect, Qt.AlignmentFlag.AlignCenter, "·")

        # 4. Hotkey pill badge
        p.setFont(get_mono_font(9))
        p.setPen(QPen(CursorBiteColors.TEXT_ACCENT))
        key_rect = QRectF(122, 8, 76, 20)
        p.drawText(key_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._hotkey_text)

        p.end()
