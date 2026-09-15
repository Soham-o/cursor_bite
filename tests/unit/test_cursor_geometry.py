# Cursor Bite — Cursor Geometry Tests
# ============================================================
# Multi-monitor virtual-screen bounds and edge detection, exercised
# against a fake win32api rather than a real desktop so the numbers are
# exact and the suite doesn't depend on whatever monitors happen to be
# attached to the machine running it.

import pytest

from infrastructure.os import cursor as cur

# SM_XVIRTUALSCREEN=76, SM_YVIRTUALSCREEN=77, SM_CXVIRTUALSCREEN=78,
# SM_CYVIRTUALSCREEN=79, SM_CMONITORS=80 — see get_virtual_screen_bounds().
_METRICS = {76: -1920, 77: 0, 78: 5760, 79: 1080, 80: 3}


@pytest.fixture()
def fake_win32api(monkeypatch):
    monkeypatch.setattr(cur.win32api, "GetSystemMetrics", lambda code: _METRICS[code])


class TestVirtualScreenBounds:
    def test_reports_combined_multi_monitor_geometry(self, fake_win32api):
        left, top, width, height = cur.get_virtual_screen_bounds()
        assert (left, top, width, height) == (-1920, 0, 5760, 1080)

    def test_monitor_count(self, fake_win32api):
        assert cur.get_monitor_count() == 3


class TestCursorPosition:
    def test_uses_qcursor_when_available(self, monkeypatch):
        from PyQt6.QtCore import QPoint

        monkeypatch.setattr(
            "PyQt6.QtGui.QCursor.pos", staticmethod(lambda: QPoint(123, 456))
        )
        pos = cur.get_cursor_position()
        assert (pos.x(), pos.y()) == (123, 456)

    def test_falls_back_to_win32_when_qcursor_unavailable(self, monkeypatch, fake_win32api):
        def broken_qcursor_import(*a, **kw):
            raise RuntimeError("no Qt widget backend available")

        # Force the QCursor path to fail so get_cursor_position() falls
        # through to win32api.GetCursorPos.
        import PyQt6.QtGui

        class _BrokenCursor:
            @staticmethod
            def pos():
                raise RuntimeError("no display")

        monkeypatch.setattr(PyQt6.QtGui, "QCursor", _BrokenCursor)
        monkeypatch.setattr(cur.win32api, "GetCursorPos", lambda: (10, 20))

        pos = cur.get_cursor_position_tuple()
        assert pos == (10, 20)

    def test_falls_back_to_screen_center_when_everything_fails(self, monkeypatch, fake_win32api):
        import PyQt6.QtGui

        class _BrokenCursor:
            @staticmethod
            def pos():
                raise RuntimeError("no display")

        monkeypatch.setattr(PyQt6.QtGui, "QCursor", _BrokenCursor)

        def broken_get_cursor_pos():
            raise RuntimeError("win32 also unavailable")

        monkeypatch.setattr(cur.win32api, "GetCursorPos", broken_get_cursor_pos)

        pos = cur.get_cursor_position()
        # Center of the fake virtual screen: left + width // 2, top + height // 2
        assert (pos.x(), pos.y()) == (-1920 + 5760 // 2, 0 + 1080 // 2)


class TestNearEdgeDetection:
    def test_center_of_screen_is_not_near_any_edge(self, monkeypatch, fake_win32api):
        monkeypatch.setattr(cur, "get_cursor_position", lambda: _point(960, 540))
        flags = cur.is_cursor_near_edge(margin=50)
        assert not any(flags.values())

    def test_left_edge(self, monkeypatch, fake_win32api):
        monkeypatch.setattr(cur, "get_cursor_position", lambda: _point(-1920, 500))
        flags = cur.is_cursor_near_edge(margin=50)
        assert flags["left"] is True
        assert flags["right"] is False

    def test_bottom_right_corner(self, monkeypatch, fake_win32api):
        # Virtual screen spans x:[-1920, 3840), y:[0, 1080).
        monkeypatch.setattr(cur, "get_cursor_position", lambda: _point(3839, 1079))
        flags = cur.is_cursor_near_edge(margin=50)
        assert flags["corner_br"] is True
        assert flags["corner_tl"] is False

    def test_margin_widens_the_detected_band(self, monkeypatch, fake_win32api):
        monkeypatch.setattr(cur, "get_cursor_position", lambda: _point(-1870, 500))
        assert cur.is_cursor_near_edge(margin=10)["left"] is False
        assert cur.is_cursor_near_edge(margin=100)["left"] is True


def _point(x, y):
    from PyQt6.QtCore import QPoint

    return QPoint(x, y)
