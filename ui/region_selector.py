# Cursor Bite — Screen Region Selector
# ============================================================
# The translucent overlay used by Capture Text (OCR): the user drags
# a rectangle, and the region underneath is captured and OCR'd.
#
# Behaviour:
#   - Covers every monitor (the whole virtual desktop, taskbar included)
#   - Left-drag draws the region; release commits it
#   - Escape or right-click cancels
#   - A stray click (tiny rectangle) counts as a cancel, not a capture
#
# COORDINATES:
#   Qt reports positions in *logical* pixels; Windows' screen-capture
#   APIs work in *physical* pixels. At 150% display scaling those differ
#   by 1.5x, so a rectangle handed straight to the capture layer would
#   grab the wrong area. region_selected therefore emits PHYSICAL
#   coordinates, scaled by the device pixel ratio of the screen the
#   selection started on. (On a mixed-DPI multi-monitor setup a
#   selection spanning two different scale factors can still be off —
#   selecting within one monitor is exact.)
#
# IMPORTANT: Nothing is captured here and nothing is written to disk.
# This widget only reports a rectangle.

from typing import Optional

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from ui.theme import CursorBiteColors, get_font
from utils.logger import get_logger

logger = get_logger("ui.region_selector")


# ── Tuning ─────────────────────────────────────────────────────────

_DIM = QColor(0, 0, 0, 110)
"""Dim wash over the un-selected area. Light enough to still see content."""

_MIN_SIDE = 6
"""Selections smaller than this are treated as a stray click."""

_HIDE_SETTLE_MS = 80
"""Delay between hiding the overlay and reporting the region.

The overlay has to be off-screen before anything grabs the desktop or
it captures itself. One repaint cycle is enough in practice.
"""


# ── Region Selector ────────────────────────────────────────────────

