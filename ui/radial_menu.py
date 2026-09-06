# Cursor Bite — Minimal Compact Radial HUD Menu
# ============================================================
# A native, quiet, cursor-centric overlay for Windows.
#
# Design principles:
#   - Compact 180–220px diameter (system overlay, not a bloated app panel)
#   - Glowing core center interaction button (NO cursor graphic)
#   - Icon-first sectors with micro numbers [1]..[8]
#   - Clean hover states with contextual tooltip
#   - Zero visual clutter, restrained purple/blue palette
#   - Full keyboard navigation (1-8 keys, Arrows, Enter, Esc)

from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QRectF,
    QTimer,
    pyqtSignal,
    QPropertyAnimation,
    QEasingCurve,
)
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QMouseEvent,
    QFont,
    QFontMetrics,
    QCursor,
    QKeyEvent,
    QPen,
    QBrush,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget, QApplication

from config.settings import settings
from domain.models import ActionKind
from ui.theme import CursorBiteColors, ACTION_THEME, get_font, get_heading_font, get_mono_font
from utils.logger import get_logger

logger = get_logger("ui.radial_menu")


# ── Action Definitions (Clockwise from 12 o'clock) ─────────────────

MENU_ACTIONS = [
    # (ActionKind, Label, Icon, KeyNumber, ShortDesc)
    (ActionKind.TRANSLATE,    "Translate",    "🌐", "1", "Offline Neural Translation"),
    (ActionKind.SUMMARIZE,    "Summarize",    "📑", "2", "Concise Summary with AI"),
    (ActionKind.EXPLAIN,      "Explain",      "💡", "3", "2-4 Sentence Concept Breakdown"),
    (ActionKind.SEARCH_WEB,   "Search Web",   "🔍", "4", "DuckDuckGo Web Search"),
    (ActionKind.SETTINGS,     "Settings",     "⚙️", "5", "Preferences & Models"),
    (ActionKind.CAPTURE_TEXT, "Capture OCR",  "📷", "6", "Screen Region Sniper"),
    (ActionKind.REWRITE,      "Rewrite",      "✍️", "7", "Precision Polish (Meaning Preserved)"),
    (ActionKind.ASK_AI,       "Ask AI",       "🤖", "8", "Contextual or Freeform AI"),
]

INDEX_TO_ACTION = [item[0] for item in MENU_ACTIONS]


# ── Sizing Constants (Target: 180–220px) ───────────────────────────

_TOTAL_SIZE = 220       # Overall window dimensions (diameter)
_OUTER_R    = 98        # Outer boundary of sector ring
_INNER_R    = 42        # Inner boundary of sector ring (hub edge)
_HUB_R      = 36        # Radius of center core interaction button
_ICON_R     = 70        # Radius where sector icons sit
_KEY_R      = 87        # Radius where [1]..[8] shortcut badges sit


# ── RadialMenu Class ───────────────────────────────────────────────

