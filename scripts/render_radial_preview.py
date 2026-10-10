"""Render the shipped radial menu widget to a PNG for the README.

This draws the real ``ui.radial_menu.RadialMenu`` widget offscreen, with the
first sector (Translate) highlighted. It is not a capture of the app running
on Windows: fonts and anti-aliasing can differ from what you see there.

Usage (no display needed):

    QT_QPA_PLATFORM=offscreen python scripts/render_radial_preview.py docs/images/radial-menu.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtGui import QColor, QPainter, QPixmap  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

SCALE = 2
MARGIN = 20
BACKGROUND = "#2b2f36"


def main(out_path: str) -> None:
    app = QApplication([])
    from ui.radial_menu import RadialMenu

    menu = RadialMenu()
    menu.show_at(QPoint(300, 300), has_selection=True)
    menu._hovered_index = 0  # highlight "Translate" so the hover state is visible
    app.processEvents()

    widget = QPixmap(menu.width() * SCALE, menu.height() * SCALE)
    widget.setDevicePixelRatio(SCALE)
    widget.fill(QColor(0, 0, 0, 0))
    menu.render(widget)

    # Composite onto a neutral background so the menu's translucency shows.
    canvas = QPixmap((menu.width() + 2 * MARGIN) * SCALE, (menu.height() + 2 * MARGIN) * SCALE)
    canvas.setDevicePixelRatio(SCALE)
    canvas.fill(QColor(BACKGROUND))
    painter = QPainter(canvas)
    painter.drawPixmap(MARGIN, MARGIN, widget)
    painter.end()

    if not canvas.save(out_path):
        raise SystemExit(f"Could not write {out_path}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/images/radial-menu.png")
