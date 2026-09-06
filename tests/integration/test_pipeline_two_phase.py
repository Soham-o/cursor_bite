# Cursor Bite — Two-Phase Pipeline Integration Tests
# ============================================================
# The pipeline is split into prepare() and execute() for one reason:
# the privacy gateway can answer "this may go out, but ask the user
# first". Asking has to happen on the UI thread; the work either side
# of it must not. The split gives the controller a seam to interject a
# dialog into.
#
# That makes the seam a correctness boundary, not just a refactor, and
# these tests hold it in place:
#
#   - prepare() decides and extracts, but does NO work. If the user
#     declines, nothing was sent, because nothing had run yet.
#   - execute() does the work and does NOT revisit the decision. It
#     cannot re-extract (the selection may have changed) or re-evaluate
#     (the answer was already given).
#   - The consent flag and its message survive the gap intact, because
#     the controller has nothing else to render the dialog from.
#
# Fake providers throughout — no network, no Ollama, no Tesseract. The
# real privacy gateway is used, since the interaction between it and
# the pipeline is the thing under test.

import pytest

from app import pipeline as pipeline_module
from app.pipeline import Pipeline, PreparedRequest
from domain.models import (
    ActionKind,
    AIResult,
    ContextSource,
    OCRResult,
    PrivacyDecision,
    ProcessingResult,
    SearchResult,
)


# ── Fakes ─────────────────────────────────────────────────────────────


class RecordingTextProvider:
    def __init__(self, text="the selected text"):
        self.text = text
        self.calls = 0

    def name(self):
        return "Recording Text"

    def is_available(self):
        return True

    def extract_text(self):
        self.calls += 1
        return ProcessingResult(
            success=True,
            data=self.text,
            metadata={"context_source": ContextSource.SELECTED_TEXT.value},
        )


class RecordingSearch:
    def __init__(self):
        self.calls = []

    def name(self):
        return "Recording Search"

    def is_available(self):
        return True

    def search(self, query, max_results=5):
        self.calls.append(query)
        return SearchResult(
            success=True,
            data="Found 1 result.",
            query=query,
            results=[{"title": "A hit", "url": "https://example.com", "snippet": "…"}],
        )


class RecordingAI:
    def __init__(self):
        self.calls = []

    def name(self):
        return "Recording AI"

    def is_available(self):
        return True

    def generate(self, prompt, system_prompt=None, temperature=None):
        self.calls.append(prompt)
        return AIResult(success=True, data="an explanation", model="fake-model")


class RecordingOCR:
    def __init__(self, text="text from the screen"):
        self.text = text
        self.calls = 0

    def name(self):
        return "Recording OCR"

    def is_available(self):
        return True

    def recognize(self, image_bytes):
        self.calls += 1
        return OCRResult(success=True, data=self.text, confidence=0.9)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def parts():
    return {
        "text": RecordingTextProvider(),
        "ai": RecordingAI(),
        "search": RecordingSearch(),
        "ocr": RecordingOCR(),
    }


@pytest.fixture()
def pipeline(parts):
    return Pipeline(
        text_provider=parts["text"],
        ai_provider=parts["ai"],
        search_provider=parts["search"],
        ocr_provider=parts["ocr"],
    )


@pytest.fixture()
def online(clean_settings):
    """Settings where an external action is permitted, subject to consent."""
    clean_settings.set("privacy.offline_mode", False)
    clean_settings.set("privacy.sensitive_data_protection", True)
    clean_settings.set("privacy.external_processing_warning", True)
    clean_settings.set("ai.enabled", True)
    return clean_settings


@pytest.fixture()
def evaluations(monkeypatch):
    """Count privacy evaluations without replacing the real gateway."""
    gateway = pipeline_module.privacy_gateway
    original = gateway.evaluate
    calls = []

    def counting(text, action_name=None, requires_external=False):
        calls.append({"action_name": action_name, "requires_external": requires_external})
        return original(
            text, action_name=action_name, requires_external=requires_external
        )

    monkeypatch.setattr(gateway, "evaluate", counting)
    return calls


# ── prepare() does no work ────────────────────────────────────────────


