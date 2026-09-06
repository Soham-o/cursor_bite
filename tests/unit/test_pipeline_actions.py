# Cursor Bite — Pipeline Action Tests
# ============================================================
# Every branch of Pipeline._execute_action, driven through fake
# providers. Nothing here starts Ollama, installs an Argos package,
# calls Tesseract, or reaches the network — the point is to test the
# pipeline's own decisions, which is where the behaviour the user sees
# actually lives:
#
#   - which provider an action reaches for
#   - what happens when that provider is missing, off, or throws
#   - whether the cache is allowed to hold the user's text
#   - what the error message says when something can't be done
#
# The privacy boundary is covered in tests/integration/. Here it only
# appears where it changes an action's behaviour (offline mode blocking
# search, no-data-retention disabling the translation cache).

import pytest

from app.pipeline import Pipeline, PreparedRequest
from domain.models import (
    ActionKind,
    AIResult,
    ContextSource,
    OCRResult,
    ProcessingResult,
    SearchResult,
    TranslationResult,
)


# ── Fakes ─────────────────────────────────────────────────────────────
#
# Deliberately not subclasses of the domain ABCs: these implement only
# the methods the pipeline calls, so an unexpected call fails loudly
# with an AttributeError instead of quietly returning a stub value.


class FakeTextProvider:
    def __init__(self, text="selected text", success=True, error=None, source=None):
        self._text = text
        self._success = success
        self._error = error
        self._source = source or ContextSource.SELECTED_TEXT.value
        self.calls = 0

    def name(self):
        return "Fake Text"

    def is_available(self):
        return True

    def extract_text(self):
        self.calls += 1
        return ProcessingResult(
            success=self._success,
            data=self._text if self._success else None,
            error=self._error,
            metadata={"context_source": self._source},
        )


class FakeTranslator:
    def __init__(self, translated="translated text", detected="fr", success=True):
        self._translated = translated
        self._detected = detected
        self._success = success
        self.calls = []
        self.detect_calls = 0

    def name(self):
        return "Fake Translator"

    def is_available(self):
        return True

    def detect_language(self, text):
        self.detect_calls += 1
        return self._detected

    def translate(self, text, source_lang=None, target_lang=None):
        self.calls.append((text, source_lang, target_lang))
        return TranslationResult(
            success=self._success,
            data=self._translated if self._success else None,
            error=None if self._success else "Language pair not installed.",
            source_language=source_lang or self._detected,
            target_language=target_lang,
        )


class FakeAI:
    def __init__(self, answer="ai answer", available=True, success=True, raises=None):
        self._answer = answer
        self._available = available
        self._success = success
        self._raises = raises
        self.calls = []

    def name(self):
        return "Fake AI"

    def is_available(self):
        return self._available

    def generate(self, prompt, system_prompt=None, temperature=None):
        if self._raises is not None:
            raise self._raises
        self.calls.append(
            {"prompt": prompt, "system_prompt": system_prompt, "temperature": temperature}
        )
        return AIResult(
            success=self._success,
            data=self._answer if self._success else None,
            error=None if self._success else "Model not found.",
            model="fake-model",
        )


class FakeSearch:
    def __init__(self, results=None, success=True, raises=None):
        self._results = results if results is not None else [
            {"title": "First hit", "url": "https://example.com/1", "snippet": "Snippet one."},
            {"title": "Second hit", "url": "https://example.com/2", "snippet": "Snippet two."},
        ]
        self._success = success
        self._raises = raises
        self.calls = []

    def name(self):
        return "Fake Search"

    def is_available(self):
        return True

    def search(self, query, max_results=5):
        if self._raises is not None:
            raise self._raises
        self.calls.append((query, max_results))
        return SearchResult(
            success=self._success,
            data=f"Found {len(self._results)} results." if self._success else None,
            error=None if self._success else "DuckDuckGo unreachable.",
            query=query,
            results=self._results[:max_results],
        )


class FakeOCR:
    def __init__(self, text="text from screen", available=True, success=True):
        self._text = text
        self._available = available
        self._success = success
        self.calls = 0

    def name(self):
        return "Fake OCR"

    def is_available(self):
        return self._available

    def recognize(self, image_bytes):
        self.calls += 1
        return OCRResult(
            success=self._success,
            data=self._text if self._success else None,
            error=None if self._success else "No text found.",
            confidence=0.9,
        )


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def providers():
    """One of each fake, so a test can assert on what was called."""
    return {
        "text": FakeTextProvider(),
        "translation": FakeTranslator(),
        "ocr": FakeOCR(),
        "ai": FakeAI(),
        "search": FakeSearch(),
    }


@pytest.fixture()
def pipeline(providers):
    return Pipeline(
        text_provider=providers["text"],
        translation_provider=providers["translation"],
        ocr_provider=providers["ocr"],
        ai_provider=providers["ai"],
        search_provider=providers["search"],
    )