class RegionSelector(QWidget):
    """Full-screen overlay for selecting a rectangular screen region."""

    # ── Signals ─────────────────────────────────────────────────

    region_selected = pyqtSignal(QRect)
    """Emitted with the chosen region in PHYSICAL screen pixels."""

    cancelled = pyqtSignal()
    """Emitted when the user aborts the selection."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setWindowTitle("Cursor Bite — Select Region")

        self._origin: Optional[QPoint] = None
        self._current: Optional[QPoint] = None
        self._dragging = False
        self._finished = False

        logger.debug("Region selector created.")

    # ── Public API ──────────────────────────────────────────────

    def start(self) -> None:
        """Show the overlay across every monitor and begin selection."""
        self._origin = None
        self._current = None
        self._dragging = False
        self._finished = False

        self.setGeometry(self._virtual_geometry())
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.grabKeyboard()

        logger.info("Region selection started.")

    def cancel(self) -> None:
        """Abort an in-progress selection from outside (hotkey, shutdown)."""
        self._cancel()

    # ── Geometry ────────────────────────────────────────────────

    @staticmethod
    def _virtual_geometry() -> QRect:
        """Union of every screen's full geometry (the virtual desktop)."""
        screens = QGuiApplication.screens()
        if not screens:
            return QRect(0, 0, 800, 600)

        union = screens[0].geometry()
        for screen in screens[1:]:
            union = union.united(screen.geometry())
        return union

    def _selection_rect(self) -> QRect:
        """Current selection in widget-local coordinates."""
        if self._origin is None or self._current is None:
            return QRect()
        return QRect(self._origin, self._current).normalized()

    def _to_global(self, rect: QRect) -> QRect:
        """Convert a widget-local rect to logical screen coordinates."""
        offset = self.geometry().topLeft()
        return QRect(rect.topLeft() + offset, rect.size())

    def _to_physical(self, logical: QRect) -> QRect:
        """Scale a logical screen rect to physical pixels.

        See the coordinates note in the module header for why this is
        necessary and where it is approximate.
        """
        screen = QGuiApplication.screenAt(logical.topLeft())
        if screen is None:
            screen = QGuiApplication.primaryScreen()

        ratio = screen.devicePixelRatio() if screen is not None else 1.0
        if abs(ratio - 1.0) < 0.01:
            return QRect(logical)

        return QRect(
            round(logical.left() * ratio),
            round(logical.top() * ratio),
            round(logical.width() * ratio),
            round(logical.height() * ratio),
        )

    # ── Mouse ───────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._cancel()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self._dragging = True
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self._dragging:
            return

        self._dragging = False
        self._current = event.pos()
        local = self._selection_rect()

        if local.width() < _MIN_SIDE or local.height() < _MIN_SIDE:
            logger.info("Region selection dismissed (click, not a drag).")
            self._cancel()
            return

        self._commit(self._to_physical(self._to_global(local)))

    # ── Keyboard ────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    # ── Finish ──────────────────────────────────────────────────

    def _commit(self, physical: QRect) -> None:
        """Hide, then report the region once the overlay is really gone."""
        if self._finished:
            return
        self._finished = True

        self._teardown()
        logger.info(
            f"Region selected: {physical.width()}x{physical.height()} "
            f"at ({physical.left()}, {physical.top()})"
        )
        QTimer.singleShot(_HIDE_SETTLE_MS, lambda: self.region_selected.emit(physical))

    def _cancel(self) -> None:
        """Abort the selection."""
        if self._finished:
            return
        self._finished = True

        self._teardown()
        logger.info("Region selection cancelled.")
        self.cancelled.emit()

    def _teardown(self) -> None:
        """Release the keyboard and get the overlay off the screen now."""
        self.releaseKeyboard()
        self.hide()
        QApplication.processEvents()

    # ── Painting ────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        full = self.rect()
        selection = self._selection_rect()

        if selection.isEmpty():
            painter.fillRect(full, _DIM)
            self._paint_hint(painter, full)
            return

        # Dim everything except the selection. Painting the four
        # surrounding bands (rather than clearing a hole) keeps the
        # selected area perfectly untouched.
        painter.fillRect(QRect(full.left(), full.top(), full.width(),
                               selection.top() - full.top()), _DIM)
        painter.fillRect(QRect(full.left(), selection.bottom() + 1, full.width(),
                               full.bottom() - selection.bottom()), _DIM)
        painter.fillRect(QRect(full.left(), selection.top(),
                               selection.left() - full.left(), selection.height()), _DIM)
        painter.fillRect(QRect(selection.right() + 1, selection.top(),
                               full.right() - selection.right(), selection.height()), _DIM)

        pen = QPen(QColor("#38BDF8"))
        pen.setWidthF(1.5)
        painter.setPen(pen)
        painter.drawRect(selection.adjusted(0, 0, -1, -1))

        self._paint_size_label(painter, selection)

    def _paint_hint(self, painter: QPainter, full: QRect) -> None:
        """Draw the instruction line before a drag starts."""
        painter.setFont(get_font(12, bold=True))
        painter.setPen(CursorBiteColors.TEXT_PRIMARY)

        text = "Drag a box to capture text with OCR   ·   Esc to cancel"
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(text) + 36
        height = metrics.height() + 16

        box = QRect(
            full.center().x() - width // 2,
            full.top() + 64,
            width,
            height,
        )

        painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        painter.setBrush(QColor(14, 17, 28, 240))
        painter.drawRoundedRect(box, 10, 10)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor("#F8FAFC"))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_size_label(self, painter: QPainter, selection: QRect) -> None:
        """Draw the live pixel dimensions beside the selection."""
        painter.setFont(get_font(10, bold=True))
        text = f"{selection.width()} × {selection.height()}"

        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(text) + 16
        height = metrics.height() + 8

        # Prefer above the selection; drop below when there's no room.
        top = selection.top() - height - 6
        if top < self.rect().top() + 4:
            top = selection.bottom() + 6

        box = QRect(selection.left(), top, width, height)

        painter.setPen(QPen(QColor(56, 189, 248, 80), 1.0))
        painter.setBrush(QColor(14, 17, 28, 240))
        painter.drawRoundedRect(box, 6, 6)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor("#38BDF8"))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
