# Cursor Bite — Capture Readiness Tests
# ============================================================
# Regression coverage for a bug found during a live smoke test: Capture
# Text (OCR) probed Tesseract's own availability before opening the
# region selector, but never checked that the *screen-capture* package
# ('mss') was importable. On a machine with Tesseract installed but
# 'mss' missing, dragging a region crashed with an unhandled
# ModuleNotFoundError instead of the actionable "install this package"
# message every other optional component gives.
#
# `infrastructure.os.screen_capture` imports mss at module level, so
# these tests fake its presence/absence in sys.modules rather than
# relying on whether the real package happens to be installed in
# whatever environment runs the suite.

import sys
import types

import pytest
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication

from app.controller import Controller
from domain.models import ActionKind


@pytest.fixture()
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture()
def controller(qapp):
    c = Controller()
    yield c
    c.shutdown()


@pytest.fixture()
def mss_missing(monkeypatch):
    """Make `import mss` fail, and evict any cached screen_capture module
    so it re-attempts the import instead of serving a cached success."""
    monkeypatch.delitem(sys.modules, "mss", raising=False)
    monkeypatch.delitem(sys.modules, "mss.tools", raising=False)
    monkeypatch.delitem(sys.modules, "infrastructure.os.screen_capture", raising=False)

    import builtins

    real_import = builtins.__import__

    def guard(name, *args, **kwargs):
        if name == "mss" or name.startswith("mss."):
            raise ModuleNotFoundError("No module named 'mss'", name="mss")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)


@pytest.fixture()
def mss_present(monkeypatch):
    """Fake a successfully-importable 'mss' regardless of the real machine."""
    fake = types.ModuleType("mss")
    monkeypatch.setitem(sys.modules, "mss", fake)


class _AlwaysAvailableOCR:
    def is_available(self):
        return True


class TestScreenCaptureAvailability:
    def test_reports_unavailable_when_mss_is_missing(self, controller, mss_missing):
        assert controller._screen_capture_available() is False

    def test_reports_available_when_mss_importable(self, controller, mss_present):
        assert controller._screen_capture_available() is True


class TestProbeCaptureReadiness:
    def test_false_when_mss_missing_even_if_tesseract_is_available(
        self, controller, mss_missing, monkeypatch
    ):
        monkeypatch.setattr(
            type(controller.pipeline), "ocr_provider", property(lambda self: _AlwaysAvailableOCR())
        )
        assert controller._probe_capture_readiness() is False

    def test_true_when_both_mss_and_tesseract_are_available(
        self, controller, mss_present, monkeypatch
    ):
        monkeypatch.setattr(
            type(controller.pipeline), "ocr_provider", property(lambda self: _AlwaysAvailableOCR())
        )
        assert controller._probe_capture_readiness() is True


class TestCaptureAndPrepareDegradesGracefully:
    def test_missing_mss_is_an_actionable_prepared_error_not_a_crash(
        self, controller, mss_missing
    ):
        """This is the exact path that previously raised an unhandled
        ModuleNotFoundError out of a worker thread."""
        prepared = controller._capture_and_prepare(QRect(0, 0, 10, 10))

        assert prepared.action == ActionKind.CAPTURE_TEXT
        assert prepared.is_ready is False
        assert "mss" in prepared.error
        assert "pip install" in prepared.error
