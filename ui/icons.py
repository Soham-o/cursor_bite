# Cursor Bite — Icon System
# ============================================================
# Simple, consistent line icons drawn directly with QPainter — no emoji,
# no icon font, no image assets. One visual language (single stroke
# weight, round caps/joins, no fill except small accent dots) used
# everywhere an action needs a glyph: the radial menu, result headers,
# the components list.
#
# Emoji were the thing being replaced here: they render with whatever
# color and style the OS's emoji font ships that week, which is exactly
# the "inconsistent icon styles" a calm, minimal UI can't have. These are
# plain vector shapes, so they always look like they belong to the same
# product.

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen


def draw_icon(
    painter: QPainter,
    key: str,
    center: QPointF,
    size: float,
    color: QColor,
    stroke: float | None = None,
) -> None:
    """Draw icon `key` centered at `center`, fitting within a `size`-wide box.

    Args:
        painter: Active QPainter (caller manages save/restore if needed).
        key: One of "globe", "summary", "bulb", "search", "sliders",
            "frame", "pencil", "chat".
        center: Icon center point.
        size: Bounding box width/height in pixels.
        color: Stroke (and small accent-fill) color.
        stroke: Line width; defaults to a proportion of `size` so icons
            stay visually consistent at different sector/context sizes.
    """
    cx, cy = center.x(), center.y()
    r = size / 2.0
    pen = QPen(color, stroke if stroke is not None else max(1.3, size * 0.1))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    draw_fn = _ICONS.get(key)
    if draw_fn is None:
        # Unknown key: a small dot beats a crash or a silent blank sector.
        painter.setBrush(QBrush(color))
        painter.drawEllipse(center, r * 0.15, r * 0.15)
        return
    draw_fn(painter, cx, cy, r, color)


def _globe(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.drawEllipse(QPointF(cx, cy), r * 0.42, r)
    p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))


def _summary(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    widths = (1.0, 0.72, 0.48)
    top = cy - r * 0.6
    for i, w in enumerate(widths):
        y = top + i * (r * 0.6)
        p.drawLine(QPointF(cx - r * w, y), QPointF(cx + r * w, y))


def _bulb(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    br = r * 0.62
    bc = QPointF(cx, cy - r * 0.15)
    p.drawEllipse(bc, br, br)
    p.drawLine(QPointF(cx - br * 0.4, cy + br * 0.7), QPointF(cx + br * 0.4, cy + br * 0.7))
    p.drawLine(QPointF(cx - br * 0.28, cy + br * 1.0), QPointF(cx + br * 0.28, cy + br * 1.0))


def _search(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    gr = r * 0.58
    gc = QPointF(cx - r * 0.18, cy - r * 0.18)
    p.drawEllipse(gc, gr, gr)
    start = QPointF(gc.x() + gr * 0.72, gc.y() + gr * 0.72)
    end = QPointF(cx + r * 0.55, cy + r * 0.55)
    p.drawLine(start, end)


def _sliders(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    rows = ((cy - r * 0.55, -0.2), (cy, 0.35), (cy + r * 0.55, -0.5))
    for y, knob_offset in rows:
        p.drawLine(QPointF(cx - r, y), QPointF(cx + r, y))
        p.setBrush(QBrush(color))
        p.drawEllipse(QPointF(cx + knob_offset * r, y), r * 0.15, r * 0.15)
        p.setBrush(Qt.BrushStyle.NoBrush)


def _frame(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    arm = r * 0.55
    corners = (
        (cx - r * 0.85, cy - r * 0.85, 1, 1),
        (cx + r * 0.85, cy - r * 0.85, -1, 1),
        (cx - r * 0.85, cy + r * 0.85, 1, -1),
        (cx + r * 0.85, cy + r * 0.85, -1, -1),
    )
    for ox, oy, dx, dy in corners:
        p.drawLine(QPointF(ox, oy), QPointF(ox + dx * arm, oy))
        p.drawLine(QPointF(ox, oy), QPointF(ox, oy + dy * arm))


def _pencil(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    p.drawLine(QPointF(cx - r * 0.55, cy + r * 0.55), QPointF(cx + r * 0.6, cy - r * 0.6))
    tip = QPainterPath()
    tip.moveTo(cx - r * 0.72, cy + r * 0.72)
    tip.lineTo(cx - r * 0.55, cy + r * 0.55)
    tip.lineTo(cx - r * 0.38, cy + r * 0.72)
    tip.closeSubpath()
    p.setBrush(QBrush(color))
    p.drawPath(tip)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _chat(p: QPainter, cx: float, cy: float, r: float, color: QColor) -> None:
    rect = QRectF(cx - r * 0.95, cy - r * 0.75, r * 1.9, r * 1.4)
    p.drawRoundedRect(rect, r * 0.35, r * 0.35)
    tail = QPainterPath()
    tail.moveTo(cx - r * 0.35, cy + r * 0.65)
    tail.lineTo(cx - r * 0.1, cy + r * 0.65)
    tail.lineTo(cx - r * 0.45, cy + r * 1.05)
    tail.closeSubpath()
    p.setBrush(QBrush(color))
    p.drawPath(tail)
    p.setBrush(Qt.BrushStyle.NoBrush)


_ICONS = {
    "globe": _globe,
    "summary": _summary,
    "bulb": _bulb,
    "search": _search,
    "sliders": _sliders,
    "frame": _frame,
    "pencil": _pencil,
    "chat": _chat,
}
