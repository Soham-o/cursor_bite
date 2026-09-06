# Cursor Bite — Test Configuration
# ============================================================
# Makes the project importable from the tests, provides the shared
# settings fixture, and works around a platform-level crash described
# below.

import logging
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ── Workaround: logging + asyncio under pytest ─────────────────────
#
# Since Python 3.12, LogRecord.__init__ calls asyncio.current_task()
# for every record it builds, whenever asyncio happens to be imported
# (pytest and its plugins import it). On some Windows CPython builds
# that call faults inside the _asyncio C extension when no event loop
# is running, taking the whole interpreter down with an access
# violation — so a single logger.warning() anywhere in the code under
# test kills the run.
#
# Reproducible with nothing but a two-line test file:
#     import asyncio; asyncio.current_task()
#
# logAsyncioTasks is CPython's documented switch for that branch. The
# field it populates (LogRecord.taskName) is one Cursor Bite never
# formats, so turning it off costs the tests nothing. This is scoped
# to the test harness deliberately: the application is not affected
# and its logging is left exactly as it ships.
logging.logAsyncioTasks = False


# ── Safety net: no keystrokes to the real desktop ──────────────────


@pytest.fixture(autouse=True)
def no_real_keystrokes(monkeypatch):
    """Stop any test from sending a real Ctrl+C to the foreground window.

    SelectedTextProvider works by pressing Ctrl+C in whatever window has
    focus. Under test that window belongs to the person running the
    suite, so a provider that reaches the real implementation types into
    their editor and overwrites their clipboard. It is not hypothetical:
    it happened while these tests were being written, when a fake failed
    to take effect and the provider quietly did the real thing instead.

    Autouse, so it protects tests that never think about the clipboard.
    Tests that do install their own fake copy afterwards, which takes
    precedence; this only fires if the real one is reached by accident.
    """
    from infrastructure.os import clipboard as clipboard_module
    from infrastructure.os import selected_text as selected_text_module

    def refuse() -> None:
        raise AssertionError(
            "A test reached the real simulate_copy_selection(), which would "
            "send Ctrl+C to the foreground window. Install a fake instead."
        )

    # Patched in both modules: selected_text imports the name directly,
    # so rebinding it on clipboard alone would miss the live reference.
    monkeypatch.setattr(clipboard_module, "simulate_copy_selection", refuse)
    monkeypatch.setattr(selected_text_module, "simulate_copy_selection", refuse)


# ── Shared fixtures ────────────────────────────────────────────────


@pytest.fixture()
def clean_settings():
    """Run a test against empty settings, restoring the real ones after.

    Settings is a module-level singleton, so a test that writes to it
    would otherwise leak into every test that follows. Starting from an
    empty dict also means each test states the values it depends on
    instead of inheriting whatever config.json happens to hold.
    """
    from config.settings import settings

    original = dict(settings._config)
    settings._config = {}
    yield settings
    settings._config = original


@pytest.fixture()
def clear_cache():
    """Empty the in-memory cache before and after a test.

    The cache is a singleton keyed on text, so a translation cached by
    one test would be served to the next one from memory.
    """
    from infrastructure.storage.cache import cache

    cache.clear()
    yield cache
    cache.clear()
