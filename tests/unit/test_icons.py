# Cursor Bite — Icon System Tests
# ============================================================
# draw_icon() replaced emoji glyphs in the radial menu with plain
# QPainter-drawn line icons. These tests only guard against a crash or
# a silently-blank icon — pixel-perfect appearance is a visual concern,
# checked by hand against real screenshots, not something a unit test
# should assert on.

import pytest
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF

from ui.icons import draw_icon, _ICONS


@pytest.fixture()
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


def _render(key: str) -> QImage:
    img = QImage(32, 32, QImage.Format.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    draw_icon(painter, key, QPointF(16, 16), 20.0, QColor("#FFFFFF"))
    painter.end()
    return img


class TestAllKnownIcons:
    @pytest.mark.parametrize("key", sorted(_ICONS.keys()))
    def test_draws_without_raising(self, qapp, key):
        _render(key)  # must not raise

    @pytest.mark.parametrize("key", sorted(_ICONS.keys()))
    def test_actually_paints_something(self, qapp, key):
        """A regression guard against a no-op draw function: at least
        one non-transparent pixel must land in the image."""
        img = _render(key)
        has_ink = any(
            QColor(img.pixel(x, y)).alpha() > 0
            for x in range(32)
            for y in range(32)
        )
        assert has_ink, f"icon {key!r} produced a fully transparent image"


class TestUnknownIcon:
    def test_unknown_key_falls_back_to_a_dot_instead_of_crashing(self, qapp):
        img = _render("not-a-real-icon-key")
        has_ink = any(
            QColor(img.pixel(x, y)).alpha() > 0
            for x in range(32)
            for y in range(32)
        )
        assert has_ink

    def test_all_eight_menu_actions_have_a_real_icon(self):
        """Every action the radial menu can show must resolve to a real
        icon, not the unknown-key fallback dot."""
        from ui.radial_menu import MENU_ACTIONS

        for kind, label, icon_key, key_num, desc in MENU_ACTIONS:
            assert icon_key in _ICONS, f"{label!r} references unknown icon key {icon_key!r}"