@pytest.fixture()
def local_ok(clean_settings):
    """Settings under which a local action is allowed to proceed."""
    clean_settings.set("privacy.offline_mode", False)
    clean_settings.set("privacy.no_data_retention", False)
    clean_settings.set("ai.enabled", True)
    return clean_settings


# ── Translation ───────────────────────────────────────────────────────


class TestTranslate:
    def test_translates_into_the_configured_target(
        self, local_ok, clear_cache, pipeline, providers
    ):
        local_ok.set("translation.default_target_language", "es")
        local_ok.set("translation.auto_detect_source", True)

        result = pipeline.process(ActionKind.TRANSLATE, context_text="bonjour")

        assert result.success
        assert result.data == "translated text"
        assert providers["translation"].calls == [("bonjour", "fr", "es")]
        assert result.metadata["target_lang"] == "es"

    def test_auto_detect_off_leaves_the_source_unset(
        self, local_ok, clear_cache, pipeline, providers
    ):
        local_ok.set("translation.default_target_language", "en")
        local_ok.set("translation.auto_detect_source", False)

        pipeline.process(ActionKind.TRANSLATE, context_text="hola")

        assert providers["translation"].detect_calls == 0
        assert providers["translation"].calls == [("hola", None, "en")]

    def test_text_already_in_the_target_language_is_not_translated(
        self, local_ok, clear_cache, pipeline, providers
    ):
        """Round-tripping English through an en→en model would mangle it."""
        local_ok.set("translation.default_target_language", "en")
        local_ok.set("translation.auto_detect_source", True)
        providers["translation"]._detected = "en"

        result = pipeline.process(ActionKind.TRANSLATE, context_text="hello there")

        assert result.success
        assert result.data == "hello there"
        assert result.metadata["untranslated"] is True
        assert providers["translation"].calls == []

    def test_second_identical_request_is_served_from_cache(
        self, local_ok, clear_cache, pipeline, providers
    ):
        local_ok.set("translation.default_target_language", "es")
        local_ok.set("privacy.no_data_retention", False)

        pipeline.process(ActionKind.TRANSLATE, context_text="bonjour")
        second = pipeline.process(ActionKind.TRANSLATE, context_text="bonjour")

        assert second.metadata.get("cached") is True
        assert len(providers["translation"].calls) == 1

    def test_no_data_retention_keeps_text_out_of_the_cache(
        self, local_ok, clear_cache, pipeline, providers
    ):
        """The cache holds the user's text in memory. With retention off
        that trade is refused, even at the cost of the speed-up."""
        local_ok.set("translation.default_target_language", "es")
        local_ok.set("privacy.no_data_retention", True)

        pipeline.process(ActionKind.TRANSLATE, context_text="bonjour")
        second = pipeline.process(ActionKind.TRANSLATE, context_text="bonjour")

        assert second.metadata.get("cached") is not True
        assert len(providers["translation"].calls) == 2

    def test_translation_failure_is_surfaced(
        self, local_ok, clear_cache, pipeline, providers
    ):
        providers["translation"]._success = False

        result = pipeline.process(ActionKind.TRANSLATE, context_text="bonjour")

        assert result.success is False
        assert "not installed" in result.error


# ── AI actions ────────────────────────────────────────────────────────


class TestAIActions:
    @pytest.mark.parametrize(
        "action", [ActionKind.EXPLAIN, ActionKind.SUMMARIZE, ActionKind.REWRITE]
    )
    def test_action_reaches_the_ai_provider(self, local_ok, pipeline, providers, action):
        result = pipeline.process(action, context_text="some prose")

        assert result.success
        assert result.data == "ai answer"
        assert result.metadata["model"] == "fake-model"
        assert len(providers["ai"].calls) == 1
        assert "some prose" in providers["ai"].calls[0]["prompt"]

    @pytest.mark.parametrize(
        "action", [ActionKind.EXPLAIN, ActionKind.SUMMARIZE, ActionKind.REWRITE]
    )
    def test_each_action_sends_its_own_instructions(
        self, local_ok, pipeline, providers, action
    ):
        pipeline.process(action, context_text="some prose")
        assert providers["ai"].calls[0]["system_prompt"]

    def test_ai_turned_off_does_not_call_the_provider(
        self, local_ok, pipeline, providers
    ):
        local_ok.set("ai.enabled", False)

        result = pipeline.process(ActionKind.EXPLAIN, context_text="some prose")

        assert result.success is False
        assert "Settings" in result.error
        assert providers["ai"].calls == []

    def test_missing_ollama_explains_how_to_install_it(
        self, local_ok, pipeline, providers
    ):
        providers["ai"]._available = False

        result = pipeline.process(ActionKind.EXPLAIN, context_text="some prose")

        assert result.success is False
        assert "ollama" in result.error.lower()

    def test_provider_failure_is_surfaced(self, local_ok, pipeline, providers):
        providers["ai"]._success = False

        result = pipeline.process(ActionKind.SUMMARIZE, context_text="some prose")

        assert result.success is False
        assert "Model not found" in result.error

    def test_provider_exception_becomes_a_clean_failure(
        self, local_ok, pipeline, providers
    ):
        """A traceback must not reach the user, and must not carry text."""
        providers["ai"]._raises = RuntimeError("connection reset by peer")

        result = pipeline.process(ActionKind.REWRITE, context_text="some prose")

        assert result.success is False
        assert "connection reset" not in result.error


