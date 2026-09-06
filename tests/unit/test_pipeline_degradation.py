# Cursor Bite — Graceful Degradation Tests
# ============================================================
# Every optional component (Tesseract, Ollama, Argos, an internet
# connection) can be absent, and the app is documented as starting and
# running the same either way — the missing piece disables one action
# and nothing else.
#
# The gap this covers is the *Python package* being absent rather than
# the engine behind it. Providers are imported lazily, so a missing
# package surfaced as an ImportError from whichever code path touched
# the provider first — which meant the tray's "Check Components"
# dialog, whose entire job is to report what is missing, was the thing
# that broke when something was missing.
#
# Which package breaks which provider is not uniform, and the tests
# below use the real mapping rather than an assumed one:
#
#   pyperclip  → module-level in os.clipboard, so os.selected_text
#                cannot be imported without it. Handled here.
#   requests   → module-level in ai.ollama and search.web_search.
#   bs4        → module-level in search.web_search.
#   PIL        → module-level in ocr.tesseract.
#   pytesseract, argostranslate → imported inside their methods, and
#                already handled there: those providers report
#                themselves unavailable without any help from the
#                pipeline. Their own suites cover that.
#
# Imports are blocked the way a real partial install presents them: by
# making the import itself fail.

import builtins
import sys

import pytest

from app.pipeline import Pipeline, _UnavailableProvider
from domain.models import ActionKind


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def block_imports(monkeypatch):
    """Make the named top-level packages unimportable for one test.

    Returns a callable taking package names. Provider modules are
    evicted from sys.modules alongside them, because the import under
    test is deferred: a module an earlier test already imported
    successfully would otherwise be served from cache and never re-run
    its own imports, so the block would silently do nothing.

    config and domain are deliberately left cached — the settings
    singleton a test has patched has to stay the one the reloaded
    provider sees.
    """
    real_import = builtins.__import__

    def block(*packages):
        blocked = set(packages)

        for name in list(sys.modules):
            root = name.split(".")[0]
            if root in blocked or root == "infrastructure":
                monkeypatch.delitem(sys.modules, name, raising=False)

        def guard(name, *args, **kwargs):
            if name.split(".")[0] in blocked:
                # name= is what CPython sets on a real missing-module
                # ImportError, and the code under test reads it to name
                # the package in its hint.
                raise ImportError(f"No module named '{name}'", name=name)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", guard)

    return block


@pytest.fixture()
def ready(clean_settings):
    """Settings that permit every action, so only the missing package bites."""
    clean_settings.set("privacy.offline_mode", False)
    clean_settings.set("privacy.external_processing_warning", False)
    clean_settings.set("ai.enabled", True)
    return clean_settings


ALL_PACKAGES = ("pyperclip", "requests", "bs4", "PIL", "mss")


# ── The status dialog survives a partial install ──────────────────────


class TestComponentStatus:
    """The one thing that must work when nothing else does."""

    def test_status_is_reported_when_every_package_is_missing(
        self, ready, block_imports
    ):
        block_imports(*ALL_PACKAGES)

        status = Pipeline().get_component_status()

        assert set(status) >= {"text", "translation", "ocr", "ai", "search"}
        assert all("name" in entry for entry in status.values())

    def test_missing_packages_are_reported_unavailable(self, ready, block_imports):
        block_imports(*ALL_PACKAGES)

        status = Pipeline().get_component_status()

        for slot in ("text", "ocr", "ai", "search"):
            assert status[slot]["available"] is False, slot

    def test_the_hint_names_the_missing_package(self, ready, block_imports):
        """Sending someone to install Tesseract when the missing piece is
        a Python package wastes their time. The name comes from the failed
        import, not from a guess about the slot."""
        block_imports("PIL")

        hint = Pipeline().get_component_status()["ocr"]["hint"]

        assert "PIL" in hint
        assert "pip install" in hint

    def test_the_privacy_gateway_is_unaffected(self, ready, block_imports):
        """Nothing about privacy enforcement depends on an optional package."""
        block_imports(*ALL_PACKAGES)

        status = Pipeline().get_component_status()

        assert status["privacy_gateway"]["available"] is True

    def test_recheck_does_not_raise(self, ready, block_imports):
        block_imports(*ALL_PACKAGES)

        assert Pipeline().recheck_components()