class TestPrepareDoesNoWork:
    """Everything before the consent dialog must be free to abandon."""

    def test_prepare_extracts_but_does_not_search(self, online, pipeline, parts):
        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)

        assert isinstance(prepared, PreparedRequest)
        assert prepared.is_ready
        assert parts["text"].calls == 1
        assert parts["search"].calls == [], "nothing may go out before consent"

    def test_declining_consent_means_nothing_was_sent(self, online, pipeline, parts):
        """The declined path is simply "never call execute()"."""
        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)
        assert prepared.requires_consent

        # User says no. The controller drops the request here.

        assert parts["search"].calls == []

    def test_granting_consent_runs_the_work(self, online, pipeline, parts):
        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)

        result = pipeline.execute(prepared)

        assert result.success
        assert parts["search"].calls == ["the selected text"]

    def test_prepare_does_not_call_the_ai_provider(self, online, pipeline, parts):
        pipeline.prepare(ActionKind.EXPLAIN)
        assert parts["ai"].calls == []


# ── execute() does not revisit the decision ───────────────────────────


class TestExecuteDoesNotRevisit:
    def test_text_is_extracted_exactly_once(self, online, pipeline, parts):
        """Re-extracting in execute() would read a selection that may have
        changed while the consent dialog was up."""
        prepared = pipeline.prepare(ActionKind.EXPLAIN)
        pipeline.execute(prepared)

        assert parts["text"].calls == 1

    def test_privacy_is_evaluated_exactly_once(
        self, online, pipeline, evaluations
    ):
        """The user already answered; asking the gateway again could
        produce a different answer for text they consented to."""
        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)
        pipeline.execute(prepared)

        assert len(evaluations) == 1

    def test_the_consented_text_is_the_text_that_is_used(self, online, pipeline, parts):
        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)
        consented = prepared.text

        # The user's selection changes after they consented.
        parts["text"].text = "something else entirely"
        pipeline.execute(prepared)

        assert parts["search"].calls == [consented]

    def test_a_prepared_request_can_be_executed_after_a_delay(
        self, online, pipeline, parts
    ):
        """A prepared request holds everything execute() needs, so the
        dialog can take as long as the user does."""
        prepared = pipeline.prepare(ActionKind.EXPLAIN)
        parts["text"].text = "changed while the dialog was up"

        result = pipeline.execute(prepared)

        assert result.success
        assert "the selected text" in parts["ai"].calls[0]


# ── The consent flag survives the gap ─────────────────────────────────


class TestConsentFlag:
    def test_external_action_asks_when_warnings_are_on(self, online, pipeline):
        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)

        assert prepared.requires_consent is True
        assert prepared.consent_message, "the dialog has nothing else to show"
        assert prepared.privacy_decision == PrivacyDecision.WARN

    def test_external_action_does_not_ask_when_warnings_are_off(self, online, pipeline):
        online.set("privacy.external_processing_warning", False)

        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)

        assert prepared.requires_consent is False
        assert prepared.privacy_decision == PrivacyDecision.SAFE_EXTERNAL

    @pytest.mark.parametrize(
        "action",
        [
            ActionKind.TRANSLATE,
            ActionKind.EXPLAIN,
            ActionKind.SUMMARIZE,
            ActionKind.REWRITE,
            ActionKind.ASK_AI,
            ActionKind.CAPTURE_TEXT,
        ],
    )
    def test_local_actions_never_ask(self, online, pipeline, action):
        """Nothing leaves the machine, so there is nothing to consent to.
        Prompting anyway would train the user to click through."""
        prepared = pipeline.prepare(action, context_text="some text")

        assert prepared.requires_consent is False
        assert prepared.privacy_decision == PrivacyDecision.LOCAL_PROCESSING

    def test_consent_is_not_asked_for_a_blocked_request(self, online, pipeline):
        """Blocked is final — there is no dialog that unblocks it."""
        online.set("privacy.offline_mode", True)

        prepared = pipeline.prepare(ActionKind.SEARCH_WEB)

        assert prepared.is_ready is False
        assert prepared.requires_consent is False
        assert prepared.error


# ── The privacy boundary, end to end through the seam ─────────────────