class TestAskAI:
    def test_question_and_text_both_reach_the_model(
        self, local_ok, pipeline, providers
    ):
        result = pipeline.process(
            ActionKind.ASK_AI,
            context_text="The tower is 300m tall.",
            question="How tall is it?",
        )

        assert result.success
        prompt = providers["ai"].calls[0]["prompt"]
        assert "The tower is 300m tall." in prompt
        assert "How tall is it?" in prompt

    def test_missing_question_is_refused_before_the_model_is_called(
        self, local_ok, pipeline, providers
    ):
        result = pipeline.process(ActionKind.ASK_AI, context_text="some prose")

        assert result.success is False
        assert "question" in result.error.lower()
        assert providers["ai"].calls == []

    def test_blank_question_is_refused(self, local_ok, pipeline, providers):
        result = pipeline.process(
            ActionKind.ASK_AI, context_text="some prose", question="   \n "
        )

        assert result.success is False
        assert providers["ai"].calls == []


# ── Search ────────────────────────────────────────────────────────────


class TestSearchWeb:
    def test_results_are_formatted_and_counted(self, local_ok, pipeline, providers):
        local_ok.set("privacy.external_processing_warning", False)

        result = pipeline.process(ActionKind.SEARCH_WEB, context_text="python asyncio")

        assert result.success
        assert result.metadata["result_count"] == 2
        assert "First hit" in result.data
        assert "https://example.com/1" in result.data
        assert result.metadata["results"][0]["title"] == "First hit"

    def test_a_long_selection_is_reduced_to_a_usable_query(
        self, local_ok, pipeline, providers
    ):
        """Search engines mangle multi-line queries, so only the first
        line is sent, capped in length."""
        local_ok.set("privacy.external_processing_warning", False)
        selection = "  what is a   monad  \nsecond line\nthird line"

        pipeline.process(ActionKind.SEARCH_WEB, context_text=selection)

        query, _max_results = providers["search"].calls[0]
        assert query == "what is a monad"

    def test_offline_mode_blocks_the_search_before_the_provider_is_called(
        self, local_ok, pipeline, providers
    ):
        local_ok.set("privacy.offline_mode", True)

        result = pipeline.process(ActionKind.SEARCH_WEB, context_text="python asyncio")

        assert result.success is False
        assert providers["search"].calls == []

    def test_no_results_is_not_an_error(self, local_ok, pipeline, providers):
        local_ok.set("privacy.external_processing_warning", False)
        providers["search"]._results = []

        result = pipeline.process(ActionKind.SEARCH_WEB, context_text="asdkjhasd")

        assert result.success
        assert result.data

    def test_search_exception_becomes_a_clean_failure(
        self, local_ok, pipeline, providers
    ):
        local_ok.set("privacy.external_processing_warning", False)
        providers["search"]._raises = RuntimeError("DNS failure for html.duckduckgo.com")

        result = pipeline.process(ActionKind.SEARCH_WEB, context_text="python asyncio")

        assert result.success is False
        assert "DNS failure" not in result.error


# ── OCR / Capture Text ────────────────────────────────────────────────


class TestCaptureText:
    def test_recognized_text_is_the_result(self, local_ok, pipeline, providers):
        result = pipeline.process(ActionKind.CAPTURE_TEXT, image_bytes=b"PNGDATA")

        assert result.success
        assert result.data == "text from screen"
        assert result.metadata["context_source"] == ContextSource.OCR.value
        assert providers["ocr"].calls == 1

    def test_missing_tesseract_explains_how_to_install_it(
        self, local_ok, pipeline, providers
    ):
        providers["ocr"]._available = False

        result = pipeline.process(ActionKind.CAPTURE_TEXT, image_bytes=b"PNGDATA")

        assert result.success is False
        assert "tesseract" in result.error.lower()
        assert providers["ocr"].calls == 0

    def test_empty_region_reports_that_no_text_was_found(
        self, local_ok, pipeline, providers
    ):
        providers["ocr"]._success = False

        result = pipeline.process(ActionKind.CAPTURE_TEXT, image_bytes=b"PNGDATA")

        assert result.success is False
        assert result.error

    def test_ocr_text_is_the_input_for_other_actions(
        self, local_ok, clear_cache, pipeline, providers
    ):
        """An image can feed any action, not just CAPTURE_TEXT."""
        local_ok.set("translation.default_target_language", "es")

        result = pipeline.process(ActionKind.TRANSLATE, image_bytes=b"PNGDATA")

        assert result.success
        assert providers["translation"].calls[0][0] == "text from screen"


