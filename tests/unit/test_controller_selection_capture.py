# Cursor Bite — Controller Selection Capture Tests
# ============================================================
# Selection capture used to run synchronously inside on_hotkey(),
# blocking the Qt event loop for up to ~500ms on every single hotkey
# press (a simulated Ctrl+C plus a clipboard poll loop). It now runs
# off the UI thread, kicked off only after the menu is already visible.
#
# These tests pin down the state machine that makes that safe:
#   - opening the menu must never touch the text provider synchronously
#   - a capture superseded by a second hotkey press must be dropped
#   - a capture that resolves after the user already picked an action
#     must not leak stale text into whatever session runs next

import pytest
from PyQt6.QtWidgets import QApplication

from app.controller import Controller
from domain.models import ProcessingResult


@pytest.fixture()
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def controller(qapp, monkeypatch):
    """A Controller with run_async replaced by a spy.

    The real run_async would schedule work on Cursor Bite's actual
    pipeline on a background thread pool, including a real Ctrl+C
    simulation — exactly what conftest.py's autouse no_real_keystrokes
    fixture exists to catch. Replacing it here keeps these tests
    focused on the generation/consumed state machine, not real
    threading.
    """
    calls = []

    def fake_run_async(target, on_result=None, on_error=None, **kwargs):
        calls.append({"target": target, "on_result": on_result, "on_error": on_error})
        return None

    monkeypatch.setattr("app.controller.run_async", fake_run_async)
    c = Controller()
    c.run_async_calls = calls
    yield c
    c.shutdown()


class TestMenuOpensWithoutBlocking:
    def test_on_hotkey_never_touches_the_text_provider_synchronously(
        self, controller, monkeypatch
    ):
        """Regression test for the ~500ms UI-thread freeze on every hotkey press."""
        touched = []

        class Spy:
            def extract_text(self, target_hwnd=None):
                touched.append(True)
                return ProcessingResult(success=True, data="must never run inline")

        monkeypatch.setattr(
            type(controller.pipeline), "text_provider", property(lambda self: Spy())
        )

        controller.on_hotkey()

        assert touched == [], "selection capture must go through run_async, never inline"
        assert len(controller.run_async_calls) == 1

    def test_on_hotkey_opens_the_menu_before_capture_resolves(self, controller):
        controller.on_hotkey()
        assert controller.is_menu_open is True
        # The capture worker was scheduled but nothing has resolved it yet.
        assert controller._pre_captured_text is None


class TestCaptureGenerations:
    def test_stale_capture_is_dropped_after_a_second_hotkey_press(self, controller):
        controller._capture_generation = 1
        controller._on_selection_captured(1, ProcessingResult(success=True, data="first press"))
        assert controller._pre_captured_text == "first press"

        # A second hotkey press bumps the generation before the first
        # capture's worker has a chance to report back.
        controller._capture_generation = 2
        controller._capture_consumed = False
        controller._on_selection_captured(1, ProcessingResult(success=True, data="stale"))

        assert controller._pre_captured_text == "first press"

    def test_failed_capture_from_a_superseded_press_is_also_dropped(self, controller):
        controller._capture_generation = 2
        controller._pre_captured_text = "current"

        controller._on_selection_capture_failed(1, RuntimeError("boom"))

        assert controller._pre_captured_text == "current"

    def test_failed_capture_clears_pre_captured_text(self, controller):
        controller._capture_generation = 1
        controller._pre_captured_text = "leftover"

        controller._on_selection_capture_failed(1, RuntimeError("boom"))

        assert controller._pre_captured_text is None


class TestCaptureConsumedRace:
    """A user fast enough to pick an action before capture resolves must
    not have that resolution land afterwards and leak into whatever
    session starts next."""

    def test_capture_resolving_after_the_action_already_started_is_ignored(self, controller):
        controller._capture_generation = 1
        controller._capture_consumed = True  # what _begin() sets

        controller._on_selection_captured(1, ProcessingResult(success=True, data="too late"))

        assert controller._pre_captured_text is None

    def test_begin_marks_the_capture_consumed(self, controller, monkeypatch):
        from domain.models import ActionKind

        monkeypatch.setattr(controller, "_get_panel", lambda: _FakePanel())
        assert controller._capture_consumed is False

        controller._begin(ActionKind.EXPLAIN)

        assert controller._capture_consumed is True


class _FakePanel:
    def show_loading(self, *a, **kw):
        pass


class TestRefreshMenuContext:
    def test_is_a_noop_once_the_menu_is_closed(self, controller):
        assert controller._menu is None
        controller._refresh_menu_context("some text")  # must not raise