class RadialMenu(QWidget):
    """Compact, minimal dark glassmorphic radial HUD menu."""

    # ── Signals ─────────────────────────────────────────────────

    action_selected = pyqtSignal(ActionKind)
    action_hovered  = pyqtSignal(ActionKind)
    menu_closed     = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        flags = (
            Qt.WindowType.Popup
            | Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(parent, flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setFixedSize(_TOTAL_SIZE, _TOTAL_SIZE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self._hovered_index: int = -1
        self._is_open: bool = False
        self._closing: bool = False
        self._has_selection: bool = False
        self._recommended_actions: set[ActionKind] = set()
        self._animation: Optional[QPropertyAnimation] = None

        # Hover timer for smooth tracker refresh
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(25)
        self._hover_timer.timeout.connect(self._refresh_hover)

    # ── Public API ──────────────────────────────────────────────

    def show_at(self, anchor: Optional[QPoint] = None, has_selection: bool = False) -> None:
        """Open the compact radial menu centered at the cursor anchor.

        Args:
            anchor: Target center point. If None, current mouse position is used.
            has_selection: Whether text was actively selected beforehand.
        """
        if anchor is None:
            anchor = QCursor.pos()

        self._has_selection = has_selection
        self._hovered_index = -1
        self._closing = False
        self._is_open = True

        # Clamp position within screen boundaries
        clamped = self._clamp_to_screen(anchor)
        self.move(clamped)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        # Fade/Scale bloom animation
        self.setWindowOpacity(0.0)
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(120)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(0.97)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

        # Update initial hover based on current mouse position
        QTimer.singleShot(20, self._refresh_hover)

    def open_at(self, anchor: Optional[QPoint] = None, has_selection: bool = False) -> None:
        """Alias for show_at to support Controller API."""
        self.show_at(anchor=anchor, has_selection=has_selection)


    def set_recommended_actions(self, actions: list[ActionKind]) -> None:
        """Set adaptive recommended actions based on context intelligence."""
        self._recommended_actions = set(actions)
        self.update()

    def close_menu(self) -> None:
        """Dismiss the radial menu with smooth fadeout."""
        if self._closing:
            return
        self._closing = True
        self._is_open = False
        self._hover_timer.stop()

        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setDuration(90)
        self._animation.setStartValue(self.windowOpacity())
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.Type.InQuad)
        self._animation.finished.connect(self._finalize_close)
        self._animation.start()

    def _finalize_close(self) -> None:
        self.hide()
        self._closing = False
        self.menu_closed.emit()

    @property
    def is_open(self) -> bool:
        """Whether the radial menu is currently open and visible."""
        return self._is_open


    # ── Geometry & Hit-Testing ──────────────────────────────────

    def _clamp_to_screen(self, center: QPoint) -> QPoint:
        """Ensure menu stays fully inside the screen bounds."""
        screen = QApplication.screenAt(center) or QApplication.primaryScreen()
        if not screen:
            return center - QPoint(_TOTAL_SIZE // 2, _TOTAL_SIZE // 2)

        geo = screen.availableGeometry()
        margin = 12
        half = _TOTAL_SIZE // 2

        x = max(geo.left() + margin, min(center.x() - half, geo.right() - _TOTAL_SIZE - margin))
        y = max(geo.top() + margin, min(center.y() - half, geo.bottom() - _TOTAL_SIZE - margin))
        return QPoint(x, y)

    def _center_point(self) -> QPointF:
        return QPointF(_TOTAL_SIZE / 2.0, _TOTAL_SIZE / 2.0)

    def _hit_sector(self, pos: QPoint) -> int:
        """Calculate which sector index the point falls into."""
        cp = self._center_point()
        dx = pos.x() - cp.x()
        dy = pos.y() - cp.y()
        dist = math.hypot(dx, dy)

        # Inside center hub or outside outer ring -> no sector
        if dist < _INNER_R or dist > _OUTER_R + 6:
            return -1

        # Angle: 0° is 12 o'clock, clockwise
        angle = math.degrees(math.atan2(dx, -dy))
        if angle < 0:
            angle += 360.0

        sector_deg = 360.0 / len(MENU_ACTIONS)
        idx = int(angle // sector_deg) % len(MENU_ACTIONS)
        return idx

    def _point_on_radius(self, index: int, radius: float) -> QPointF:
        """Get center point of sector at given radius."""
        cp = self._center_point()
        sector_deg = 360.0 / len(MENU_ACTIONS)
        mid_angle = (index * sector_deg) + (sector_deg / 2.0)
        rad = math.radians(mid_angle)
        x = cp.x() + radius * math.sin(rad)
        y = cp.y() - radius * math.cos(rad)
        return QPointF(x, y)

    def _sector_path(self, index: int, outer_r: float, inner_r: float) -> QPainterPath:
        """Construct annular wedge path for sector."""
        cp = self._center_point()
        sector_deg = 360.0 / len(MENU_ACTIONS)
        start_angle = (index * sector_deg) - 90.0  # Qt 0° is 3 o'clock

        path = QPainterPath()
        outer_rect = QRectF(cp.x() - outer_r, cp.y() - outer_r, outer_r * 2.0, outer_r * 2.0)
        inner_rect = QRectF(cp.x() - inner_r, cp.y() - inner_r, inner_r * 2.0, inner_r * 2.0)

        # Arc from outer to inner
        path.arcMoveTo(outer_rect, -start_angle)
        path.arcTo(outer_rect, -start_angle, -sector_deg)
        path.arcTo(inner_rect, -(start_angle + sector_deg), sector_deg)
        path.closeSubpath()
        return path

    def _refresh_hover(self) -> None:
        """Synchronize hovered sector with current cursor position."""
        if not self.isVisible() or self._closing:
            return
        local_pos = self.mapFromGlobal(QCursor.pos())
        idx = self._hit_sector(local_pos)
        if idx != self._hovered_index:
            self._hovered_index = idx
            self.update()
            if 0 <= idx < len(INDEX_TO_ACTION):
                self.action_hovered.emit(INDEX_TO_ACTION[idx])

    # ── Paint Event ─────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        cp = self._center_point()
        cx, cy = cp.x(), cp.y()
        n_sectors = len(MENU_ACTIONS)
        sector_span = 360.0 / n_sectors

        # ── 1. Subtle Backdrop Ambient Ring ─────────────────────
        ambient_rect = QRectF(cx - _OUTER_R - 2, cy - _OUTER_R - 2, (_OUTER_R + 2) * 2, (_OUTER_R + 2) * 2)
        ambient_grad = QRadialGradient(cx, cy, _OUTER_R + 4)
        ambient_grad.setColorAt(0.0, QColor(15, 18, 28, 250))
        ambient_grad.setColorAt(0.85, QColor(11, 13, 20, 245))
        ambient_grad.setColorAt(1.0, QColor(7, 8, 14, 235))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(ambient_grad))
        p.drawEllipse(ambient_rect)

        # ── 2. Draw 8 Sectors ───────────────────────────────────
        for i in range(n_sectors):
            kind, label, icon, key_num, desc = MENU_ACTIONS[i]
            is_hovered = (i == self._hovered_index)
            is_recommended = (kind in self._recommended_actions)

            outer_r = _OUTER_R + (2 if is_hovered else 0)
            inner_r = _INNER_R
            path = self._sector_path(i, outer_r, inner_r)

            # Sector Fill: Restrained cohesive violet on hover, subtle dark on idle
            if is_hovered:
                p.setBrush(QBrush(QColor(99, 102, 241, 80)))  # Soft purple hover
                p.setPen(QPen(CursorBiteColors.ACCENT_SECONDARY, 1.5))
            else:
                p.setBrush(QBrush(QColor(22, 26, 38, 120)))
                p.setPen(QPen(QColor(255, 255, 255, 14), 1.0))

            p.drawPath(path)

            # Draw Sector Content (Icon + Micro Key Number)
            self._draw_sector_content(p, i, kind, label, icon, key_num, is_hovered, is_recommended)

        # ── 3. Subtle Outer Ring ────────────────────────────────
        outer_pen = QPen(QColor(255, 255, 255, 24), 1.0)
        p.setPen(outer_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - _OUTER_R, cy - _OUTER_R, _OUTER_R * 2, _OUTER_R * 2))

        # ── 4. Center Interaction Button (NO cursor graphic) ────
        self._draw_center_button(p, cx, cy)

        p.end()

    def _draw_sector_content(
        self,
        p: QPainter,
        index: int,
        kind: ActionKind,
        label: str,
        icon: str,
        key_num: str,
        is_hovered: bool,
        is_recommended: bool,
    ) -> None:
        """Render the compact icon and micro key badge in the wedge."""
        icon_pos = self._point_on_radius(index, _ICON_R)
        key_pos  = self._point_on_radius(index, _KEY_R)

        # 1. Action Icon (Emoji / Symbol)
        icon_font = QFont("Segoe UI Emoji", 13 if is_hovered else 12)
        icon_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        p.setFont(icon_font)
        p.setPen(QPen(QColor("#FFFFFF") if is_hovered else QColor("#CBD5E1")))
        icon_rect = QRectF(icon_pos.x() - 12, icon_pos.y() - 12, 24, 24)
        p.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, icon)

        # 2. Micro Key Badge (e.g. "1")
        key_font = get_mono_font(size=7)
        p.setFont(key_font)
        if is_hovered:
            p.setPen(QPen(CursorBiteColors.TEXT_ACCENT))
        else:
            p.setPen(QPen(QColor(148, 163, 184, 150)))

        key_rect = QRectF(key_pos.x() - 8, key_pos.y() - 7, 16, 14)
        p.drawText(key_rect, Qt.AlignmentFlag.AlignCenter, key_num)

        # 3. Recommended Action Subtle Indicator Dot
        if is_recommended and not is_hovered:
            rec_pos = self._point_on_radius(index, _OUTER_R - 5)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(CursorBiteColors.ACCENT_SUBTLE))
            p.drawEllipse(rec_pos, 2.0, 2.0)

    def _draw_center_button(self, p: QPainter, cx: float, cy: float) -> None:
        """Render the circular center interaction button with subtle glowing ring."""
        hub_rect = QRectF(cx - _HUB_R, cy - _HUB_R, _HUB_R * 2.0, _HUB_R * 2.0)

        # 1. Subtle Glow Ring
        glow_r = _HUB_R + 3.0
        glow_rect = QRectF(cx - glow_r, cy - glow_r, glow_r * 2.0, glow_r * 2.0)
        p.setPen(QPen(QColor(99, 102, 241, 50 if self._hovered_index >= 0 else 25), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(glow_rect)

        # 2. Center Button Core Fill
        hub_grad = QRadialGradient(cx, cy, _HUB_R)
        if self._hovered_index >= 0:
            hub_grad.setColorAt(0.0, QColor(24, 28, 46, 255))
            hub_grad.setColorAt(1.0, QColor(12, 14, 24, 255))
        else:
            hub_grad.setColorAt(0.0, QColor(18, 21, 34, 255))
            hub_grad.setColorAt(1.0, QColor(10, 11, 18, 255))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(hub_grad))
        p.drawEllipse(hub_rect)

        # 3. Center Ring Border
        if self._hovered_index >= 0:
            border_pen = QPen(CursorBiteColors.ACCENT_SECONDARY, 1.8)
        else:
            border_pen = QPen(QColor(255, 255, 255, 32), 1.0)
        p.setPen(border_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(hub_rect)

        # 4. Center Content (Clean Minimal Typography or Monogram)
        if 0 <= self._hovered_index < len(MENU_ACTIONS):
            kind, title, icon, key_num, desc = MENU_ACTIONS[self._hovered_index]

            # Show hovered action in center
            p.setFont(get_heading_font(size=8, bold=True))
            p.setPen(QPen(CursorBiteColors.TEXT_PRIMARY))
            title_rect = QRectF(cx - 30, cy - 12, 60, 14)
            p.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, title)

            # Micro key hint
            p.setFont(get_mono_font(size=7))
            p.setPen(QPen(CursorBiteColors.TEXT_ACCENT))
            key_hint_rect = QRectF(cx - 24, cy + 2, 48, 12)
            p.drawText(key_hint_rect, Qt.AlignmentFlag.AlignCenter, f"[{key_num}]")

        else:
            # Idle / Default State: Sleek Core Monogram
            p.setFont(QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold))
            p.setPen(QPen(CursorBiteColors.ACCENT_SECONDARY))
            emblem_rect = QRectF(cx - 24, cy - 14, 48, 18)
            p.drawText(emblem_rect, Qt.AlignmentFlag.AlignCenter, "CB")

            # Status dot
            p.setFont(get_font(size=6))
            p.setPen(QPen(CursorBiteColors.SUCCESS if self._has_selection else QColor("#64748B")))
            dot_rect = QRectF(cx - 20, cy + 4, 40, 10)
            p.drawText(dot_rect, Qt.AlignmentFlag.AlignCenter, "●" if self._has_selection else "ready")

    # ── Mouse Events ─────────────────────────────────────────────

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        idx = self._hit_sector(event.pos())
        if idx != self._hovered_index:
            self._hovered_index = idx
            self.update()
            if 0 <= idx < len(INDEX_TO_ACTION):
                self.action_hovered.emit(INDEX_TO_ACTION[idx])
        self._hover_timer.start()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.pos()
        cp = self._center_point()
        dist = math.hypot(pos.x() - cp.x(), pos.y() - cp.y())

        # If clicked in center core while hovering or selecting
        if dist <= _HUB_R and 0 <= self._hovered_index < len(INDEX_TO_ACTION):
            chosen = INDEX_TO_ACTION[self._hovered_index]
            logger.info(f"Radial menu center core clicked: {chosen.value}")
            self.action_selected.emit(chosen)
            self.close_menu()
            event.accept()
            return

        idx = self._hit_sector(pos)
        if 0 <= idx < len(INDEX_TO_ACTION):
            chosen = INDEX_TO_ACTION[idx]
            logger.info(f"Radial menu sector clicked: {chosen.value} (index {idx})")
            self.action_selected.emit(chosen)
            self.close_menu()
            event.accept()
            return

        # Click outside dismisses menu
        self.close_menu()
        super().mousePressEvent(event)

    # ── Keyboard Events & Shortcuts ──────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()

        # 1. Escape closes immediately
        if key in (Qt.Key.Key_Escape, Qt.Key.Key_Back):
            logger.info("Radial menu closed via Escape.")
            self.close_menu()
            event.accept()
            return

        # 2. Direct Number Shortcuts ('1' through '8')
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_8:
            idx = key - Qt.Key.Key_1
            if 0 <= idx < len(INDEX_TO_ACTION):
                chosen = INDEX_TO_ACTION[idx]
                logger.info(f"Action triggered via number key [{idx + 1}]: {chosen.value}")
                self.action_selected.emit(chosen)
                self.close_menu()
                event.accept()
                return

        # 3. Enter / Space confirms current hover
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if 0 <= self._hovered_index < len(INDEX_TO_ACTION):
                chosen = INDEX_TO_ACTION[self._hovered_index]
                logger.info(f"Action triggered via Enter/Space: {chosen.value}")
                self.action_selected.emit(chosen)
                self.close_menu()
                event.accept()
                return

        # 4. Arrow Key Navigation
        n = len(MENU_ACTIONS)
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            self._hovered_index = 0 if self._hovered_index < 0 else (self._hovered_index + 1) % n
            self.update()
            self.action_hovered.emit(INDEX_TO_ACTION[self._hovered_index])
            event.accept()
            return
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            self._hovered_index = (n - 1) if self._hovered_index < 0 else (self._hovered_index - 1) % n
            self.update()
            self.action_hovered.emit(INDEX_TO_ACTION[self._hovered_index])
            event.accept()
            return

        super().keyPressEvent(event)