# ── No text to work with ──────────────────────────────────────────────


class TestNoText:
    def test_failed_extraction_reports_the_provider_error(
        self, local_ok, providers
    ):
        providers["text"] = FakeTextProvider(
            success=False, error="Nothing selected. Select some text, then press the hotkey."
        )
        pipeline = Pipeline(
            text_provider=providers["text"],
            translation_provider=providers["translation"],
            ocr_provider=providers["ocr"],
            ai_provider=providers["ai"],
            search_provider=providers["search"],
        )

        result = pipeline.process(ActionKind.EXPLAIN)

        assert result.success is False
        assert "Nothing selected" in result.error
        assert providers["ai"].calls == []

    def test_whitespace_only_selection_is_treated_as_no_text(
        self, local_ok, providers
    ):
        pipeline = Pipeline(
            text_provider=FakeTextProvider(text="   \n\t  "),
            ai_provider=providers["ai"],
        )

        result = pipeline.process(ActionKind.EXPLAIN)

        assert result.success is False
        assert providers["ai"].calls == []

    def test_extraction_crash_does_not_propagate(self, local_ok, providers):
        class ExplodingTextProvider:
            def name(self):
                return "Exploding"

            def is_available(self):
                return True

            def extract_text(self):
                raise OSError("clipboard locked by another process")

        pipeline = Pipeline(
            text_provider=ExplodingTextProvider(), ai_provider=providers["ai"]
        )

        result = pipeline.process(ActionKind.EXPLAIN)

        assert result.success is False
        assert "clipboard locked" not in result.error

    def test_extraction_is_skipped_when_text_is_supplied(
        self, local_ok, pipeline, providers
    ):
        pipeline.process(ActionKind.EXPLAIN, context_text="already have it")

        assert providers["text"].calls == 0


# ── Dispatch and helpers ──────────────────────────────────────────────


class TestDispatch:
    def test_settings_is_not_a_pipeline_action(self, local_ok, pipeline):
        """SETTINGS is routed by the controller and never reaches here."""
        result = pipeline.process(ActionKind.SETTINGS, context_text="anything")

        assert result.success is False
        assert "settings" in result.error.lower()

    def test_only_search_leaves_the_machine(self):
        for action in ActionKind:
            expected = action == ActionKind.SEARCH_WEB
            assert Pipeline.action_requires_external(action) is expected, action

    def test_every_result_is_tagged_with_its_action(self, local_ok, pipeline):
        result = pipeline.process(ActionKind.EXPLAIN, context_text="some prose")
        assert result.metadata["action"] == ActionKind.EXPLAIN.value

    def test_query_is_capped_in_length(self):
        assert len(Pipeline._to_query("x" * 500)) == 300

    def test_query_of_blank_text_is_empty(self):
        assert Pipeline._to_query("   \n  ") == ""


# ── PreparedRequest ───────────────────────────────────────────────────


class TestPreparedRequest:
    def test_ready_requires_text_and_no_error(self):
        assert PreparedRequest(action=ActionKind.EXPLAIN, text="hi").is_ready is True
        assert PreparedRequest(action=ActionKind.EXPLAIN).is_ready is False
        assert PreparedRequest(action=ActionKind.EXPLAIN, text="  ").is_ready is False
        assert PreparedRequest(
            action=ActionKind.EXPLAIN, text="hi", error="blocked"
        ).is_ready is False

    def test_executing_an_unready_request_returns_its_reason(self, local_ok, pipeline):
        prepared = PreparedRequest(action=ActionKind.EXPLAIN, error="Blocked by policy.")

        result = pipeline.execute(prepared)

        assert result.success is False
        assert result.error == "Blocked by policy."

    def test_failure_result_carries_the_context(self):
        prepared = PreparedRequest(
            action=ActionKind.SEARCH_WEB,
            error="Blocked.",
            context_source=ContextSource.CLIPBOARD.value,
            sensitive_types=["credit_card"],
        )

        result = prepared.to_failure_result()

        assert result.success is False
        assert result.metadata["action"] == ActionKind.SEARCH_WEB.value
        assert result.metadata["context_source"] == ContextSource.CLIPBOARD.value
        assert result.metadata["sensitive_types"] == ["credit_card"]

    def test_unready_request_with_no_error_still_reports_something(self):
        result = PreparedRequest(action=ActionKind.EXPLAIN).to_failure_result()
        assert result.error
