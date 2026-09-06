# Cursor Bite — Selected Text Provider Tests
# ============================================================
# SelectedTextProvider is the one component that writes to something
# the user owns and did not hand over: the Windows clipboard. Sending
# Ctrl+C to the foreground window overwrites it, so the provider takes
# a snapshot first and puts it back afterwards.
#
# These tests pin down the two properties that make that safe:
#
#   1. The clipboard the user had is restored on EVERY path, including
#      the ones where the extraction failed or raised.
#   2. Text is never carried in memory after the call returns, and a
#      no-op Ctrl+C is never mistaken for a selection — reading the
#      clipboard blindly could process something the user copied from
#      a password manager, which is precisely what the snapshot
#      comparison exists to prevent.
#
# No Windows APIs are touched: the clipboard and the Ctrl+C keystroke
# are both replaced with fakes, so this runs anywhere.

import pytest

from domain.models import ContextSource
from infrastructure.os import selected_text as st


# ── Fakes ─────────────────────────────────────────────────────────────


class FakeClipboard:
    """In-memory stand-in for SafeClipboard, with call counting."""

    def __init__(self, content: str = "") -> None:
        self.content = content
        self._saved = None
        self._saved_set = False

        self.save_calls = 0
        self.restore_calls = 0
        self.discard_calls = 0

        self.restore_succeeds = True

    def read(self):
        return self.content

    def save(self) -> bool:
        self._saved = self.content
        self._saved_set = True
        self.save_calls += 1
        return True

    def restore(self) -> bool:
        self.restore_calls += 1
        if not self._saved_set:
            return True
        if self.restore_succeeds:
            self.content = self._saved
        self._saved = None
        self._saved_set = False
        return self.restore_succeeds

    def discard_saved(self) -> None:
        self.discard_calls += 1
        self._saved = None
        self._saved_set = False

    @property
    def has_saved_content(self) -> bool:
        return self._saved_set


@pytest.fixture()
def fake_env(monkeypatch):
    """Replace the clipboard and Ctrl+C, and remove the polling delay.

    Returns a small helper that installs a clipboard and decides what
    the simulated Ctrl+C does.
    """
    # The real provider polls 8 times at 40ms. Nothing here waits on a
    # real application, so the delay is pure test latency.
    monkeypatch.setattr(st, "_COPY_POLL_INTERVAL", 0.0)
    monkeypatch.setattr(st, "_COPY_POLL_ATTEMPTS", 2)

    class Env:
        def __init__(self) -> None:
            self.clipboard = FakeClipboard()
            self.copy_calls = 0

        def install(self, existing="", copies=None, raises=None):
            """Args:
                existing: what the clipboard holds before extraction.
                copies: what Ctrl+C puts on the clipboard (None = no-op,
                    which is what happens with nothing selected).
                raises: exception for the Ctrl+C call to raise.
            """
            self.clipboard = FakeClipboard(existing)

            def fake_copy():
                self.copy_calls += 1
                if raises is not None:
                    raise raises
                if copies is not None:
                    self.clipboard.content = copies

            monkeypatch.setattr(st, "clipboard", self.clipboard)
            monkeypatch.setattr(st, "simulate_copy_selection", fake_copy)
            return self.clipboard

    return Env()


@pytest.fixture()
def provider():
    return st.SelectedTextProvider()


# ── The restore invariant ─────────────────────────────────────────────


