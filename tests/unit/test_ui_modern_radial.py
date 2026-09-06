# Cursor Bite — Modern UI & Radial Menu Tests
# ============================================================
# Tests for the redesigned Radial HUD menu and modern UI components.

import pytest
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication

from domain.models import ActionKind
from ui.radial_menu import RadialMenu, MENU_ACTIONS, INDEX_TO_ACTION


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance exists for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_radial_menu_initialization(qapp):
    """Test that RadialMenu initializes with 8 actions and correct compact size."""
    menu = RadialMenu()
    assert 180 <= menu.width() <= 240
    assert 180 <= menu.height() <= 240
    assert len(MENU_ACTIONS) == 8
    assert len(INDEX_TO_ACTION) == 8
    assert not menu.is_open


def test_radial_menu_hit_testing(qapp):
    """Test that each of the 8 sectors correctly maps to angles/sectors."""
    menu = RadialMenu()
    cx = menu.width() // 2
    cy = menu.height() // 2

    # Sector 0 is top (12 o'clock), test at radius ~70
    top_pos = QPoint(cx, cy - 70)
    assert menu._hit_sector(top_pos) == 0
    assert INDEX_TO_ACTION[0] == ActionKind.TRANSLATE

    # Sector 2 is right (3 o'clock)
    right_pos = QPoint(cx + 70, cy)
    assert menu._hit_sector(right_pos) == 2
    assert INDEX_TO_ACTION[2] == ActionKind.EXPLAIN

    # Sector 4 is bottom (6 o'clock)
    bottom_pos = QPoint(cx, cy + 70)
    assert menu._hit_sector(bottom_pos) == 4
    assert INDEX_TO_ACTION[4] == ActionKind.SETTINGS

    # Sector 6 is left (9 o'clock)
    left_pos = QPoint(cx - 70, cy)
    assert menu._hit_sector(left_pos) == 6
    assert INDEX_TO_ACTION[6] == ActionKind.REWRITE

    # Center hub click should return -1 (no sector)
    center_pos = QPoint(cx, cy)
    assert menu._hit_sector(center_pos) == -1


def test_radial_menu_click_action(qapp):
    """Test clicking on a sector emits action_selected signal."""
    menu = RadialMenu()
    menu.open_at(QPoint(500, 500))

    selected_actions = []
    menu.action_selected.connect(lambda a: selected_actions.append(a))

    cx = menu.width() // 2
    cy = menu.height() // 2
    click_pos = QPointF(float(cx), float(cy - 70))  # Sector 0: Translate

    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        click_pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    menu.mousePressEvent(event)

    assert len(selected_actions) == 1
    assert selected_actions[0] == ActionKind.TRANSLATE



def test_radial_menu_number_keys(qapp):
    """Test number keys 1-8 directly trigger their corresponding action."""
    menu = RadialMenu()
    menu.open_at(QPoint(500, 500))

    selected_actions = []
    menu.action_selected.connect(lambda a: selected_actions.append(a))

    # Press key '3' for Explain
    key_3 = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_3,
        Qt.KeyboardModifier.NoModifier,
        "3",
    )
    menu.keyPressEvent(key_3)

    assert len(selected_actions) == 1
    assert selected_actions[0] == ActionKind.EXPLAIN


def test_radial_menu_arrow_navigation(qapp):
    """Test navigating with arrow keys updates hovered sector and Enter triggers."""
    menu = RadialMenu()
    menu.open_at(QPoint(500, 500))

    hovered = []
    selected = []
    menu.action_hovered.connect(lambda a: hovered.append(a))
    menu.action_selected.connect(lambda a: selected.append(a))

    # Start at -1, Right arrow moves to index 0
    key_right = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Right,
        Qt.KeyboardModifier.NoModifier,
    )
    menu.keyPressEvent(key_right)
    assert menu._hovered_index == 0
    assert len(hovered) == 1
    assert hovered[-1] == ActionKind.TRANSLATE

    # Another right moves to index 1 (Summarize)
    menu.keyPressEvent(key_right)
    assert menu._hovered_index == 1
    assert hovered[-1] == ActionKind.SUMMARIZE

    # Enter triggers the hovered action
    key_enter = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
    )
    menu.keyPressEvent(key_enter)
    assert len(selected) == 1
    assert selected[0] == ActionKind.SUMMARIZE


def test_radial_menu_escape_closes(qapp):
    """Test pressing Escape closes the radial menu."""
    menu = RadialMenu()
    menu.open_at(QPoint(500, 500))
    closed = []
    menu.menu_closed.connect(lambda: closed.append(True))

    key_esc = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )
    menu.keyPressEvent(key_esc)
    assert not menu.is_open or len(closed) > 0