class TestPrivacyBoundary:
    SENSITIVE = "my card is 4111111111111111 and password=hunter22"

    def test_sensitive_text_is_never_blocked_for_local_work(self, online, pipeline):
        """Blocking local processing of sensitive text would protect
        nothing — the text is already on this machine — while making the
        app useless for exactly the documents people care about."""
        prepared = pipeline.prepare(ActionKind.EXPLAIN, context_text=self.SENSITIVE)

        assert prepared.is_ready
        assert prepared.privacy_decision == PrivacyDecision.LOCAL_PROCESSING

    def test_sensitive_text_is_still_reported_for_local_work(self, online, pipeline):
        """Allowed, but the UI is told, so it can say so."""
        prepared = pipeline.prepare(ActionKind.EXPLAIN, context_text=self.SENSITIVE)

        assert "credit_card" in prepared.sensitive_types

    def test_sensitive_text_is_blocked_for_external_work(self, online, pipeline, parts):
        prepared = pipeline.prepare(
            ActionKind.SEARCH_WEB, context_text=self.SENSITIVE
        )

        assert prepared.is_ready is False
        assert prepared.privacy_decision == PrivacyDecision.BLOCKED
        assert prepared.sensitive_types

        # And executing it anyway still sends nothing.
        result = pipeline.execute(prepared)
        assert result.success is False
        assert parts["search"].calls == []

    def test_offline_mode_blocks_external_but_not_local(self, online, pipeline):
        online.set("privacy.offline_mode", True)

        assert pipeline.prepare(ActionKind.SEARCH_WEB).is_ready is False
        assert pipeline.prepare(
            ActionKind.EXPLAIN, context_text="hello"
        ).is_ready is True

    def test_only_search_is_evaluated_as_external(self, online, pipeline, evaluations):
        pipeline.prepare(ActionKind.EXPLAIN, context_text="hello")
        pipeline.prepare(ActionKind.SEARCH_WEB, context_text="hello")

        assert evaluations[0]["requires_external"] is False
        assert evaluations[1]["requires_external"] is True

    def test_the_action_name_reaches_the_gateway(self, online, pipeline, evaluations):
        pipeline.prepare(ActionKind.SUMMARIZE, context_text="hello")

        assert evaluations[0]["action_name"] == ActionKind.SUMMARIZE.value


# ── What crosses the seam ─────────────────────────────────────────────


class TestPreparedRequestContents:
    def test_supplied_text_skips_extraction(self, online, pipeline, parts):
        prepared = pipeline.prepare(ActionKind.EXPLAIN, context_text="given directly")

        assert prepared.text == "given directly"
        assert parts["text"].calls == 0

    def test_the_question_survives_the_gap(self, online, pipeline, parts):
        prepared = pipeline.prepare(
            ActionKind.ASK_AI, context_text="a document", question="what is this?"
        )

        assert prepared.question == "what is this?"

        pipeline.execute(prepared)
        assert "what is this?" in parts["ai"].calls[0]

    def test_an_image_is_recognized_during_prepare(self, online, pipeline, parts):
        """OCR is extraction, so it belongs before the decision — the
        gateway has to see the recognized text to judge it."""
        prepared = pipeline.prepare(ActionKind.CAPTURE_TEXT, image_bytes=b"PNGDATA")

        assert parts["ocr"].calls == 1
        assert prepared.text == "text from the screen"
        assert prepared.context_source == ContextSource.OCR.value

    def test_the_context_source_is_carried_to_the_result(self, online, pipeline):
        prepared = pipeline.prepare(ActionKind.CAPTURE_TEXT, image_bytes=b"PNGDATA")

        result = pipeline.execute(prepared)

        assert result.metadata["context_source"] == ContextSource.OCR.value

    def test_the_privacy_decision_is_carried_to_the_result(self, online, pipeline):
        prepared = pipeline.prepare(ActionKind.EXPLAIN, context_text="hello")

        result = pipeline.execute(prepared)

        assert result.metadata["privacy_decision"] == PrivacyDecision.LOCAL_PROCESSING.value

    def test_prepare_time_is_included_in_the_total(self, online, pipeline):
        prepared = pipeline.prepare(ActionKind.EXPLAIN, context_text="hello")
        prepared.prepare_time_ms = 250

        result = pipeline.execute(prepared)

        assert result.processing_time_ms >= 250


# ── process() composes the two phases ─────────────────────────────────


class TestProcessComposesBothPhases:
    def test_process_matches_prepare_then_execute(self, online, pipeline, parts):
        composed = pipeline.process(ActionKind.EXPLAIN, context_text="hello")

        split = pipeline.execute(
            pipeline.prepare(ActionKind.EXPLAIN, context_text="hello")
        )

        assert composed.success == split.success
        assert composed.data == split.data
        assert composed.metadata["action"] == split.metadata["action"]

    def test_process_still_honours_a_block(self, online, pipeline, parts):
        online.set("privacy.offline_mode", True)

        result = pipeline.process(ActionKind.SEARCH_WEB, context_text="hello")

        assert result.success is False
        assert parts["search"].calls == []

    def test_process_runs_a_consent_requiring_action_without_asking(
        self, online, pipeline, parts
    ):
        """process() is documented as having no UI thread to ask on. It
        must not silently drop the action — callers that can prompt are
        the ones expected to use the two-phase API."""
        result = pipeline.process(ActionKind.SEARCH_WEB, context_text="hello")

        assert result.success
        assert parts["search"].calls == ["hello"]