class TestClipboardIsAlwaysRestored:
    """Whatever happens, the user gets their clipboard back."""

    def test_restored_after_successful_capture(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        clip = fake_env.install(existing="user's own clipboard", copies="the selection")

        result = provider.extract_text()

        assert result.success
        assert result.data == "the selection"
        assert clip.content == "user's own clipboard"
        assert clip.save_calls == 1
        assert clip.restore_calls == 1

    def test_restored_when_nothing_was_selected(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        clip = fake_env.install(existing="user's own clipboard", copies=None)

        provider.extract_text()

        assert clip.content == "user's own clipboard"
        assert clip.restore_calls == 1

    def test_restored_when_copy_raises(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        clip = fake_env.install(
            existing="user's own clipboard",
            raises=RuntimeError("SendInput failed"),
        )

        result = provider.extract_text()

        assert result.success is False
        assert clip.content == "user's own clipboard"
        assert clip.restore_calls == 1, "the finally block must run on the error path"

    def test_no_text_retained_after_the_call(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        clip = fake_env.install(existing="secret note", copies="the selection")

        provider.extract_text()

        assert clip.has_saved_content is False

    def test_snapshot_dropped_even_with_protection_off(
        self, clean_settings, fake_env, provider
    ):
        """Protection off leaves the copy on the clipboard — but not in RAM."""
        clean_settings.set("privacy.clipboard_protection", False)
        clip = fake_env.install(existing="user's own clipboard", copies="the selection")

        result = provider.extract_text()

        assert result.success
        assert clip.content == "the selection", "the copy deliberately stays put"
        assert clip.save_calls == 0
        assert clip.restore_calls == 0
        assert clip.discard_calls == 1
        assert clip.has_saved_content is False

    def test_failed_restore_does_not_fail_the_extraction(
        self, clean_settings, fake_env, provider
    ):
        """A clipboard another process has locked is logged, not raised."""
        clean_settings.set("privacy.clipboard_protection", True)
        clip = fake_env.install(existing="user's own clipboard", copies="the selection")
        clip.restore_succeeds = False

        result = provider.extract_text()

        assert result.success
        assert result.data == "the selection"


# ── Telling a selection from clipboard leftovers ──────────────────────


class TestSourceAttribution:
    """A no-op Ctrl+C must never be reported as a selection."""

    def test_changed_clipboard_is_reported_as_a_selection(
        self, clean_settings, fake_env, provider
    ):
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="old", copies="freshly selected")

        result = provider.extract_text()

        assert result.data == "freshly selected"
        assert result.metadata["context_source"] == ContextSource.SELECTED_TEXT.value

    def test_unchanged_clipboard_is_reported_as_the_clipboard(
        self, clean_settings, fake_env, provider
    ):
        """Nothing selected: the fallback is used, and labelled as such."""
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="left over from earlier", copies=None)

        result = provider.extract_text()

        assert result.success
        assert result.data == "left over from earlier"
        assert result.metadata["context_source"] == ContextSource.CLIPBOARD.value

    def test_identical_copy_is_not_credited_to_the_selection(
        self, clean_settings, fake_env, provider
    ):
        """Copying text identical to the clipboard is indistinguishable
        from a no-op, so it must take the conservative label."""
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="same text", copies="same text")

        result = provider.extract_text()

        assert result.metadata["context_source"] == ContextSource.CLIPBOARD.value

    def test_no_selection_and_empty_clipboard_is_an_actionable_error(
        self, clean_settings, fake_env, provider
    ):
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="", copies=None)

        result = provider.extract_text()

        assert result.success is False
        assert "select" in result.error.lower()

    def test_whitespace_only_clipboard_is_not_a_fallback(
        self, clean_settings, fake_env, provider
    ):
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="   \n\t ", copies=None)

        result = provider.extract_text()

        assert result.success is False

    def test_fallback_can_be_turned_off(self, clean_settings, fake_env):
        """A selection-only provider must not read the standing clipboard."""
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="left over from earlier", copies=None)

        strict = st.SelectedTextProvider(allow_clipboard_fallback=False)
        result = strict.extract_text()

        assert result.success is False
        assert "select" in result.error.lower()


# ── Result shape ──────────────────────────────────────────────────────


class TestResultShape:
    """What the pipeline reads off the result."""

    def test_captured_text_is_stripped(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="old", copies="  padded selection \n")

        result = provider.extract_text()

        assert result.data == "padded selection"

    def test_protection_flag_is_reported(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="old", copies="new")

        result = provider.extract_text()

        assert result.metadata["clipboard_protected"] is True

    def test_extract_is_an_alias_for_extract_text(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="old", copies="the selection")

        assert provider.extract().data == "the selection"

    def test_ctrl_c_is_sent_exactly_once(self, clean_settings, fake_env, provider):
        clean_settings.set("privacy.clipboard_protection", True)
        fake_env.install(existing="old", copies="new")

        provider.extract_text()

        assert fake_env.copy_calls == 1

    def test_provider_is_always_available(self, provider):
        """There is no optional dependency to probe on Windows."""
        assert provider.is_available() is True
        assert provider.source() == ContextSource.SELECTED_TEXT
        assert provider.name()
