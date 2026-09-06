# Cursor Bite — Modern Result Window Tests
# ============================================================
# Tests for ResultWindow formatting, actions, and non-focus-stealing loading.

import pytest
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication

from ui.result_window import ResultWindow, format_search_html


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_result_window_loading_state(qapp):
    """Test show_loading updates header and title without stealing focus."""
    window = ResultWindow()
    window.show_loading("Explain with AI", QPoint(400, 400))

    assert "Explain" in window._title.text()
    assert not window._copy_button.isEnabled()
    assert window._raw_text == ""


def test_result_window_show_result(qapp):
    """Test show_result sets text, meta, and enables copy button."""
    window = ResultWindow()
    window.show_result("Explain", "This is an explanation of the topic.", meta="llama3.2 · 120ms")

    assert window._title.text() == "Explain"
    assert window._raw_text == "This is an explanation of the topic."
    assert window._meta_chip.text() == "llama3.2 · 120ms"
    assert window._copy_button.isEnabled()


def test_result_window_show_error(qapp):
    """Test show_error formats error message clearly and disables copy."""
    window = ResultWindow()
    window.show_error("Translation", "Target language not supported.", meta="Argos")

    assert window._title.text() == "Translation"
    assert "Target language not supported" in window._body.toHtml()
    assert not window._copy_button.isEnabled()


def test_format_search_html():
    """Test formatting search results as cards."""
    results = [
        {"title": "Test Title", "url": "https://example.com/test", "snippet": "A test snippet"},
    ]
    html = format_search_html(results)
    assert "Test Title" in html
    assert "example.com" in html
    assert "A test snippet" in html
    assert "https://example.com/test" in html


def test_result_window_streaming(qapp):
    """Test progressive token streaming and finalization in ResultWindow."""
    window = ResultWindow()
    window.show_loading("Explain", QPoint(400, 400))

    # Stream first token
    window.append_stream_token("Hello")
    assert window._is_streaming
    assert "Hello ▌" in window._body.toPlainText()
    assert "Generating" in window._status.text()

    # Stream second token
    window.append_stream_token(" world!")
    assert "Hello world! ▌" in window._body.toPlainText()

    # Finish stream
    window.finish_stream(meta="llama3.2 · 80ms")
    assert not window._is_streaming
    assert window._body.toPlainText() == "Hello world!"
    assert window._copy_button.isEnabled()
    assert window._meta_chip.text() == "llama3.2 · 80ms"


def test_result_window_pin_toggle(qapp):
    """Test Pin button toggles pinned state and prevents accidental dismiss."""
    window = ResultWindow()
    window.show_result("Explain", "Sample content")

    assert not window._is_pinned
    assert "Esc to close" in window._hint.text()

    # Toggle pin
    window._toggle_pin()
    assert window._is_pinned
    assert "Pinned" in window._hint.text()

    # Regular dismiss should be ignored when pinned
    window.dismiss(force=False)
    assert window.isVisible()

    # Force dismiss (e.g. Esc or close button) should work
    window.dismiss(force=True)
    assert not window.isVisible()


def test_result_window_detach(qapp):
    """Test detaching to a standalone window."""
    window = ResultWindow()
    window.show_result("Explain", "Detached text test", meta="llama3.2")

    window._on_detach()
    assert window._detached_window is not None
    assert window._detached_window.isVisible()
    assert window._detached_window._text == "Detached text test"
    window._detached_window.close()