# ── Actions fail cleanly, one at a time ───────────────────────────────


class TestActionsDegrade:
    def test_a_missing_ocr_package_fails_the_capture(self, ready, block_imports):
        block_imports("PIL")

        result = Pipeline().process(ActionKind.CAPTURE_TEXT, image_bytes=b"PNGDATA")

        assert result.success is False
        assert "pip install" in result.error

    def test_a_missing_ai_package_fails_the_explain(self, ready, block_imports):
        block_imports("requests")

        result = Pipeline().process(ActionKind.EXPLAIN, context_text="a monad")

        assert result.success is False
        assert "pip install" in result.error

    def test_a_missing_search_package_fails_the_search(self, ready, block_imports):
        block_imports("bs4")

        result = Pipeline().process(ActionKind.SEARCH_WEB, context_text="a monad")

        assert result.success is False
        assert "pip install" in result.error

    def test_a_missing_clipboard_package_fails_extraction(self, ready, block_imports):
        """With no text provider there is no text, so the action stops at
        prepare() with a message rather than a traceback."""
        block_imports("pyperclip")

        pipeline = Pipeline()
        assert isinstance(pipeline.text_provider, _UnavailableProvider), (
            "the block did not take effect — this test must never reach the "
            "real provider, which types Ctrl+C into the foreground window"
        )

        prepared = pipeline.prepare(ActionKind.EXPLAIN)

        assert prepared.is_ready is False
        assert "pyperclip" in prepared.error

    def test_one_missing_package_does_not_disable_the_others(
        self, ready, block_imports
    ):
        """Degradation is per-component: OCR being absent says nothing
        about whether AI works."""
        block_imports("PIL")

        status = Pipeline().get_component_status()

        assert status["ocr"]["available"] is False
        assert isinstance(status["ai"]["available"], bool)

    def test_an_injected_provider_is_never_replaced(self, ready, block_imports):
        """The stub is a fallback for the lazy import, not a wrapper —
        a provider passed in by the caller (or a test) is used as given."""
        block_imports("PIL")

        class Injected:
            def name(self):
                return "Injected OCR"

            def is_available(self):
                return True

        pipeline = Pipeline(ocr_provider=Injected())

        assert pipeline.get_component_status()["ocr"]["available"] is True


# ── The stub itself ───────────────────────────────────────────────────


class TestUnavailableProvider:
    @pytest.fixture()
    def stub(self):
        return _UnavailableProvider("OCR", "pytesseract")

    def test_it_reports_itself_unavailable(self, stub):
        assert stub.is_available() is False

    def test_its_name_says_why(self, stub):
        """It appears verbatim in the Components dialog."""
        assert "OCR" in stub.name()
        assert "not installed" in stub.name()

    def test_its_hint_is_actionable(self, stub):
        assert "pytesseract" in stub.unavailable_hint
        assert "pip install" in stub.unavailable_hint

    @pytest.mark.parametrize(
        "call",
        [
            lambda p: p.extract_text(),
            lambda p: p.extract(),
            lambda p: p.recognize(b"PNGDATA"),
            lambda p: p.translate("hello", target_lang="fr"),
            lambda p: p.generate("a prompt"),
            lambda p: p.search("a query"),
        ],
    )
    def test_every_method_returns_a_failure_instead_of_raising(self, stub, call):
        result = call(stub)

        assert result.success is False
        assert "pytesseract" in result.error

    def test_translate_keeps_the_language_fields(self, stub):
        """_action_translate reads them off the result unconditionally."""
        result = stub.translate("hello", source_lang="en", target_lang="fr")

        assert result.source_language == "en"
        assert result.target_language == "fr"

    def test_search_echoes_the_query(self, stub):
        assert stub.search("a query").query == "a query"

    def test_the_metadata_accessors_are_empty_not_absent(self, stub):
        assert stub.detect_language("hello") is None
        assert stub.supported_languages() == []
        assert stub.list_models() == []
        assert stub.get_default_model() == ""

    def test_invalidate_is_a_no_op(self, stub):
        """recheck_components() calls it on every provider."""
        stub.invalidate()
        assert stub.is_available() is False
